import json
from backend.app.providers.base import ProviderUnavailableError

class MockLLM:
    name = "mock"
    model = "mock-v1"

    async def is_available(self) -> bool:
        return True

    async def ensure_available(self) -> None:
        if not await self.is_available():
            raise ProviderUnavailableError()

    async def generate(self, message: str) -> str:
        return (
            "Respuesta simulada: no hay modelo de lenguaje ni documentación conectados. "
            "Esto es una prueba de conectividad, no asesoría académica."
        )

    async def generate_with_system(self, system_prompt: str, user_prompt: str) -> str:
        combined = (system_prompt + "\n" + user_prompt).lower()
        if "rubrica" in combined or "rúbrica" in combined or "criterios" in combined:
            stress = "estrés" in combined or "estres" in combined
            return json.dumps({
                "overall_score": 72,
                "criteria": [
                    {"name": "relevance", "score": 80, "status": "applicable", "explanation": "La respuesta aborda la pregunta principal."},
                    {"name": "clarity", "score": 75, "status": "applicable", "explanation": "La redacción es comprensible."},
                    {"name": "coherence", "score": 70, "status": "applicable", "explanation": "Las ideas se conectan de forma razonable."},
                    {"name": "technical_accuracy", "score": 65, "status": "applicable", "explanation": "Hay afirmaciones técnicas parcialmente respaldadas."},
                    {"name": "depth", "score": 60, "status": "applicable", "explanation": "La explicación podría profundizar más."},
                    {"name": "professionalism", "score": 78, "status": "applicable", "explanation": "El tono es profesional."},
                    {"name": "confidence", "score": 70, "status": "applicable", "explanation": "Se expresa confianza moderada."},
                    {"name": "naturalness", "score": 74, "status": "applicable", "explanation": "El lenguaje suena natural."},
                    {"name": "evidence_examples", "score": 55, "status": "insufficient_evidence", "explanation": "Faltan ejemplos concretos."},
                    {"name": "practical_reasoning", "score": 68, "status": "applicable", "explanation": "Hay razonamiento práctico básico."},
                ],
                "strengths": ["La respuesta comunica una intención clara.", "Mantiene un tono profesional."],
                "weaknesses": ["Faltan ejemplos concretos.", "La profundidad técnica es limitada."],
                "recommendations": ["Incluir un ejemplo breve de un proyecto real.", "Explicar con más detalle los conceptos técnicos."],
                "revised_answer": "Respuesta mejorada que conserva la experiencia del candidato y añade claridad.",
                "practice_tip": "Practica responder en 90 segundos con un ejemplo concreto.",
                "technical_accuracy": {"classification": "partially_correct", "claims": [{"claim": "Afirmación técnica", "classification": "partially_correct", "explanation": "No se puede verificar completamente desde la respuesta."}]},
                "stress_management": {"addresses": ["planificación del tiempo"], "missing": ["planificación de contingencias"], "suggestions": ["Detallar cómo priorizará actividades."]} if stress else None,
                "feedback": "Evaluación simulada para pruebas automatizadas. No constituye una decisión oficial de admisión."
            }, ensure_ascii=False)
        if "plan de preparacion" in combined or "plan de preparación" in combined or "actividades" in combined or "priority_topics" in combined or "mi plan" in combined:
            payload = {
                "summary": "Plan simulado basado en las entrevistas y el CV disponible.",
                "priority_topics": [
                    {"topic": "Algoritmos", "reason": "Area con menor evidencia en las entrevistas.", "priority": "high", "allocated_minutes_per_week": 60},
                    {"topic": "Bases de datos", "reason": "Se requiere mas evidencia practica.", "priority": "medium", "allocated_minutes_per_week": 40},
                ],
                "activities": [
                    {"topic": "Algoritmos", "title": "Practicar diseño de algoritmos", "description": "Resolver 3 problemas y explicar la complejidad.", "estimated_minutes": 45, "week": 1, "day": "Lunes", "resource": "Documentacion oficial y ejercicios abiertos"},
                    {"topic": "Bases de datos", "title": "Repasar SQL y JOIN", "description": "Escribir consultas con JOIN y subconsultas.", "estimated_minutes": 30, "week": 1, "day": "Miercoles", "resource": "Tutoriales introductorios"},
                    {"topic": "Comunicacion", "title": "Respuestas estructuradas", "description": "Practicar respuestas de 90 segundos con evidencia.", "estimated_minutes": 25, "week": 2, "day": "Viernes", "resource": "Practica oral"},
                ],
                "milestones": [{"week": 2, "title": "Primera entrevista de repaso", "success_criteria": "Completar todas las actividades de la semana 1"}],
                "review_sessions": ["Repaso de algoritmos al final de la semana 1"],
            }
            return __import__("json").dumps(payload, ensure_ascii=False)

        if "cv" in combined or "curriculum" in combined or "requisitos" in combined or "evidencia" in combined:
            return json.dumps({
                "professional_summary": "Perfil académico y técnico extraído del CV proporcionado.",
                "strengths": ["Evidencia de formación o experiencia técnica relevante cuando el CV la respalda."],
                "missing_or_unclear_evidence": ["Faltan detalles verificables sobre el título exacto o la experiencia."],
                "recommendations": ["Completar el perfil académico con el título, institución y fechas."],
                "requirement_classification": [
                    {"requirement": "Egreso de una carrera de Ingeniería o Licenciatura en área afín a computación y/o inteligencia artificial.", "category": "mandatory", "status": "evidence_insufficient", "evidence": "El CV no aporta suficiente evidencia verificable."},
                    {"requirement": "Conocimientos previos en algún lenguaje de alto nivel.", "category": "recommended", "status": "not_demonstrated", "evidence": ""},
                    {"requirement": "Manejo de bases de datos.", "category": "recommended", "status": "not_demonstrated", "evidence": ""},
                    {"requirement": "Facilidad para comprender conceptos abstractos y formular algoritmos para la resolución de problemas.", "category": "recommended", "status": "not_demonstrated", "evidence": ""}
                ],
                "wording_improvements": ["Usar verbos de acción y resultados medibles en la experiencia técnica."],
                "feedback": "Análisis simulado para pruebas automatizadas. No constituye una decisión oficial de admisión."
            }, ensure_ascii=False)
        return json.dumps({
            "should_ask": True,
            "followup_question": "¿Podrías explicar con un ejemplo concreto cómo aplicarías eso en un proyecto de inteligencia artificial?",
            "rationale": "Sigue la respuesta anterior sin inventar datos del candidato.",
        }, ensure_ascii=False)
