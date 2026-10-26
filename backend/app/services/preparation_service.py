"""Personalized AI preparation plan service."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.errors import AdmissionError
from backend.app.db import connect
from backend.app.providers.base import LLMProvider


class PreparationActivityOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    topic: str = ""
    title: str = ""
    description: str = ""
    estimated_minutes: int = Field(default=30, ge=5, le=240)
    week: int = Field(default=1, ge=1, le=52)
    day: str = ""
    resource: str = ""


class PreparationPlanOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    summary: str = ""
    priority_topics: list[dict] = Field(default_factory=list)
    activities: list[PreparationActivityOutput] = Field(default_factory=list)
    milestones: list[dict] = Field(default_factory=list)
    review_sessions: list[str] = Field(default_factory=list)


DISCLAIMER = "Plan generado por IA para preparacion del candidato. No constituye una decision oficial de admision ni una medicion psicometrica validada."

CURATED_RESOURCES = [
    "Documentacion oficial del lenguaje o tecnologia estudiada",
    "Tutoriales introductorios de universidades o fundaciones sin fines de lucro",
    "Articulos de revision y documentacion de bibliotecas open source",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _weeks_between(target_date: str | None) -> int:
    if not target_date:
        return 4
    try:
        target = date.fromisoformat(target_date)
    except ValueError:
        return 4
    today = datetime.now(timezone.utc).date()
    delta = (target - today).days
    if delta <= 0:
        return 1
    return max(1, min(12, round(delta / 7)))


class PreparationService:
    def __init__(self):
        from backend.app.services.candidate_service import CandidateService
        from backend.app.services.interview_service import InterviewService
        from backend.app.services.session_service import InterviewSessionService
        from backend.app.services.cv_analysis_service import CVAnalysisService
        from backend.app.services.answer_evaluation_service import AnswerEvaluationService

        self.candidates = CandidateService()
        self.interviews = InterviewService()
        self.sessions = InterviewSessionService()
        self.cv = CVAnalysisService()
        self.evaluations = AnswerEvaluationService()

    def _candidate_sessions(self, candidate_id: str):
        all_sessions = self.sessions.list(500)
        return [s for s in all_sessions if s.get("candidate_id") == candidate_id]

    def _latest_cv(self, candidate_id: str):
        with connect() as connection:
            row = connection.execute(
                "SELECT * FROM cv_analyses WHERE candidate_id = ? AND status = 'completed' ORDER BY created_at DESC LIMIT 1",
                (candidate_id,),
            ).fetchone()
        if row is None:
            return None
        return self.cv._row_to_dict({key: row[key] for key in row.keys()})

    def _interview_summary(self, candidate_id: str):
        summaries = []
        for session in self._candidate_sessions(candidate_id):
            if session.get("status") != "completed":
                continue
            evals = self.evaluations.list_evaluations(session["id"])
            scores = [e.get("overall_score") or e.get("score") for e in evals if (e.get("overall_score") or e.get("score")) is not None]
            avg = round(sum(scores) / len(scores), 1) if scores else None
            weak = []
            for ev in evals:
                for c in (ev.get("criteria") or []):
                    if isinstance(c, dict) and (c.get("score") or 0) < 60:
                        weak.append(c.get("name"))
            summaries.append({
                "session_id": session["id"],
                "mode": session.get("mode"),
                "completed_at": session.get("completed_at"),
                "average_score": avg,
                "question_count": len(evals),
                "weak_criteria": sorted(set(weak)),
            })
        return summaries

    def _build_context(self, candidate_id, target_date, study_minutes, goal, topics):
        candidate = self.candidates.get(candidate_id)
        if candidate is None:
            raise AdmissionError("candidate_not_found", "No existe el candidato indicado.", 404)
        sessions = self._interview_summary(candidate_id)
        cv = self._latest_cv(candidate_id)
        cv_summary = None
        if cv:
            analysis = cv.get("analysis") or {}
            cv_summary = {
                "file_name": cv.get("file_name"),
                "professional_summary": analysis.get("professional_summary"),
                "strengths": analysis.get("strengths", []),
                "missing_or_unclear_evidence": analysis.get("missing_or_unclear_evidence", []),
                "recommendations": analysis.get("recommendations", []),
            }
        weeks = _weeks_between(target_date)
        return {
            "candidate": candidate,
            "sessions": sessions,
            "cv": cv_summary,
            "target_date": target_date,
            "study_minutes_per_week": study_minutes,
            "weeks": weeks,
            "goal": goal,
            "topics": topics or [],
        }

    def _prompt(self, context):
        system = (
            "Eres un asistente academico que crea planes de preparacion personalizados para admision a una Maestria en IA. "
            "Usa solo la informacion proporcionada. No inventes calificaciones, experiencia ni enlaces. "
            "Devuelve unicamente JSON valido. Las actividades deben caber en el tiempo disponible. "
            "Prioriza areas con puntuaciones bajas. No presentes prioridades como cientificamente validadas."
        )
        user = (
            "Crea un plan de preparacion personalizado.\n"
            f"Candidato: {context['candidate'].get('full_name')}\n"
            f"Objetivo: {context['goal'] or 'Preparacion para entrevista de admision'}\n"
            f"Fecha objetivo: {context['target_date'] or 'sin fecha'}\n"
            f"Semanas disponibles: {context['weeks']}\n"
            f"Tiempo de estudio por semana (minutos): {context['study_minutes_per_week']}\n"
            f"Temas opcionales a mejorar: {context['topics']}\n"
            f"Entrevistas completadas: {json.dumps(context['sessions'], ensure_ascii=False)}\n"
            f"Analisis de CV: {json.dumps(context['cv'], ensure_ascii=False)}\n\n"
            "Devuelve JSON con estas claves:\n"
            "{\n"
            '  "summary": "resumen del plan",\n'
            '  "priority_topics": [{"topic":"","reason":"","priority":"high|medium|low","allocated_minutes_per_week":0}],\n'
            '  "activities": [{"topic":"","title":"","description":"","estimated_minutes":30,"week":1,"day":"Lunes","resource":"recurso gratuito sugerido"}],\n'
            '  "milestones": [{"week":1,"title":"","success_criteria":""}],\n'
            '  "review_sessions": ["sesion de repaso sugerida"]\n'
            "}\n"
            "Reglas: no inventes enlaces; usa nombres de recursos o sugerencias genericas verificables; "
            "la suma de estimated_minutes no debe superar el tiempo semanal disponible multiplicado por las semanas; "
            "si solo hay una entrevista, tratela como linea base."
        )
        return system, user

    async def generate_plan(self, provider: LLMProvider, candidate_id: str, target_date=None, study_minutes_per_week=300, goal=None, topics=None, force=False):
        context = self._build_context(candidate_id, target_date, study_minutes_per_week, goal, topics)
        system, user = self._prompt(context)
        await provider.ensure_available()
        raw = None
        parsed = None
        error_text = None
        for attempt in range(2):
            try:
                if attempt == 0:
                    raw = await provider.generate_with_system(system, user)
                else:
                    raw = await provider.generate_with_system(system, user + "\n\nLa respuesta anterior no fue JSON valido. Corrigela.\n" + str(raw) + "\nError: " + str(error_text))
                data = json.loads(raw)
                parsed = PreparationPlanOutput.model_validate(data)
                break
            except Exception as exc:
                error_text = str(exc)
                parsed = None
        if parsed is None:
            raise AdmissionError("malformed_llm_output", "El modelo devolvio un plan invalido.", 502)

        weeks = context["weeks"]
        available_total = study_minutes_per_week * weeks
        total = sum(a.estimated_minutes for a in parsed.activities)
        if total > available_total and total > 0:
            factor = available_total / total
            for activity in parsed.activities:
                activity.estimated_minutes = max(5, int(activity.estimated_minutes * factor))

        plan_id = str(uuid.uuid4())
        now = _now()
        with connect() as connection:
            connection.execute(
                "INSERT INTO preparation_plans (id, candidate_id, target_date, study_time_per_week, goal, topics, status, plan_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (plan_id, candidate_id, target_date, study_minutes_per_week, goal or "", json.dumps(topics or [], ensure_ascii=False), "active", json.dumps(parsed.model_dump(), ensure_ascii=False), now, now),
            )
            for activity in parsed.activities:
                connection.execute(
                    "INSERT INTO preparation_activities (id, plan_id, topic, title, description, estimated_minutes, week_number, day_label, status, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), plan_id, activity.topic, activity.title or activity.topic, activity.description, activity.estimated_minutes, activity.week, activity.day, "pending", now),
                )
            connection.commit()

        return self.get_plan(plan_id)

    def get_plan(self, plan_id: str):
        with connect() as connection:
            row = connection.execute("SELECT * FROM preparation_plans WHERE id = ?", (plan_id,)).fetchone()
        if row is None:
            raise AdmissionError("plan_not_found", "No existe el plan indicado.", 404)
        plan = {key: row[key] for key in row.keys()}
        plan["topics"] = json.loads(plan.get("topics") or "[]")
        plan["plan_json"] = json.loads(plan.get("plan_json") or "{}")
        with connect() as connection:
            rows = connection.execute("SELECT * FROM preparation_activities WHERE plan_id = ? ORDER BY week_number, created_at", (plan_id,)).fetchall()
        activities = [{key: r[key] for key in r.keys()} for r in rows]
        plan["activities"] = activities
        completed = sum(1 for a in activities if a.get("status") == "completed")
        plan["progress"] = {"completed": completed, "total": len(activities), "percent": round(100 * completed / len(activities), 1) if activities else 0}
        plan["disclaimer"] = DISCLAIMER
        return plan

    def get_active_plan(self, candidate_id: str):
        with connect() as connection:
            row = connection.execute("SELECT id FROM preparation_plans WHERE candidate_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1", (candidate_id,)).fetchone()
        if row is None:
            return None
        return self.get_plan(row["id"])

    def list_plans(self, candidate_id: str):
        with connect() as connection:
            rows = connection.execute("SELECT id FROM preparation_plans WHERE candidate_id = ? ORDER BY created_at DESC", (candidate_id,)).fetchall()
        return [self.get_plan(r["id"]) for r in rows]

    def update_activity(self, activity_id: str, status: str):
        if status not in {"pending", "completed"}:
            raise AdmissionError("invalid_status", "Estado de actividad invalido.", 422)
        now = _now() if status == "completed" else None
        with connect() as connection:
            connection.execute("UPDATE preparation_activities SET status = ?, completed_at = ? WHERE id = ?", (status, now, activity_id))
            connection.commit()
            row = connection.execute("SELECT plan_id FROM preparation_activities WHERE id = ?", (activity_id,)).fetchone()
        if row is None:
            raise AdmissionError("activity_not_found", "No existe la actividad indicada.", 404)
        return self.get_plan(row["plan_id"])

    def compare_interviews(self, candidate_id: str):
        return self._interview_summary(candidate_id)