"""Academic CV analysis engine for AI admission preparation."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.api.schemas import CVAnalysisLLMOutput
from backend.app.core.config import PROJECT_ROOT, settings
from backend.app.core.errors import AdmissionError
from backend.app.db import connect
from backend.app.prompts.cv_evaluator import CV_EVALUATOR_SYSTEM_PROMPT
from backend.app.providers.base import LLMProvider, ProviderUnavailableError
from backend.app.services.candidate_service import CandidateService
from backend.app.utils.document_extract import extract


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


PROGRAMMING_LANGUAGES = [
    "Python", "Java", "C", "C++", "C#", "JavaScript", "TypeScript", "R", "MATLAB",
    "Go", "Rust", "Julia", "Scala", "Kotlin", "Swift", "PHP", "Ruby", "SQL",
]
DATABASES = [
    "SQL", "MySQL", "PostgreSQL", "SQLite", "MongoDB", "Redis", "Oracle",
    "SQL Server", "MariaDB", "Firebase", "Cassandra", "Neo4j",
]
AI_TERMS = [
    "inteligencia artificial", "machine learning", "deep learning", "aprendizaje automático",
    "aprendizaje profundo", "redes neuronales", "nlp", "visión por computadora",
    "computer vision", "procesamiento de lenguaje natural", "data science", "ciencia de datos",
]


class CVAnalysisService:
    def __init__(self, storage_dir=None, max_bytes=None) -> None:
        self.candidates = CandidateService()
        self.storage_dir = Path(storage_dir) if storage_dir is not None else Path(settings.cv_storage_path)
        if not self.storage_dir.is_absolute():
            self.storage_dir = PROJECT_ROOT / self.storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes if max_bytes is not None else settings.cv_max_upload_bytes

    def _safe_filename(self, file_name: str) -> str:
        base = Path(file_name).name.strip()
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
        safe = safe.strip("._")
        if not safe:
            safe = "cv.pdf"
        if not safe.lower().endswith(".pdf"):
            safe += ".pdf"
        return safe[:180]

    def _candidate(self, candidate_id, full_name, email):
        if candidate_id:
            candidate = self.candidates.get(candidate_id)
            if candidate is None:
                raise AdmissionError("candidate_not_found", "No existe el candidato indicado.", 404)
            return candidate
        return self.candidates.create(full_name or "Candidato de simulación", email)

    def _validate_and_extract(self, file_name, data):
        if not file_name or Path(file_name).suffix.lower() != ".pdf":
            raise AdmissionError("invalid_file_type", "Solo se permiten archivos PDF.", 415)
        if not data:
            raise AdmissionError("empty_file", "El archivo está vacío.", 400)
        if len(data) > self.max_bytes:
            raise AdmissionError("file_size", "El archivo excede el tamaño máximo permitido.", 413)
        if not data.startswith(b"%PDF-"):
            raise AdmissionError("invalid_file", "El archivo no es un PDF válido.", 400)
        try:
            blocks = extract(data, ".pdf")
        except AdmissionError as exc:
            raise exc
        except Exception as exc:
            raise AdmissionError("corrupted_pdf", "El PDF está dañado o no se pudo leer.", 400) from exc
        text = "\n".join(block.get("text", "") for block in blocks)
        if not text.strip():
            raise AdmissionError("no_text", "El PDF no contiene texto extraíble. Los PDF escaneados requieren OCR.", 400)
        evidence = self._extract_evidence(blocks, text)
        summary = {
            "file_name": file_name,
            "extension": ".pdf",
            "block_count": len(blocks),
            "character_count": len(text),
            "text_excerpt": text[:500],
        }
        return blocks, text, evidence, summary

    def _extract_evidence(self, blocks, text):
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        section_headers = (
            "educación", "formación", "estudios", "experiencia", "habilidades",
            "proyectos", "certificaciones", "investigación", "perfil", "resumen",
        )
        sections = {}
        current = "General"
        for line in lines:
            lowered = line.lower()
            if len(line) <= 90 and any(header in lowered for header in section_headers):
                current = line
                sections.setdefault(current, [])
            else:
                sections.setdefault(current, []).append(line)

        def snippets_for(keywords, limit=20):
            result = []
            seen = set()
            for line in lines:
                lowered = line.lower()
                if any(keyword in lowered for keyword in keywords) and line not in seen:
                    seen.add(line)
                    result.append(line[:500])
                    if len(result) >= limit:
                        break
            return result

        def find_terms(terms):
            found = []
            for term in terms:
                if re.search(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE):
                    found.append(term)
            return sorted(set(found), key=str.lower)

        programming = find_terms(PROGRAMMING_LANGUAGES)
        databases = find_terms(DATABASES)
        ai_experience = snippets_for(AI_TERMS, 20)
        return {
            "sections_detected": list(sections.keys())[:40],
            "education": snippets_for(["licenciatura", "ingeniería", "maestría", "doctorado", "título", "grado", "universidad", "instituto", "formación académica", "estudios"], 20),
            "degrees": snippets_for(["licenciatura", "ingeniería", "maestría", "doctorado", "título", "grado", "bachelor", "master"], 20),
            "programming_languages": programming,
            "databases": databases,
            "technical_skills": snippets_for(["habilidades", "skills", "tecnologías", "framework", "herramientas", "lenguajes"], 20),
            "software_projects": snippets_for(["proyecto", "project", "desarrollo", "aplicación", "sistema"], 20),
            "ai_experience": ai_experience,
            "professional_experience": snippets_for(["experiencia profesional", "experiencia laboral", "trabajo", "empresa", "puesto", "cargo", "empleo"], 20),
            "certifications": snippets_for(["certificación", "certificado", "certification", "curso", "diploma"], 20),
            "research_interests": snippets_for(["investigación", "research", "interés", "línea de investigación"], 20),
            "evidence_snippets": [
                {"page": block.get("page"), "paragraph": block.get("paragraph"), "text": (block.get("text") or "")[:300]}
                for block in blocks[:25]
            ],
            "text_excerpt": text[:1500],
        }

    def _storage_path_for(self, candidate_id, analysis_id):
        directory = self.storage_dir / candidate_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{analysis_id}.pdf"

    def _get_row_or_404(self, analysis_id):
        with connect() as connection:
            row = connection.execute("SELECT * FROM cv_analyses WHERE id = ?", (analysis_id,)).fetchone()
        if row is None:
            raise AdmissionError("analysis_not_found", "No existe el análisis de CV indicado.", 404)
        return row

    def _row_to_dict(self, row):
        extracted = json.loads(row["extracted_evidence"] or "{}")
        analysis = json.loads(row["analysis_result"] or "{}")
        summary = json.loads(row["summary"] or "{}")
        error = None
        if row["error_code"]:
            error = {"code": row["error_code"], "message": row["error_message"] or ""}
        return {
            "id": row["id"],
            "analysis_id": row["id"],
            "candidate_id": row["candidate_id"],
            "file_name": row["file_name"],
            "original_file_name": row["file_name"],
            "content_type": row["content_type"],
            "file_size": row["file_size"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "analyzed_at": row["analyzed_at"],
            "analysis_date": row["analyzed_at"],
            "summary": summary,
            "extraction_summary": summary,
            "extracted_evidence": extracted,
            "analysis": analysis,
            "result": analysis,
            "error": error,
        }


    def upload_cv(self, candidate_id=None, full_name=None, email=None, file_name=None, data=None, content_type=None):
        blocks, text, evidence, summary = self._validate_and_extract(file_name, data)
        candidate = self._candidate(candidate_id, full_name, email)
        analysis_id = str(uuid.uuid4())
        safe_name = self._safe_filename(file_name)
        stored_path = self._storage_path_for(candidate["id"], analysis_id)
        now = _now()
        sha256 = hashlib.sha256(data).hexdigest()
        try:
            stored_path.write_bytes(data)
            with connect() as connection:
                connection.execute(
                    "INSERT INTO cv_analyses (id, candidate_id, file_name, stored_path, content_type, file_size, sha256, "
                    "status, extracted_evidence, analysis_result, summary, created_at, updated_at, analyzed_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 'uploaded', ?, '{}', ?, ?, ?, NULL)",
                    (
                        analysis_id,
                        candidate["id"],
                        safe_name,
                        str(stored_path),
                        content_type or "application/pdf",
                        len(data),
                        sha256,
                        json.dumps(evidence, ensure_ascii=False),
                        json.dumps(summary, ensure_ascii=False),
                        now,
                        now,
                    ),
                )
                connection.commit()
            row = self._get_row_or_404(analysis_id)
            return self._row_to_dict(row)
        except Exception:
            try:
                if stored_path.exists():
                    stored_path.unlink()
            except OSError:
                pass
            raise

    def analyze(self, file_name, data):
        blocks, text, evidence, summary = self._validate_and_extract(file_name, data)
        return {**summary, "evidence": evidence}

    def analyze_and_store(self, candidate_id, file_name, data):
        return self.upload_cv(candidate_id=candidate_id, file_name=file_name, data=data)

    async def start_analysis(self, analysis_id, provider):
        row = self._get_row_or_404(analysis_id)
        stored_path = Path(row["stored_path"])
        if not stored_path.exists():
            raise AdmissionError("file_not_found", "No se encontró el archivo CV almacenado.", 404)
        data = stored_path.read_bytes()
        blocks, text, evidence, summary = self._validate_and_extract(row["file_name"], data)
        now = _now()
        with connect() as connection:
            connection.execute(
                "UPDATE cv_analyses SET status = 'analyzing', extracted_evidence = ?, summary = ?, updated_at = ?, "
                "error_code = NULL, error_message = NULL WHERE id = ?",
                (json.dumps(evidence, ensure_ascii=False), json.dumps(summary, ensure_ascii=False), now, analysis_id),
            )
            connection.commit()

        try:
            await provider.ensure_available()
            parsed = await self._evaluate(provider, evidence, text)
            requirements = self._normalize_requirements(parsed.requirement_classification)
            evaluation = self._build_evaluation(parsed, requirements)
            analyzed_at = _now()
            with connect() as connection:
                connection.execute(
                    "UPDATE cv_analyses SET status = 'completed', analysis_result = ?, analyzed_at = ?, updated_at = ?, "
                    "error_code = NULL, error_message = NULL WHERE id = ?",
                    (json.dumps(evaluation, ensure_ascii=False), analyzed_at, analyzed_at, analysis_id),
                )
                connection.commit()
        except AdmissionError as exc:
            self._mark_failed(analysis_id, exc.code, exc.message)
            raise
        except ProviderUnavailableError as exc:
            self._mark_failed(analysis_id, "provider_unavailable", "El proveedor local de IA no está disponible.")
            raise ProviderUnavailableError() from exc
        except Exception as exc:
            self._mark_failed(analysis_id, "analysis_failed", "No se pudo completar el análisis del CV.")
            raise AdmissionError("analysis_failed", "No se pudo completar el análisis del CV.", 500) from exc

        return self._row_to_dict(self._get_row_or_404(analysis_id))

    async def _evaluate(self, provider, evidence, text):
        system_prompt = CV_EVALUATOR_SYSTEM_PROMPT + "\n\nResponde únicamente con JSON válido."
        user_prompt = (
            "Analiza el siguiente CV para admisión a la Maestría en IA.\n\n"
            "Evidencia estructurada extraída:\n"
            f"{json.dumps(evidence, ensure_ascii=False)[:18000]}\n\n"
            "Texto del CV (extracto acotado):\n"
            f"{text[:12000]}\n\n"
            "Clasifica los requisitos obligatorios y recomendados. "
            "Devuelve JSON con las claves solicitadas."
        )

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
                from backend.app.api.schemas import CVAnalysisLLMOutput as OutputSchema
                parsed = OutputSchema.model_validate(data)
                break
            except (json.JSONDecodeError, ValueError, Exception) as exc:
                error_text = str(exc)
                parsed = None
        if parsed is None:
            raise AdmissionError("malformed_llm_output", "El modelo devolvió una respuesta inválida.", 502)
        return parsed

    def _normalize_requirements(self, classified):
        defaults = [
            {
                "requirement": "Egreso de una carrera de Ingeniería o Licenciatura en área afín a computación y/o inteligencia artificial.",
                "category": "mandatory",
                "status": "not_demonstrated",
                "evidence": "",
            },
            {
                "requirement": "Conocimientos previos en algún lenguaje de alto nivel.",
                "category": "recommended",
                "status": "not_demonstrated",
                "evidence": "",
            },
            {
                "requirement": "Manejo de bases de datos.",
                "category": "recommended",
                "status": "not_demonstrated",
                "evidence": "",
            },
            {
                "requirement": "Facilidad para comprender conceptos abstractos y formular algoritmos para la resolución de problemas.",
                "category": "recommended",
                "status": "not_demonstrated",
                "evidence": "",
            },
        ]
        result = [item.model_dump() if hasattr(item, "model_dump") else dict(item) for item in classified]
        for default in defaults:
            if not any(item.get("category") == default["category"] and item.get("requirement", "").lower().startswith(default["requirement"][:20].lower()) for item in result):
                result.append(dict(default))
        if not any(item.get("category") == "mandatory" for item in result):
            result.insert(0, dict(defaults[0]))
        return result

    def _build_evaluation(self, parsed, requirements):
        evaluation = {
            "professional_summary": parsed.professional_summary,
            "resumen_profesional": parsed.professional_summary,
            "strengths": parsed.strengths,
            "fortalezas": parsed.strengths,
            "missing_or_unclear_evidence": parsed.missing_or_unclear_evidence,
            "evidencia_faltante_o_poco_clara": parsed.missing_or_unclear_evidence,
            "recommendations": parsed.recommendations,
            "recomendaciones": parsed.recommendations,
            "requirement_classification": requirements,
            "clasificacion_requisitos": requirements,
            "wording_improvements": parsed.wording_improvements,
            "mejoras_redaccion": parsed.wording_improvements,
            "feedback": parsed.feedback,
            "retroalimentacion_profesional": parsed.feedback,
            "disclaimer": "Análisis generado por IA para preparación del candidato. No constituye una decisión oficial de admisión.",
        }
        return evaluation

    def _mark_failed(self, analysis_id, code, message):
        now = _now()
        with connect() as connection:
            connection.execute(
                "UPDATE cv_analyses SET status = 'failed', error_code = ?, error_message = ?, updated_at = ? WHERE id = ?",
                (code, message, now, analysis_id),
            )
            connection.commit()

    def get_analysis(self, analysis_id):
        return self._row_to_dict(self._get_row_or_404(analysis_id))

    def get_status(self, analysis_id):
        row = self._get_row_or_404(analysis_id)
        data = self._row_to_dict(row)
        return {
            "id": data["id"],
            "analysis_id": data["analysis_id"],
            "candidate_id": data["candidate_id"],
            "status": data["status"],
            "analyzed_at": data["analyzed_at"],
            "analysis_date": data["analysis_date"],
            "error": data["error"],
        }

    def delete_cv(self, analysis_id):
        row = self._get_row_or_404(analysis_id)
        stored_path = Path(row["stored_path"]) if row["stored_path"] else None
        if stored_path is not None and stored_path.exists():
            try:
                stored_path.unlink()
            except OSError:
                pass
            try:
                if stored_path.parent.exists() and not any(stored_path.parent.iterdir()):
                    stored_path.parent.rmdir()
            except OSError:
                pass
        with connect() as connection:
            connection.execute("DELETE FROM cv_analyses WHERE id = ?", (analysis_id,))
            connection.commit()
        return {"deleted": True, "analysis_id": analysis_id}

    def get_result(self, analysis_id):
        return self.get_analysis(analysis_id)

    def get_results(self, analysis_id):
        return self.get_analysis(analysis_id)

    def retrieve_analysis(self, analysis_id):
        return self.get_analysis(analysis_id)

    def delete_analysis(self, analysis_id):
        return self.delete_cv(analysis_id)

    def delete(self, analysis_id):
        return self.delete_cv(analysis_id)

    def upload(self, *args, **kwargs):
        return self.upload_cv(*args, **kwargs)

    async def analyze_stored(self, analysis_id, provider):
        return await self.start_analysis(analysis_id, provider)

    async def start(self, analysis_id, provider):
        return await self.start_analysis(analysis_id, provider)
