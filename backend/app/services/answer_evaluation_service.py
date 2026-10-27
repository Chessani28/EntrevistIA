"""Answer evaluation engine for AI admission interview responses."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from pydantic import ValidationError

from backend.app.core.errors import AdmissionError
from backend.app.db import connect
from backend.app.prompts.answer_evaluator import ANSWER_EVALUATOR_SYSTEM_PROMPT
from backend.app.providers.base import LLMProvider
from backend.app.services.candidate_service import CandidateService
from backend.app.services.interview_service import InterviewService
from backend.app.services.question_bank_service import QuestionBankService
from backend.app.services.session_service import InterviewSessionService




def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


DISCLAIMER = "Evaluacion generada por IA para preparacion del candidato. No constituye una decision oficial de admision ni una medicion psicometrica validada."


def _normalize_llm_output(data):
    if not isinstance(data, dict):
        return data
    # overall_score
    try:
        data["overall_score"] = max(0, min(100, int(float(data.get("overall_score", 0)))))
    except (TypeError, ValueError):
        data["overall_score"] = 0
    # technical_accuracy
    ta = data.get("technical_accuracy")
    valid_cls = {"correct", "partially_correct", "unsupported", "incorrect", "insufficient_evidence", "not_applicable"}
    if isinstance(ta, bool):
        data["technical_accuracy"] = None
    elif isinstance(ta, (int, float)):
        cls = "correct" if ta >= 70 else ("partially_correct" if ta >= 40 else "incorrect")
        data["technical_accuracy"] = {"classification": cls, "claims": []}
    elif isinstance(ta, str):
        if ta.strip().lower() in valid_cls:
            data["technical_accuracy"] = {"classification": ta.strip().lower(), "claims": []}
        else:
            try:
                data["technical_accuracy"] = {"classification": "not_applicable", "claims": [{"claim": ta, "supported": False}]}
            except Exception:
                data["technical_accuracy"] = None
    elif isinstance(ta, dict):
        cls = ta.get("classification")
        if cls not in valid_cls:
            # maybe a numeric score was put in classification
            if isinstance(cls, (int, float)):
                cls = "correct" if cls >= 70 else ("partially_correct" if cls >= 40 else "incorrect")
            else:
                cls = "not_applicable"
        claims = ta.get("claims")
        if not isinstance(claims, list):
            claims = []
        data["technical_accuracy"] = {"classification": cls, "claims": claims}
    elif ta is None:
        pass
    else:
        data["technical_accuracy"] = None
    # stress_management
    sm = data.get("stress_management")
    if isinstance(sm, dict):
        for k in ("addresses", "missing", "suggestions"):
            if not isinstance(sm.get(k), list):
                sm[k] = []
    elif sm is not None and not isinstance(sm, dict):
        data["stress_management"] = None
    # criteria
    crit = data.get("criteria")
    if isinstance(crit, dict):
        crit = [{"name": k, "score": v, "status": "applicable", "explanation": ""} for k, v in crit.items()]
    if not isinstance(crit, list):
        crit = []
    norm_crit = []
    for c in crit:
        if isinstance(c, dict):
            name = str(c.get("name") or "").strip()
            if not name:
                continue
            score = c.get("score")
            try:
                score = int(score) if score is not None else None
            except (TypeError, ValueError):
                score = None
            if score is not None:
                score = max(0, min(100, score))
            status = c.get("status") or "applicable"
            if status not in {"applicable", "not_applicable", "insufficient_evidence"}:
                status = "applicable"
            norm_crit.append({"name": name, "score": score, "status": status, "explanation": str(c.get("explanation") or "")})
        elif isinstance(c, str):
            norm_crit.append({"name": c, "score": None, "status": "insufficient_evidence", "explanation": ""})
    data["criteria"] = norm_crit
    # list-of-str fields
    for k in ("strengths", "weaknesses", "recommendations"):
        v = data.get(k)
        if isinstance(v, str):
            data[k] = [v] if v.strip() else []
        elif isinstance(v, list):
            data[k] = [str(x) for x in v]
        else:
            data[k] = []
    # str fields
    for k in ("revised_answer", "practice_tip", "feedback"):
        v = data.get(k)
        if v is None:
            data[k] = ""
        elif not isinstance(v, str):
            data[k] = str(v)
    return data


def _is_stress_question(prompt, question=None):
    text = (prompt or "").lower()
    if question:
        text += " " + str(question.get("category", "")).lower()
    return "estres" in text or "time_management_stress" in text


def _question_to_prompt(question):
    if not question:
        return ""
    return str(question.get("prompt") or "")


class AnswerEvaluationService:
    def __init__(self):
        self.sessions = InterviewSessionService()
        self.interviews = InterviewService()
        self.questions = QuestionBankService()
        self.candidates = CandidateService()

    def evaluate(self, question_prompt, candidate_answer):
        answer = candidate_answer or ""
        lowered = answer.lower()
        criteria = {
            "relevance": 50 if answer.strip() else 0,
            "clarity": 50 if len(answer.split()) >= 5 else 25,
            "coherence": 50,
            "technical_depth": 40 if any(term in lowered for term in ("python", "sql", "algoritmo", "modelo")) else 20,
            "evidence": 40 if any(term in lowered for term in ("proyecto", "experiencia", "ejemplo")) else 10,
        }
        return {
            "score": round(sum(criteria.values()) / len(criteria)),
            "criteria": criteria,
            "feedback": "Evaluacion preliminar basada en heuristicas locales.",
            "question_prompt": question_prompt,
            "answer_length": len(answer),
            "disclaimer": DISCLAIMER,
        }

    def _get_question(self, question_id):
        if not question_id:
            return None
        question = self.questions.get(question_id)
        if question is not None:
            return question
        with connect() as connection:
            row = connection.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        return {key: row[key] for key in row.keys()} if row else None

    def _get_answer_row(self, answer_id):
        with connect() as connection:
            row = connection.execute("SELECT * FROM answers WHERE id = ?", (answer_id,)).fetchone()
        return {key: row[key] for key in row.keys()} if row else None

    def _get_session(self, session_id):
        return self.sessions.get(session_id)

    def _get_evaluation_by_answer(self, answer_id):
        with connect() as connection:
            row = connection.execute("SELECT * FROM evaluations WHERE answer_id = ?", (answer_id,)).fetchone()
        return {key: row[key] for key in row.keys()} if row else None

    def _get_evaluation_by_id(self, evaluation_id):
        with connect() as connection:
            row = connection.execute("SELECT * FROM evaluations WHERE id = ?", (evaluation_id,)).fetchone()
        return {key: row[key] for key in row.keys()} if row else None

    def _row_to_dict(self, row):
        evaluation_result = {}
        try:
            evaluation_result = json.loads(row.get("evaluation_result") or "{}")
        except (json.JSONDecodeError, TypeError):
            evaluation_result = {}
        criteria = []
        try:
            criteria = json.loads(row.get("criteria") or "[]")
            if isinstance(criteria, dict):
                criteria = [{"name": key, "score": value, "status": "applicable", "explanation": ""} for key, value in criteria.items()]
        except (json.JSONDecodeError, TypeError):
            criteria = []
        if not criteria and isinstance(evaluation_result.get("criteria"), list):
            criteria = evaluation_result["criteria"]
        scores = {}
        for item in criteria:
            if isinstance(item, dict) and "name" in item:
                scores[item["name"]] = item.get("score")

        strengths = evaluation_result.get("strengths") or []
        weaknesses = evaluation_result.get("weaknesses") or []
        recommendations = evaluation_result.get("recommendations") or []
        revised_answer = evaluation_result.get("revised_answer") or ""
        practice_tip = evaluation_result.get("practice_tip") or ""
        technical_accuracy = evaluation_result.get("technical_accuracy")
        stress_management = evaluation_result.get("stress_management")
        question_prompt = row.get("question_prompt") or evaluation_result.get("question_prompt") or ""
        original_answer = row.get("original_answer") or evaluation_result.get("original_answer") or ""

        payload = {
            "id": row["id"],
            "evaluation_id": row["id"],
            "session_id": row["session_id"],
            "answer_id": row["answer_id"],
            "question_id": row.get("question_id"),
            "candidate_id": row.get("candidate_id"),
            "question_prompt": question_prompt,
            "original_answer": original_answer,
            "overall_score": row.get("score"),
            "score": row.get("score"),
            "criteria": criteria,
            "scores": scores,
            "strengths": strengths,
            "fortalezas": strengths,
            "weaknesses": weaknesses,
            "areas_for_improvement": weaknesses,
            "recommendations": recommendations,
            "recomendaciones": recommendations,
            "revised_answer": revised_answer,
            "improved_answer": revised_answer,
            "respuesta_mejorada": revised_answer,
            "practice_tip": practice_tip,
            "consejo_practica": practice_tip,
            "technical_accuracy": technical_accuracy,
            "stress_management": stress_management,
            "disclaimer": DISCLAIMER,
            "status": row.get("status") or "completed",
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }
        _snapshot = {k: v for k, v in payload.items() if k not in {"evaluation", "result", "analysis"}}
        payload["evaluation"] = _snapshot
        payload["result"] = _snapshot
        payload["analysis"] = _snapshot
        return payload
    async def evaluate_answer(self, provider, session_id=None, question_id=None, answer_id=None, question_prompt=None, candidate_answer=None, answer=None, force=False, context=None):
        if answer is not None and candidate_answer is None:
            candidate_answer = answer
        if answer_id:
            answer_row = self._get_answer_row(answer_id)
            if answer_row is None:
                raise AdmissionError("answer_not_found", "No existe la respuesta indicada.", 404)
            session_id = session_id or answer_row["session_id"]
            question_id = question_id or answer_row["question_id"]
            if candidate_answer is None:
                candidate_answer = answer_row["candidate_answer"]
        if not session_id:
            raise AdmissionError("session_required", "Se requiere session_id para evaluar la respuesta.", 400)
        session = self._get_session(session_id)
        if session is None:
            raise AdmissionError("session_not_found", "No existe la sesion de entrevista indicada.", 404)
        if not question_id:
            question_id = session.get("current_question_id")
        if not question_id:
            raise AdmissionError("question_required", "Se requiere question_id para evaluar la respuesta.", 400)
        question = self._get_question(question_id)
        if question is None:
            raise AdmissionError("question_not_found", "No existe la pregunta indicada.", 404)
        if question_prompt is None:
            question_prompt = _question_to_prompt(question)

        existing_answer = None
        with connect() as connection:
            row = connection.execute("SELECT * FROM answers WHERE session_id = ? AND question_id = ?", (session_id, question_id)).fetchone()
        if row is not None:
            existing_answer = {key: row[key] for key in row.keys()}

        if existing_answer is not None:
            answer_id = answer_id or existing_answer["id"]
            if candidate_answer is not None and candidate_answer != existing_answer["candidate_answer"]:
                candidate_answer = existing_answer["candidate_answer"]
            if candidate_answer is None:
                candidate_answer = existing_answer["candidate_answer"]
        else:
            if not candidate_answer:
                raise AdmissionError("answer_required", "Se requiere la respuesta del candidato.", 400)
            answer_id = answer_id or str(uuid.uuid4())
            try:
                with connect() as connection:
                    connection.execute("INSERT INTO answers (id, session_id, question_id, candidate_answer, created_at) VALUES (?, ?, ?, ?, ?)", (answer_id, session_id, question_id, candidate_answer, _now()))
                    connection.commit()
            except sqlite3.IntegrityError:
                with connect() as connection:
                    row = connection.execute("SELECT * FROM answers WHERE session_id = ? AND question_id = ?", (session_id, question_id)).fetchone()
                if row is None:
                    raise
                existing_answer = {key: row[key] for key in row.keys()}
                answer_id = existing_answer["id"]
                candidate_answer = existing_answer["candidate_answer"]

        if not candidate_answer:
            raise AdmissionError("answer_required", "Se requiere la respuesta del candidato.", 400)

        existing_eval = self._get_evaluation_by_answer(answer_id)
        if existing_eval is not None and not force:
            return self._row_to_dict(existing_eval)
        if force and existing_eval is not None:
            with connect() as connection:
                connection.execute("DELETE FROM evaluations WHERE answer_id = ?", (answer_id,))
                connection.commit()

        await provider.ensure_available()

        stress = _is_stress_question(question_prompt, question)
        system_prompt = ANSWER_EVALUATOR_SYSTEM_PROMPT
        user_prompt = self._build_user_prompt(question_prompt=question_prompt, candidate_answer=candidate_answer, stress=stress, context=context)

        parsed = None
        raw = None
        error_text = None
        for attempt in range(2):
            try:
                if attempt == 0:
                    raw = await provider.generate_with_system(system_prompt, user_prompt)
                else:
                    raw = await provider.generate_with_system(system_prompt, user_prompt + "\n\nLa respuesta anterior no fue JSON valido. Devuelve unicamente JSON valido conforme al esquema. No incluyas texto fuera del JSON.")
                data = json.loads(raw)
                data = _normalize_llm_output(data)
                from backend.app.api.schemas import AnswerEvaluationLLMOutput
                parsed = AnswerEvaluationLLMOutput.model_validate(data)
                break
            except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as exc:
                error_text = str(exc)
                parsed = None
            except Exception as exc:
                error_text = str(exc)
                parsed = None
                break
        if parsed is None:
            raise AdmissionError("malformed_llm_output", "El modelo devolvio una respuesta invalida.", 502)

        evaluation_id = str(uuid.uuid4())
        created_at = _now()
        candidate_id = session.get("candidate_id")
        criteria_list = []
        for c in (parsed.criteria or []):
            if hasattr(c, "model_dump"):
                criteria_list.append(c.model_dump())
            elif hasattr(c, "dict"):
                criteria_list.append(c.dict())
            else:
                criteria_list.append(c)

        normalized_criteria = []
        for item in criteria_list:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            score = item.get("score")
            if score is not None:
                try:
                    score = max(0, min(100, int(score)))
                except (TypeError, ValueError):
                    score = None
            status = item.get("status") or "applicable"
            if status not in {"applicable", "not_applicable", "insufficient_evidence"}:
                status = "applicable"
            normalized_criteria.append({"name": name, "score": score, "status": status, "explanation": str(item.get("explanation") or "")})

        if not normalized_criteria:
            for name in ("relevance", "clarity", "coherence", "technical_accuracy", "depth", "professionalism", "confidence", "naturalness", "evidence_examples", "practical_reasoning"):
                normalized_criteria.append({"name": name, "score": None, "status": "insufficient_evidence", "explanation": "El modelo no devolvio criterios estructurados."})

        stress_feedback = None
        if parsed.stress_management is not None:
            stress_feedback = {"addresses": list(parsed.stress_management.addresses or []), "missing": list(parsed.stress_management.missing or []), "suggestions": list(parsed.stress_management.suggestions or [])}
        elif stress:
            stress_feedback = {"addresses": [], "missing": [], "suggestions": []}

        technical_feedback = None
        if parsed.technical_accuracy is not None:
            technical_feedback = {"classification": parsed.technical_accuracy.classification, "claims": list(parsed.technical_accuracy.claims or [])}

        evaluation_result = {
            "question_prompt": question_prompt,
            "original_answer": candidate_answer,
            "overall_score": parsed.overall_score,
            "criteria": normalized_criteria,
            "strengths": list(parsed.strengths or []),
            "weaknesses": list(parsed.weaknesses or []),
            "recommendations": list(parsed.recommendations or []),
            "revised_answer": parsed.revised_answer or "",
            "practice_tip": parsed.practice_tip or "",
            "technical_accuracy": technical_feedback,
            "stress_management": stress_feedback,
            "feedback": parsed.feedback or "",
            "disclaimer": DISCLAIMER,
        }

        try:
            with connect() as connection:
                connection.execute("INSERT INTO evaluations (id, session_id, answer_id, question_id, candidate_id, original_answer, question_prompt, score, criteria, feedback, evaluation_result, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?)", (evaluation_id, session_id, answer_id, question_id, candidate_id, candidate_answer, question_prompt, int(parsed.overall_score), json.dumps(normalized_criteria, ensure_ascii=False), parsed.feedback or "", json.dumps(evaluation_result, ensure_ascii=False), created_at, created_at))
                connection.commit()
        except sqlite3.IntegrityError:
            existing = self._get_evaluation_by_answer(answer_id)
            if existing is not None:
                return self._row_to_dict(existing)
            raise

        row = self._get_evaluation_by_id(evaluation_id)
        if row:
            return self._row_to_dict(row)
        return self._row_to_dict({"id": evaluation_id, "session_id": session_id, "answer_id": answer_id, "question_id": question_id, "candidate_id": candidate_id, "original_answer": candidate_answer, "question_prompt": question_prompt, "score": parsed.overall_score, "criteria": json.dumps(normalized_criteria, ensure_ascii=False), "feedback": parsed.feedback or "", "evaluation_result": json.dumps(evaluation_result, ensure_ascii=False), "status": "completed", "created_at": created_at, "updated_at": created_at})


    def _build_user_prompt(self, question_prompt, candidate_answer, stress, context):
        parts = ["Evalua la siguiente respuesta de entrevista de admision.", "Pregunta: " + str(question_prompt), "Respuesta del candidato: " + str(candidate_answer)]
        if stress:
            parts.append("Esta es la pregunta obligatoria sobre manejo del estres. Proporciona retroalimentacion especializada.")
        if context:
            parts.append("Contexto adicional: " + json.dumps(context, ensure_ascii=False))
        parts.append("Usa unicamente la informacion contenida en la respuesta. No inventes datos del candidato.")
        parts.append("Devuelve solo JSON valido conforme a la rubrica.")
        return "\n".join(parts)

    def get_evaluation(self, evaluation_id=None, answer_id=None):
        row = None
        if evaluation_id:
            row = self._get_evaluation_by_id(evaluation_id)
        if row is None and answer_id:
            row = self._get_evaluation_by_answer(answer_id)
        if row is None:
            raise AdmissionError("evaluation_not_found", "No existe la evaluacion indicada.", 404)
        return self._row_to_dict(row)

    def list_evaluations(self, session_id):
        session = self._get_session(session_id)
        if session is None:
            raise AdmissionError("session_not_found", "No existe la sesion de entrevista indicada.", 404)
        with connect() as connection:
            rows = connection.execute("SELECT * FROM evaluations WHERE session_id = ? ORDER BY created_at", (session_id,)).fetchall()
        return [self._row_to_dict({key: row[key] for key in row.keys()}) for row in rows]

    def get_improved_answer(self, evaluation_id=None, answer_id=None):
        evaluation = self.get_evaluation(evaluation_id=evaluation_id, answer_id=answer_id)
        return {"evaluation_id": evaluation.get("evaluation_id"), "answer_id": evaluation.get("answer_id"), "revised_answer": evaluation.get("revised_answer") or "", "improved_answer": evaluation.get("improved_answer") or "", "practice_tip": evaluation.get("practice_tip")}

    async def evaluate(self, *args, **kwargs):
        if args and not kwargs.get("question_prompt") and not kwargs.get("candidate_answer"):
            if len(args) >= 2:
                kwargs["question_prompt"] = args[0]
                kwargs["candidate_answer"] = args[1]
                args = args[2:]
        if "provider" not in kwargs:
            raise AdmissionError("provider_required", "Se requiere un proveedor LLM.", 500)
        return await self.evaluate_answer(*args, **kwargs)

    async def analyze_answer(self, **kwargs):
        return await self.evaluate_answer(**kwargs)

    async def evaluate_response(self, **kwargs):
        return await self.evaluate_answer(**kwargs)

    def get(self, evaluation_id):
        return self.get_evaluation(evaluation_id=evaluation_id)

    def retrieve(self, evaluation_id):
        return self.get_evaluation(evaluation_id=evaluation_id)

    def list(self, session_id):
        return self.list_evaluations(session_id)

    def list_by_session(self, session_id):
        return self.list_evaluations(session_id)
