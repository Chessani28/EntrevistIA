"""Interview session persistence."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from backend.app.db import connect

_UNSET = object()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InterviewSessionService:
    def create(self, candidate_id: str, mode: str, question_count: int) -> dict:
        if question_count < 1:
            raise ValueError("question_count must be positive")
        if mode not in {"quick", "standard", "complete"}:
            raise ValueError("mode must be quick, standard, or complete")
        session_id = str(uuid.uuid4())
        now = _now()
        with connect() as connection:
            connection.execute(
                "INSERT INTO interview_sessions (id, candidate_id, mode, question_count, status, "
                "current_position, followup_context, created_at, updated_at) VALUES (?, ?, ?, ?, 'created', 0, '{}', ?, ?)",
                (session_id, candidate_id, mode, question_count, now, now),
            )
            connection.commit()
        return self.get(session_id)

    def get(self, session_id: str) -> dict | None:
        with connect() as connection:
            row = connection.execute("SELECT * FROM interview_sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        data = {key: row[key] for key in row.keys()}
        data["followup_context"] = json.loads(data.get("followup_context") or "{}")
        return data

    def update_status(self, session_id: str, status: str) -> None:
        with connect() as connection:
            connection.execute(
                "UPDATE interview_sessions SET status = ?, updated_at = ? WHERE id = ?",
                (status, _now(), session_id),
            )
            connection.commit()

    def update_progress(
        self,
        session_id: str,
        *,
        status: str | None = None,
        current_question_id: object = _UNSET,
        current_position: int | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
        followup_context: dict | None = None,
    ) -> None:
        fields = []
        values = []
        if status is not None:
            fields.append("status = ?")
            values.append(status)
        if current_question_id is not _UNSET:
            fields.append("current_question_id = ?")
            values.append(current_question_id)
        if current_position is not None:
            fields.append("current_position = ?")
            values.append(current_position)
        if started_at is not None:
            fields.append("started_at = ?")
            values.append(started_at)
        if completed_at is not None:
            fields.append("completed_at = ?")
            values.append(completed_at)
        if followup_context is not None:
            fields.append("followup_context = ?")
            values.append(json.dumps(followup_context, ensure_ascii=False))
        fields.append("updated_at = ?")
        values.append(_now())
        values.append(session_id)
        with connect() as connection:
            connection.execute(
                "UPDATE interview_sessions SET " + ", ".join(fields) + " WHERE id = ?",
                tuple(values),
            )
            connection.commit()

    def list_answers(self, session_id: str) -> list[dict]:
        with connect() as connection:
            rows = connection.execute(
                "SELECT * FROM answers WHERE session_id = ? ORDER BY created_at",
                (session_id,),
            ).fetchall()
        return [{key: row[key] for key in row.keys()} for row in rows]

    def list(self, limit: int = 100) -> list[dict]:
        with connect() as connection:
            rows = connection.execute('SELECT id FROM interview_sessions ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()
        return [self.get(row['id']) for row in rows]

