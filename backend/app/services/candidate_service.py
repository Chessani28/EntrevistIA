"""Candidate profile foundation."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from backend.app.core.errors import AdmissionError
from backend.app.db import connect


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_UNSET = object()


class CandidateService:
    def create(self, full_name: str, email: str | None = None, academic_profile: dict | None = None) -> dict:
        candidate_id = str(uuid.uuid4())
        with connect() as connection:
            connection.execute(
                "INSERT INTO candidates (id, full_name, email, academic_profile, created_at) VALUES (?, ?, ?, ?, ?)",
                (candidate_id, full_name, email, json.dumps(academic_profile or {}, ensure_ascii=False), _now()),
            )
            connection.commit()
        return self.get(candidate_id)

    def get(self, candidate_id: str) -> dict | None:
        with connect() as connection:
            row = connection.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        if row is None:
            return None
        return {"id": row["id"], "full_name": row["full_name"], "email": row["email"],
                "academic_profile": json.loads(row["academic_profile"] or "{}"), "created_at": row["created_at"]}

    def list(self, limit: int = 100) -> list[dict]:
        with connect() as connection:
            rows = connection.execute("SELECT id FROM candidates ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self.get(row["id"]) for row in rows]

    def update(self, candidate_id: str, *, full_name=None, email=_UNSET, academic_profile=None) -> dict:
        candidate = self.get(candidate_id)
        if candidate is None:
            raise AdmissionError("candidate_not_found", "No existe el candidato indicado.", 404)
        next_name = full_name if full_name is not None else candidate["full_name"]
        next_email = candidate["email"] if email is _UNSET else email
        next_profile = dict(candidate.get("academic_profile") or {})
        if isinstance(academic_profile, dict):
            next_profile.update(academic_profile)
        with connect() as connection:
            connection.execute(
                "UPDATE candidates SET full_name = ?, email = ?, academic_profile = ? WHERE id = ?",
                (next_name, next_email, json.dumps(next_profile, ensure_ascii=False), candidate_id),
            )
            connection.commit()
        return self.get(candidate_id)
