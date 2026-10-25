"""Interview orchestration service."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from backend.app.core.errors import AdmissionError
from backend.app.db import connect
from backend.app.prompts.committee import COMMITTEE_SYSTEM_PROMPT
from backend.app.providers.base import LLMProvider
from backend.app.services.candidate_service import CandidateService
from backend.app.services.question_bank_service import QuestionBankService
from backend.app.services.session_service import InterviewSessionService


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _question_to_schema(question: dict | None) -> dict | None:
    if not question:
        return None
    return {
        "id": question["id"],
        "category": question["category"],
        "prompt": question["prompt"],
        "difficulty": question["difficulty"],
    }


class InterviewService:
    def __init__(self) -> None:
        self.candidates = CandidateService()
        self.sessions = InterviewSessionService()
        self.questions = QuestionBankService()

    def create_session(
        self,
        *,
        candidate_id: str | None = None,
        full_name: str | None = None,
        email: str | None = None,
        mode: str = "standard",
    ) -> dict[str, Any]:
        if mode not in {"quick", "standard", "complete"}:
            raise AdmissionError("invalid_mode", "El modo de entrevista no es válido.", 422)
        if candidate_id:
            candidate = self.candidates.get(candidate_id)
            if candidate is None:
                raise AdmissionError("candidate_not_found", "No existe el candidato indicado.", 404)
        else:
            candidate = self.candidates.create(full_name or "Candidato de simulación", email)
        count = {"quick": 5, "standard": 10, "complete": 15}[mode]
        session = self.sessions.create(candidate["id"], mode, count)
        return {"session": session, "candidate": candidate}

    def _get_session_or_404(self, session_id: str) -> dict[str, Any]:
        session = self.sessions.get(session_id)
        if session is None:
            raise AdmissionError("session_not_found", "No existe la sesión de entrevista indicada.", 404)
        return session

    def _base_questions(self, session_id: str) -> list[dict[str, Any]]:
        with connect() as connection:
            rows = connection.execute(
                "SELECT q.* FROM session_questions sq JOIN questions q ON q.id = sq.question_id "
                "WHERE sq.session_id = ? ORDER BY sq.position",
                (session_id,),
            ).fetchall()
        return [{key: row[key] for key in row.keys()} for row in rows]

    def start(self, session_id: str) -> dict[str, Any]:
        session = self._get_session_or_404(session_id)
        if session["status"] != "created":
            raise AdmissionError("invalid_transition", "La entrevista ya fue iniciada o finalizada.", 409)
        selected = self.questions.select_questions(session["mode"])
        if not selected:
            raise AdmissionError("question_bank_empty", "No hay preguntas disponibles para la entrevista.", 500)
        with connect() as connection:
            connection.execute("DELETE FROM session_questions WHERE session_id = ?", (session_id,))
            for position, question in enumerate(selected, start=1):
                connection.execute(
                    "INSERT INTO session_questions (session_id, question_id, position) VALUES (?, ?, ?)",
                    (session_id, question["id"], position),
                )
            connection.commit()
        now = _now()
        self.sessions.update_progress(
            session_id,
            status="in_progress",
            current_question_id=selected[0]["id"],
            current_position=1,
            started_at=now,
            followup_context={},
        )
        updated = self._get_session_or_404(session_id)
        return {
            "session": updated,
            "current_question": _question_to_schema(selected[0]),
            "total_questions": len(selected),
        }

    def get_status(self, session_id: str) -> dict[str, Any]:
        session = self._get_session_or_404(session_id)
        current = None
        if session.get("current_question_id"):
            current = _question_to_schema(self.questions.get(session["current_question_id"]))
        base = self._base_questions(session_id)
        answered = len(self.sessions.list_answers(session_id))
        return {
            "session": session,
            "current_question": current,
            "total_questions": len(base) if base else session["question_count"],
            "answered_questions": answered,
        }

    def get_current_question(self, session_id: str) -> dict[str, Any]:
        session = self._get_session_or_404(session_id)
        base = self._base_questions(session_id)
        total = len(base) if base else session["question_count"]
        current = None
        if session.get("current_question_id"):
            current = _question_to_schema(self.questions.get(session["current_question_id"]))
        return {
            "session_id": session_id,
            "status": session["status"],
            "position": session.get("current_position") or 0,
            "total_questions": total,
            "current_question": current,
        }

    def submit_answer(self, session_id: str, question_id: str, answer: str) -> dict[str, Any]:
        session = self._get_session_or_404(session_id)
        if session["status"] != "in_progress":
            raise AdmissionError("invalid_session_state", "La entrevista no está en curso.", 409)
        existing = next(
            (item for item in self.sessions.list_answers(session_id) if item["question_id"] == question_id),
            None,
        )
        if existing is not None:
            raise AdmissionError("duplicate_answer", "La pregunta ya fue respondida.", 409)
        if session.get("current_question_id") != question_id:
            raise AdmissionError("not_current_question", "La pregunta no es la pregunta actual de la sesión.", 400)
        question = self.questions.get(question_id)
        if question is None:
            with connect() as connection:
                row = connection.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
            question = {key: row[key] for key in row.keys()} if row else None
        if question is None:
            raise AdmissionError("question_not_found", "No existe la pregunta indicada.", 404)
        answer_id = str(uuid.uuid4())
        try:
            with connect() as connection:
                connection.execute(
                    "INSERT INTO answers (id, session_id, question_id, candidate_answer, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (answer_id, session_id, question_id, answer, _now()),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise AdmissionError("duplicate_answer", "La pregunta ya fue respondida.", 409) from exc

        context = dict(session.get("followup_context") or {})
        context["last_question_id"] = question_id
        context["last_question_prompt"] = question["prompt"]
        context["last_answer"] = answer
        is_followup = question.get("category") == "follow_up"
        if not is_followup:
            context["last_base_question_id"] = question_id
            context["last_base_position"] = session.get("current_position") or 0
        else:
            context.pop("pending_followup_id", None)

        base = self._base_questions(session_id)
        if is_followup:
            parent_position = int(context.get("last_base_position") or session.get("current_position") or 0)
            next_position = parent_position + 1
        else:
            next_position = int(session.get("current_position") or 0) + 1

        next_question = None
        if 1 <= next_position <= len(base):
            next_question = base[next_position - 1]
            self.sessions.update_progress(
                session_id,
                current_question_id=next_question["id"],
                current_position=next_position,
                followup_context=context,
            )
        else:
            self.sessions.update_progress(
                session_id,
                current_question_id=None,
                current_position=int(session.get("current_position") or 0),
                followup_context=context,
            )
        updated = self._get_session_or_404(session_id)
        return {
            "session_id": session_id,
            "question_id": question_id,
            "answer_id": answer_id,
            "status": updated["status"],
            "next_question": _question_to_schema(next_question),
            "completed_available": True,
        }

    def get_history(self, session_id: str) -> dict[str, Any]:
        session = self._get_session_or_404(session_id)
        items = []
        for answer in self.sessions.list_answers(session_id):
            question = self.questions.get(answer["question_id"])
            if question is None:
                with connect() as connection:
                    row = connection.execute("SELECT * FROM questions WHERE id = ?", (answer["question_id"],)).fetchone()
                question = {key: row[key] for key in row.keys()} if row else None
            if question is None:
                continue
            items.append({
                "question_id": question["id"],
                "category": question["category"],
                "prompt": question["prompt"],
                "answer": answer["candidate_answer"],
                "created_at": answer["created_at"],
            })
        return {"session_id": session_id, "status": session["status"], "items": items}

    def complete(self, session_id: str) -> dict[str, Any]:
        session = self._get_session_or_404(session_id)
        if session["status"] != "in_progress":
            raise AdmissionError("invalid_session_state", "La entrevista no está en curso.", 409)
        now = _now()
        self.sessions.update_progress(
            session_id,
            status="completed",
            current_question_id=None,
            completed_at=now,
            followup_context=session.get("followup_context") or {},
        )
        updated = self._get_session_or_404(session_id)
        return {
            "session_id": session_id,
            "status": updated["status"],
            "completed_at": updated.get("completed_at"),
        }

    async def generate_followup(self, session_id: str, provider: LLMProvider) -> dict[str, Any]:
        session = self._get_session_or_404(session_id)
        if session["status"] != "in_progress":
            raise AdmissionError("invalid_session_state", "La entrevista no está en curso.", 409)
        context = dict(session.get("followup_context") or {})
        last_answer = context.get("last_answer")
        if not last_answer:
            answers = self.sessions.list_answers(session_id)
            if answers:
                last = answers[-1]
                last_answer = last["candidate_answer"]
                context["last_answer"] = last_answer
                question = self.questions.get(last["question_id"])
                if question is not None:
                    context["last_question_prompt"] = question["prompt"]
                    context["last_question_id"] = question["id"]
        if not last_answer:
            raise AdmissionError("no_answer", "Se necesita una respuesta previa para generar un seguimiento.", 400)
        last_prompt = context.get("last_question_prompt") or "Pregunta anterior"
        await provider.ensure_available()
        system_prompt = (
            COMMITTEE_SYSTEM_PROMPT
            + "\n\nCuando se te pida una pregunta de seguimiento, responde únicamente con JSON válido."
        )
        user_prompt = (
            "Genera una pregunta de seguimiento para una entrevista de admisión.\n"
            f"Pregunta anterior: {last_prompt}\n"
            f"Respuesta del candidato: {last_answer}\n\n"
            "Devuelve JSON con exactamente estas claves:\n"
            '{"should_ask": true o false, "followup_question": "pregunta en español mexicano profesional", "rationale": "breve"}\n'
            "Reglas: no inventes datos del candidato; la pregunta debe derivarse únicamente de su respuesta; "
            "si no conviene profundizar, usa should_ask=false y followup_question=""."
        )
        from backend.app.api.schemas import LLMFollowupOutput

        raw = None
        parsed = None
        error_text = None
        for attempt in range(2):
            try:
                if attempt == 0:
                    raw = await provider.generate_with_system(system_prompt, user_prompt)
                else:
                    raw = await provider.generate_with_system(
                        system_prompt,
                        user_prompt
                        + "\n\nLa respuesta anterior no fue JSON válido. Corrígela y devuelve solo JSON.\n"
                        + f"Respuesta anterior: {raw}\nError: {error_text}",
                    )
                data = json.loads(raw)
                parsed = LLMFollowupOutput.model_validate(data)
                break
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                error_text = str(exc)
                parsed = None
        if parsed is None:
            raise AdmissionError("malformed_llm_output", "El modelo devolvió una respuesta inválida.", 502)
        if not parsed.should_ask or not parsed.followup_question.strip():
            context["pending_followup_id"] = None
            self.sessions.update_progress(session_id, followup_context=context)
            return {
                "session_id": session_id,
                "should_ask": False,
                "followup_question": None,
                "message": parsed.rationale or "No se generó pregunta de seguimiento.",
            }
        followup_id = str(uuid.uuid4())
        prompt = parsed.followup_question.strip()
        with connect() as connection:
            connection.execute(
                "INSERT INTO questions (id, category, prompt, difficulty, created_at) VALUES (?, ?, ?, ?, ?)",
                (followup_id, "follow_up", prompt, "medium", _now()),
            )
            connection.commit()
        context["pending_followup_id"] = followup_id
        context["last_base_position"] = context.get("last_base_position") or session.get("current_position") or 0
        self.sessions.update_progress(
            session_id,
            current_question_id=followup_id,
            followup_context=context,
        )
        return {
            "session_id": session_id,
            "should_ask": True,
            "followup_question": {
                "id": followup_id,
                "category": "follow_up",
                "prompt": prompt,
                "difficulty": "medium",
            },
            "message": parsed.rationale,
        }
