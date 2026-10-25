"""Server-side Spanish PDF report generation for completed admissions interviews."""

from __future__ import annotations

import json
import re
import textwrap
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.core.errors import AdmissionError
from backend.app.db import connect
from backend.app.services.answer_evaluation_service import AnswerEvaluationService
from backend.app.services.candidate_service import CandidateService
from backend.app.services.cv_analysis_service import CVAnalysisService
from backend.app.services.interview_service import InterviewService
from backend.app.services.session_service import InterviewSessionService

DISCLAIMER = (
    "Simulacion academica independiente. Las puntuaciones son retroalimentacion "
    "generada por IA para preparacion del candidato; no constituyen una decision "
    "oficial de admision ni una medicion psicometrica validada."
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt_dt(value: str | None) -> str:
    if not value:
        return "No disponible"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(value)


def _mode_label(mode: str) -> str:
    return {
        "quick": "Rapida (5 preguntas)",
        "standard": "Estandar (10 preguntas)",
        "complete": "Completa (15 preguntas)",
    }.get(mode, mode or "No disponible")


class SimplePDF:
    PAGE_WIDTH = 595
    PAGE_HEIGHT = 842
    MARGIN = 50

    def __init__(self) -> None:
        self.pages = []
        self._new_page()

    def _new_page(self) -> None:
        self.pages.append(bytearray())
        self.y = self.PAGE_HEIGHT - self.MARGIN

    def _ensure_space(self, needed: int) -> None:
        if self.y - needed < self.MARGIN + 20:
            self._new_page()

    @staticmethod
    def _escape(text: str) -> bytes:
        try:
            data = str(text).encode("cp1252", errors="replace")
        except Exception:
            data = str(text).encode("latin-1", errors="replace")
        out = bytearray()
        for byte in data:
            if byte in (0x28, 0x29, 0x5C):
                out.extend(b"\\" + bytes([byte]))
            elif byte < 0x20 or byte == 0x7F:
                out.extend(b"\\%03o" % byte)
            else:
                out.append(byte)
        return bytes(out)

    def _put(self, command: bytes) -> None:
        self.pages[-1].extend(command + b"\n")

    def text(self, value: str, size: int = 11, bold: bool = False, italic: bool = False,
             indent: int = 0, space_after: int = 4, color=None) -> None:
        font = "/F2" if bold else ("/F3" if italic else "/F1")
        usable = self.PAGE_WIDTH - 2 * self.MARGIN - indent
        chars = max(12, int(usable / max(1, size * 0.47)))
        lines = []
        for paragraph in str(value).split("\n"):
            wrapped = textwrap.wrap(paragraph, width=chars, break_long_words=True, break_on_hyphens=False)
            lines.extend(wrapped if wrapped else [""])
        line_height = int(size * 1.35)
        for line in lines:
            self._ensure_space(line_height)
            x = self.MARGIN + indent
            escaped = self._escape(line)
            color_cmd = b""
            if color is not None:
                color_cmd = b"%.3f %.3f %.3f rg " % (
                    color[0] / 255.0, color[1] / 255.0, color[2] / 255.0
                )
            self._put(
                b"BT " + color_cmd + font.encode() + b" " + str(size).encode() + b" Tf "
                + str(x).encode() + b" " + str(self.y).encode() + b" Td (" + escaped + b") Tj ET"
            )
            self.y -= line_height
        self.y -= space_after

    def heading(self, value: str, size: int = 14) -> None:
        self._ensure_space(size * 2 + 8)
        self.y -= 4
        self.text(value, size=size, bold=True, space_after=6, color=(30, 60, 120))

    def subheading(self, value: str) -> None:
        self.text(value, size=12, bold=True, space_after=2, color=(50, 50, 50))

    def bullet(self, value: str, indent: int = 18) -> None:
        self.text("• " + str(value), size=11, indent=indent, space_after=2)

    def rule(self) -> None:
        self._ensure_space(8)
        self._put(
            b"0.8 w " + str(self.MARGIN).encode() + b" " + str(self.y).encode()
            + b" m " + str(self.PAGE_WIDTH - self.MARGIN).encode() + b" " + str(self.y).encode() + b" l S"
        )
        self.y -= 8

    def spacer(self, amount: int = 6) -> None:
        self.y -= amount
        if self.y < self.MARGIN + 20:
            self._new_page()

    def to_bytes(self) -> bytes:
        total = len(self.pages)
        objects = []
        page_object_numbers = list(range(3, 3 + total))
        font_numbers = [3 + total, 4 + total, 5 + total]
        content_numbers = list(range(6 + total, 6 + total + total))
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        kids = b" ".join(b"%d 0 R" % n for n in page_object_numbers)
        objects.append(b"<< /Type /Pages /Kids [" + kids + b"] /Count " + str(total).encode() + b" >>")
        for number in page_object_numbers:
            content_ref = content_numbers[page_object_numbers.index(number)]
            objects.append(
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 " + str(self.PAGE_WIDTH).encode() + b" "
                + str(self.PAGE_HEIGHT).encode() + b"] /Resources << /Font << /F1 " + str(font_numbers[0]).encode()
                + b" 0 R /F2 " + str(font_numbers[1]).encode() + b" 0 R /F3 " + str(font_numbers[2]).encode()
                + b" 0 R >> >> /Contents " + str(content_ref).encode() + b" 0 R >>"
            )
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>")

        for index, page in enumerate(self.pages):
            footer = "Pagina %d de %d" % (index + 1, total)
            footer_cmd = (
                b"BT /F1 9 Tf " + str(self.MARGIN).encode() + b" 30 Td ("
                + self._escape(footer) + b") Tj ET\n"
            )
            page.extend(footer_cmd)

        for page in self.pages:
            stream = bytes(page)
            objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream")

        output = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(output))
            output.extend(b"%d 0 obj\n" % index)
            output.extend(obj)
            output.extend(b"\nendobj\n")
        xref_offset = len(output)
        output.extend(b"xref\n0 %d\n" % (len(objects) + 1))
        output.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            output.extend(b"%010d 00000 n \n" % offset)
        output.extend(
            b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objects) + 1, xref_offset)
        )
        return bytes(output)


class ReportService:
    def __init__(self) -> None:
        self.candidates = CandidateService()
        self.sessions = InterviewSessionService()
        self.interviews = InterviewService()
        self.cv = CVAnalysisService()
        self.evaluations = AnswerEvaluationService()

    def _collect(self, session_id: str) -> dict[str, Any]:
        session = self.sessions.get(session_id)
        if session is None:
            raise AdmissionError("session_not_found", "No existe la sesion de entrevista indicada.", 404)
        if session.get("status") != "completed":
            raise AdmissionError("interview_not_completed", "El reporte solo esta disponible para entrevistas finalizadas.", 409)
        candidate = self.candidates.get(session["candidate_id"])
        if candidate is None:
            raise AdmissionError("candidate_not_found", "No existe el candidato asociado a la sesion.", 404)

        with connect() as connection:
            answer_rows = connection.execute(
                "SELECT a.id, a.question_id, a.candidate_answer, a.created_at, q.prompt, q.category "
                "FROM answers a LEFT JOIN questions q ON q.id = a.question_id "
                "WHERE a.session_id = ? ORDER BY a.created_at",
                (session_id,),
            ).fetchall()
            evaluation_rows = connection.execute(
                "SELECT * FROM evaluations WHERE session_id = ? ORDER BY created_at", (session_id,)
            ).fetchall()
            cv_row = connection.execute(
                "SELECT * FROM cv_analyses WHERE candidate_id = ? AND status = 'completed' "
                "ORDER BY COALESCE(analyzed_at, created_at) DESC LIMIT 1",
                (candidate["id"],),
            ).fetchone()

        evaluations_by_answer = {}
        for row in evaluation_rows:
            evaluations_by_answer[row["answer_id"]] = self.evaluations._row_to_dict(
                {key: row[key] for key in row.keys()}
            )

        items = []
        for row in answer_rows:
            answer_id = row["id"]
            evaluation = evaluations_by_answer.get(answer_id)
            items.append({
                "answer_id": answer_id,
                "question_id": row["question_id"],
                "question_prompt": row["prompt"] or (evaluation or {}).get("question_prompt") or "",
                "category": row["category"] or "general",
                "answer": row["candidate_answer"] or "",
                "created_at": row["created_at"],
                "evaluation": evaluation,
            })

        cv_analysis = None
        if cv_row is not None:
            cv_analysis = self.cv._row_to_dict({key: cv_row[key] for key in cv_row.keys()})

        scores = [item["evaluation"]["overall_score"] for item in items if item["evaluation"] and item["evaluation"].get("overall_score") is not None]
        average = round(sum(scores) / len(scores), 1) if scores else None

        return {
            "session": session,
            "candidate": candidate,
            "items": items,
            "cv_analysis": cv_analysis,
            "average_score": average,
            "completed_count": len(items),
            "evaluated_count": len(scores),
        }

    def _safe_filename(self, candidate_name: str, session_id: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9_-]+", "_", candidate_name or "candidato").strip("_")
        slug = slug[:40] or "candidato"
        return "reporte_entrevista_%s_%s.pdf" % (slug, session_id[:8])

    def generate(self, session_id: str) -> tuple[bytes, str]:
        data = self._collect(session_id)
        pdf = self._render(data)
        filename = self._safe_filename(data["candidate"]["full_name"], session_id)
        return pdf, filename

    def _render(self, data: dict[str, Any]) -> bytes:
        pdf = SimplePDF()
        session = data["session"]
        candidate = data["candidate"]
        items = data["items"]
        cv = data["cv_analysis"]
        average = data["average_score"]

        pdf.heading("AI Admission Simulator", size=20)
        pdf.text("Reporte de entrevista de admision simulada", size=12, italic=True, space_after=2)
        pdf.text("Maestria en Inteligencia Artificial - Instituto Tecnologico El Llano Aguascalientes", size=10, space_after=8)
        pdf.rule()

        pdf.subheading("Datos del reporte")
        pdf.text("Candidato: " + str(candidate.get("full_name") or "No disponible"), size=11)
        pdf.text("Correo: " + str(candidate.get("email") or "No disponible"), size=11)
        pdf.text("Fecha de generacion: " + _fmt_dt(_now().isoformat()), size=11)
        pdf.text("Fecha de entrevista: " + _fmt_dt(session.get("completed_at") or session.get("started_at") or session.get("created_at")), size=11)
        pdf.text("Modo de entrevista: " + _mode_label(session.get("mode", "")), size=11)
        pdf.text("Preguntas completadas: " + str(data["completed_count"]), size=11)
        pdf.text("Evaluaciones disponibles: " + str(data["evaluated_count"]), size=11)
        if average is None:
            pdf.text("Puntaje promedio de preparacion (simulacion): No disponible (faltan evaluaciones).", size=11, bold=True)
        else:
            pdf.text("Puntaje promedio de preparacion (simulacion): " + str(average) + " / 100", size=11, bold=True)
            pdf.text("Calculo: promedio aritmetico de " + str(data["evaluated_count"]) + " evaluaciones individuales. Las respuestas sin evaluacion no se tratan como cero.", size=9, italic=True, space_after=8)
        pdf.rule()

        pdf.heading("Aviso academico")
        pdf.text(DISCLAIMER, size=10)
        pdf.text("Este reporte no estima la probabilidad real de admision del candidato.", size=10, bold=True)

        pdf.heading("Resumen ejecutivo")
        if average is None:
            pdf.text("No hay evaluaciones suficientes para generar un resumen cuantitativo. Revise las evaluaciones individuales cuando esten disponibles.", size=11)
        else:
            pdf.text(
                "El candidato completo " + str(data["completed_count"]) + " preguntas y "
                + str(data["evaluated_count"]) + " de ellas cuentan con evaluacion simulada. "
                + "El puntaje promedio de preparacion es " + str(average) + " de 100. "
                + "Las puntuaciones identicas en respuestas distintas no constituyen prueba de precision de la evaluacion.",
                size=11,
            )
        all_strengths = []
        all_weaknesses = []
        all_recommendations = []
        for item in items:
            ev = item["evaluation"] or {}
            all_strengths.extend(ev.get("strengths") or [])
            all_weaknesses.extend(ev.get("weaknesses") or ev.get("areas_for_improvement") or [])
            all_recommendations.extend(ev.get("recommendations") or [])
        if all_strengths:
            pdf.subheading("Fortalezas observadas")
            for value in sorted(set(all_strengths)):
                pdf.bullet(value)
        if all_weaknesses:
            pdf.subheading("Areas de mejora")
            for value in sorted(set(all_weaknesses)):
                pdf.bullet(value)
        if all_recommendations:
            pdf.subheading("Recomendaciones generales")
            for value in sorted(set(all_recommendations)):
                pdf.bullet(value)

        pdf.heading("Preguntas, respuestas y evaluaciones")
        for index, item in enumerate(items, start=1):
            pdf.subheading("Pregunta %d - %s" % (index, item["category"].replace("_", " ").title()))
            pdf.text("Pregunta: " + (item["question_prompt"] or "No disponible"), size=11, bold=True)
            pdf.text("Respuesta del candidato: " + (item["answer"] or "No disponible"), size=11)
            ev = item["evaluation"]
            if not ev:
                pdf.text("Evaluacion: No disponible para esta respuesta.", size=11, italic=True)
                pdf.spacer(4)
                continue
            score = ev.get("overall_score", ev.get("score"))
            pdf.text("Evaluacion simulada: " + str(score if score is not None else "No disponible") + " / 100", size=11, bold=True)
            criteria = ev.get("criteria") or []
            if criteria:
                pdf.text("Criterios:", size=10, bold=True, space_after=2)
                for criterion in criteria:
                    if not isinstance(criterion, dict):
                        continue
                    name = criterion.get("name") or criterion.get("criterion") or "Criterio"
                    value = criterion.get("score")
                    explanation = criterion.get("explanation") or criterion.get("status") or ""
                    pdf.bullet("%s: %s - %s" % (name, value if value is not None else "No disponible", explanation))
            strengths = ev.get("strengths") or []
            weaknesses = ev.get("weaknesses") or ev.get("areas_for_improvement") or []
            recommendations = ev.get("recommendations") or []
            if strengths:
                pdf.text("Fortalezas:", size=10, bold=True, space_after=2)
                for value in strengths:
                    pdf.bullet(value)
            if weaknesses:
                pdf.text("Areas de mejora:", size=10, bold=True, space_after=2)
                for value in weaknesses:
                    pdf.bullet(value)
            if recommendations:
                pdf.text("Recomendaciones:", size=10, bold=True, space_after=2)
                for value in recommendations:
                    pdf.bullet(value)
            revised = ev.get("revised_answer") or ev.get("improved_answer")
            if revised:
                pdf.text("Respuesta mejorada sugerida: " + revised, size=10, italic=True)
            tip = ev.get("practice_tip")
            if tip:
                pdf.text("Consejo de practica: " + tip, size=10)
            tech = ev.get("technical_accuracy")
            if isinstance(tech, dict) and tech.get("classification"):
                pdf.text("Precision tecnica: " + str(tech.get("classification")), size=10)
            stress = ev.get("stress_management")
            if isinstance(stress, dict):
                addresses = ", ".join(stress.get("addresses") or []) or "No disponible"
                missing = ", ".join(stress.get("missing") or []) or "No disponible"
                suggestions = ", ".join(stress.get("suggestions") or []) or "No disponible"
                pdf.text("Manejo del estres - aborda: " + addresses, size=10)
                pdf.text("Manejo del estres - falta: " + missing, size=10)
                pdf.text("Manejo del estres - sugerencias: " + suggestions, size=10)
            disclaimer = ev.get("disclaimer")
            if disclaimer:
                pdf.text(disclaimer, size=8, italic=True)
            pdf.spacer(6)

        pdf.heading("Retroalimentacion tecnica")
        tech_items = [item["evaluation"].get("technical_accuracy") for item in items if item["evaluation"] and isinstance(item["evaluation"].get("technical_accuracy"), dict)]
        if tech_items:
            classifications = {}
            for tech in tech_items:
                key = tech.get("classification") or "sin_clasificacion"
                classifications[key] = classifications.get(key, 0) + 1
            for key, count in classifications.items():
                pdf.bullet("%s: %d respuesta(s)" % (key, count))
            pdf.text("Consulte las evaluaciones individuales para el detalle de cada afirmacion tecnica.", size=10, italic=True)
        else:
            pdf.text("No disponible: no se registraron evaluaciones con retroalimentacion tecnica.", size=10, italic=True)

        pdf.heading("Manejo del estres")
        stress_items = [item["evaluation"].get("stress_management") for item in items if item["evaluation"] and isinstance(item["evaluation"].get("stress_management"), dict)]
        if stress_items:
            addresses = sorted({value for stress in stress_items for value in (stress.get("addresses") or [])})
            missing = sorted({value for stress in stress_items for value in (stress.get("missing") or [])})
            suggestions = sorted({value for stress in stress_items for value in (stress.get("suggestions") or [])})
            if addresses:
                pdf.text("Aspectos abordados: " + ", ".join(addresses), size=11)
            if missing:
                pdf.text("Aspectos faltantes: " + ", ".join(missing), size=11)
            if suggestions:
                pdf.text("Sugerencias: " + ", ".join(suggestions), size=11)
        else:
            pdf.text("No disponible: no se registraron evaluaciones de manejo del estres.", size=10, italic=True)

        pdf.heading("Recomendaciones personalizadas")
        if all_recommendations:
            for value in sorted(set(all_recommendations)):
                pdf.bullet(value)
        else:
            pdf.text("No disponible: no se registraron recomendaciones personalizadas.", size=10, italic=True)

        pdf.heading("Mensaje de cierre personalizado")
        name = candidate.get("full_name") or "candidato"
        if average is None:
            closing = "Gracias, %s. Completa la entrevista y genera evaluaciones para recibir retroalimentacion mas detallada. Sigue practicando con ejemplos concretos y estructura tus respuestas." % name
        elif average >= 75:
            closing = "Excelente preparacion, %s. Manten la claridad y profundiza en los ejemplos tecnicos; tu desempeno simulado es solido." % name
        elif average >= 60:
            closing = "Buen avance, %s. Refuerza los conceptos tecnicos y agrega ejemplos concretos para elevar tu preparacion." % name
        else:
            closing = "Gracias, %s. Enfoca tu preparacion en los fundamentos tecnicos y en comunicar tus experiencias con claridad." % name
        pdf.text(closing, size=11)
        pdf.text("Recuerda que esta simulacion no determina una decision oficial de admision.", size=10, italic=True)

        pdf.heading("CV asociado")
        if cv is None:
            pdf.text("No disponible: no se encontro un analisis de CV completado y asociado a este candidato.", size=10, italic=True)
        else:
            pdf.text("Archivo analizado: " + str(cv.get("file_name") or "No disponible"), size=10)
            analysis = cv.get("analysis") or {}
            summary_text = analysis.get("professional_summary")
            if summary_text:
                pdf.text("Resumen profesional: " + summary_text, size=10)
            strengths = analysis.get("strengths") or []
            if strengths:
                pdf.text("Fortalezas del CV:", size=10, bold=True, space_after=2)
                for value in strengths:
                    pdf.bullet(value)
            missing = analysis.get("missing_or_unclear_evidence") or []
            if missing:
                pdf.text("Evidencia faltante o poco clara:", size=10, bold=True, space_after=2)
                for value in missing:
                    pdf.bullet(value)
            recommendations = analysis.get("recommendations") or []
            if recommendations:
                pdf.text("Recomendaciones del CV:", size=10, bold=True, space_after=2)
                for value in recommendations:
                    pdf.bullet(value)
            requirements = analysis.get("requirement_classification") or analysis.get("clasificacion_requisitos") or []
            if requirements:
                pdf.text("Clasificacion de requisitos del CV:", size=10, bold=True, space_after=2)
                for req in requirements:
                    if not isinstance(req, dict):
                        continue
                    pdf.bullet("%s (%s): %s" % (
                        req.get("requirement") or "Requisito",
                        req.get("status") or "sin estado",
                        req.get("evidence") or "Sin evidencia registrada",
                    ))
            pdf.text("No se incluye el texto completo del CV para proteger la privacidad del candidato.", size=9, italic=True)

        pdf.heading("Nota de integridad del reporte")
        pdf.text(
            "Los puntajes se derivan de registros reales de evaluacion. El puntaje promedio es un calculo documentado (media aritmetica). "
            "Las evaluaciones faltantes no se tratan como cero. Este reporte no estima una probabilidad real de admision.",
            size=10,
        )
        return pdf.to_bytes()
