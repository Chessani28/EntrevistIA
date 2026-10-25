"""Question bank for AI admissions interviews."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from backend.app.db import connect

MODES = {"quick": 5, "standard": 10, "complete": 15}
STRESS_QUESTION = (
    "¿Cómo serás capaz de manejar el estrés de estudiar una Maestría en Inteligencia "
    "Artificial compaginando el trabajo, la familia y tiempo personal y de descanso?"
)

CATEGORY_ORDER = [
    "academic_background",
    "motivation",
    "programming",
    "algorithms",
    "databases",
    "ai_fundamentals",
    "research_interests",
    "professional_experience",
    "time_management_stress",
    "ethics_professional_goals",
]

SEED_QUESTIONS = [
    ("academic_background", "ab-01", "Describe tu formación académica previa y cómo se relaciona con la inteligencia artificial.", "medium"),
    ("academic_background", "ab-02", "¿Qué materias o proyectos universitarios consideras más relevantes para esta maestría?", "medium"),
    ("academic_background", "ab-03", "¿Has cursado asignaturas de matemáticas, estadística o álgebra lineal? Describe tu nivel de confianza.", "medium"),
    ("motivation", "mo-01", "¿Por qué deseas ingresar a la Maestría en Inteligencia Artificial y qué esperas lograr?", "medium"),
    ("motivation", "mo-02", "¿Qué problema o aplicación de la inteligencia artificial te motiva más y por qué?", "medium"),
    ("motivation", "mo-03", "¿Dónde te ves profesionalmente después de concluir la maestría?", "medium"),
    ("programming", "pr-01", "¿En qué lenguajes de programación tienes experiencia y cuál prefieres para inteligencia artificial?", "medium"),
    ("programming", "pr-02", "Describe un programa o sistema que hayas desarrollado y tu rol en él.", "medium"),
    ("programming", "pr-03", "¿Cómo organizas y pruebas tu código cuando trabajas en un proyecto?", "medium"),
    ("algorithms", "al-01", "Explica cómo abordarías el diseño de un algoritmo para resolver un problema nuevo.", "medium"),
    ("algorithms", "al-02", "¿Qué estructuras de datos conoces y en qué situaciones las usarías?", "medium"),
    ("algorithms", "al-03", "Describe una situación en la que optimizaste tiempo o memoria de un algoritmo.", "medium"),
    ("databases", "db-01", "¿Qué experiencia tienes con bases de datos relacionales o NoSQL?", "medium"),
    ("databases", "db-02", "Explica la diferencia entre una consulta SQL con JOIN y una subconsulta.", "medium"),
    ("databases", "db-03", "¿Cómo diseñarías una base de datos para almacenar resultados de experimentos de inteligencia artificial?", "medium"),
    ("ai_fundamentals", "ai-01", "¿Qué entiendes por inteligencia artificial y aprendizaje automático?", "medium"),
    ("ai_fundamentals", "ai-02", "Describe la diferencia entre aprendizaje supervisado, no supervisado y por refuerzo.", "medium"),
    ("ai_fundamentals", "ai-03", "¿Qué métricas usarías para evaluar un modelo de clasificación y por qué?", "medium"),
    ("research_interests", "ri-01", "¿Tienes interés en investigación? Describe un tema que te gustaría explorar.", "medium"),
    ("research_interests", "ri-02", "¿Cómo buscarías y evaluarías literatura científica sobre un tema de inteligencia artificial?", "medium"),
    ("research_interests", "ri-03", "¿Qué experiencia tienes leyendo o reproduciendo artículos científicos?", "medium"),
    ("professional_experience", "pe-01", "Describe tu experiencia profesional y cómo se conecta con la inteligencia artificial.", "medium"),
    ("professional_experience", "pe-02", "¿Has trabajado en equipo en proyectos tecnológicos? ¿Qué rol desempeñaste?", "medium"),
    ("professional_experience", "pe-03", "¿Cómo manejas cambios de requisitos o prioridades en un proyecto?", "medium"),
    ("time_management_stress", "ts-01", STRESS_QUESTION, "medium"),
    ("time_management_stress", "ts-02", "¿Qué estrategias usas para organizar tu tiempo cuando tienes múltiples responsabilidades?", "medium"),
    ("time_management_stress", "ts-03", "¿Cómo reaccionas ante plazos ajustados o resultados inesperados en un proyecto?", "medium"),
    ("ethics_professional_goals", "eg-01", "¿Qué consideras una práctica ética en el desarrollo o uso de sistemas de inteligencia artificial?", "medium"),
    ("ethics_professional_goals", "eg-02", "¿Cómo evitarías sesgos o daños en un modelo de inteligencia artificial?", "medium"),
    ("ethics_professional_goals", "eg-03", "¿Qué impacto social esperas tener como profesional de inteligencia artificial?", "medium"),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class QuestionBankService:
    def seed_questions(self) -> None:
        canonical_ids = {item[1] for item in SEED_QUESTIONS}
        with connect() as connection:
            for category, question_id, prompt, difficulty in SEED_QUESTIONS:
                connection.execute(
                    "INSERT OR IGNORE INTO questions (id, category, prompt, difficulty, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (question_id, category, prompt, difficulty, _now()),
                )
                connection.execute(
                    "UPDATE questions SET category=?, prompt=?, difficulty=? WHERE id=?",
                    (category, prompt, difficulty, question_id),
                )
            placeholders = ",".join("?" for _ in canonical_ids)
            connection.execute(
                "DELETE FROM questions WHERE id NOT IN ({}) AND id NOT IN "
                "(SELECT question_id FROM session_questions UNION SELECT question_id FROM answers)".format(placeholders),
                tuple(canonical_ids),
            )
            connection.commit()

    def seed_if_empty(self) -> None:
        self.seed_questions()

    def categories(self) -> list[str]:
        return list(CATEGORY_ORDER)

    def list_questions(self, category: str | None = None) -> list[dict]:
        query = "SELECT * FROM questions"
        params: tuple = ()
        if category:
            query += " WHERE category = ?"
            params = (category,)
        query += " ORDER BY category, id"
        with connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [{key: row[key] for key in row.keys()} for row in rows]

    def get(self, question_id: str) -> dict | None:
        with connect() as connection:
            row = connection.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        return {key: row[key] for key in row.keys()} if row else None

    def select_questions(self, mode: str, include_stress: bool = False) -> list[dict]:
        if mode not in MODES:
            raise ValueError("mode must be quick, standard, or complete")
        count = MODES[mode]
        questions = self.list_questions()
        by_category = {category: [] for category in CATEGORY_ORDER}
        for question in questions:
            if question["category"] in by_category:
                by_category[question["category"]].append(question)
        for category in CATEGORY_ORDER:
            by_category[category].sort(key=lambda item: item["id"])

        selected: list[dict] = []
        selected_ids: set[str] = set()
        round_index = 0
        while len(selected) < count:
            added_this_round = False
            for category in CATEGORY_ORDER:
                items = by_category[category]
                if round_index < len(items):
                    question = items[round_index]
                    if question["id"] not in selected_ids:
                        selected.append(question)
                        selected_ids.add(question["id"])
                        added_this_round = True
                        if len(selected) >= count:
                            break
            if not added_this_round:
                break
            round_index += 1

        stress = self.get("ts-01")
        if stress is not None and stress["id"] not in selected_ids:
            if selected:
                selected[-1] = stress
            else:
                selected.append(stress)

        return selected[:count]

    def count_base(self) -> int:
        with connect() as connection:
            return connection.execute(
                "SELECT COUNT(*) AS n FROM questions WHERE category != 'follow_up'"
            ).fetchone()["n"]
