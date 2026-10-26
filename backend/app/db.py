"""Independent SQLite persistence for AIAdmissionSimulator."""
from pathlib import Path
import sqlite3

from backend.app.core.config import settings, PROJECT_ROOT


def database_path() -> Path:
    path = Path(settings.database_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


from contextlib import contextmanager

@contextmanager
def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(database_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT,
    academic_profile TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS interview_sessions (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    question_count INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    current_question_id TEXT,
    current_position INTEGER NOT NULL DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    followup_context TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    prompt TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'medium',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS session_questions (
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    PRIMARY KEY (session_id, question_id),
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS answers (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    candidate_answer TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cv_analyses (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    stored_path TEXT NOT NULL DEFAULT '',
    content_type TEXT NOT NULL DEFAULT 'application/pdf',
    file_size INTEGER NOT NULL DEFAULT 0,
    sha256 TEXT,
    status TEXT NOT NULL DEFAULT 'uploaded',
    extracted_evidence TEXT NOT NULL DEFAULT '{}',
    analysis_result TEXT NOT NULL DEFAULT '{}',
    error_code TEXT,
    error_message TEXT,
    summary TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT '',
    analyzed_at TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS evaluations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    answer_id TEXT NOT NULL,
    question_id TEXT,
    candidate_id TEXT,
    original_answer TEXT NOT NULL DEFAULT '',
    question_prompt TEXT NOT NULL DEFAULT '',
    score INTEGER NOT NULL,
    criteria TEXT NOT NULL DEFAULT '{}',
    feedback TEXT NOT NULL DEFAULT '',
    evaluation_result TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'completed',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (answer_id) REFERENCES answers(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    report_path TEXT,
    summary TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS preparation_plans (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    target_date TEXT,
    study_time_per_week INTEGER NOT NULL DEFAULT 300,
    goal TEXT NOT NULL DEFAULT '',
    topics TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'active',
    plan_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS preparation_activities (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    topic TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    estimated_minutes INTEGER NOT NULL DEFAULT 30,
    week_number INTEGER NOT NULL DEFAULT 1,
    day_label TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    completed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES preparation_plans(id) ON DELETE CASCADE
);
"""


def init_db() -> None:
    with connect() as connection:
        connection.executescript(SCHEMA)
        _migrate(connection)
        connection.commit()


def _migrate(connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(interview_sessions)").fetchall()}
    additions = {
        "current_question_id": "TEXT",
        "current_position": "INTEGER NOT NULL DEFAULT 0",
        "started_at": "TEXT",
        "completed_at": "TEXT",
        "followup_context": "TEXT NOT NULL DEFAULT '{}'",
    }
    for name, definition in additions.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE interview_sessions ADD COLUMN {name} {definition}")
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_answers_session_question "
        "ON answers(session_id, question_id)"
    )
    cv_columns = {row["name"] for row in connection.execute("PRAGMA table_info(cv_analyses)").fetchall()}
    cv_additions = {
        "stored_path": "TEXT NOT NULL DEFAULT ''",
        "content_type": "TEXT NOT NULL DEFAULT 'application/pdf'",
        "file_size": "INTEGER NOT NULL DEFAULT 0",
        "sha256": "TEXT",
        "status": "TEXT NOT NULL DEFAULT 'uploaded'",
        "extracted_evidence": "TEXT NOT NULL DEFAULT '{}'",
        "analysis_result": "TEXT NOT NULL DEFAULT '{}'",
        "error_code": "TEXT",
        "error_message": "TEXT",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
        "analyzed_at": "TEXT",
    }
    for name, definition in cv_additions.items():
        if name not in cv_columns:
            connection.execute(f"ALTER TABLE cv_analyses ADD COLUMN {name} {definition}")
    connection.execute("UPDATE cv_analyses SET updated_at = COALESCE(NULLIF(updated_at, ''), created_at)")
    eval_columns = {row["name"] for row in connection.execute("PRAGMA table_info(evaluations)").fetchall()}
    eval_additions = {
        "question_id": "TEXT",
        "candidate_id": "TEXT",
        "original_answer": "TEXT NOT NULL DEFAULT ''",
        "question_prompt": "TEXT NOT NULL DEFAULT ''",
        "evaluation_result": "TEXT NOT NULL DEFAULT '{}'",
        "status": "TEXT NOT NULL DEFAULT 'completed'",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    }
    for name, definition in eval_additions.items():
        if name not in eval_columns:
            connection.execute(f"ALTER TABLE evaluations ADD COLUMN {name} {definition}")
    connection.execute("UPDATE evaluations SET updated_at = COALESCE(NULLIF(updated_at, ''), created_at)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_evaluations_answer_id ON evaluations(answer_id)")
    for statement in (
        """CREATE TABLE IF NOT EXISTS preparation_plans (
            id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            target_date TEXT,
            study_time_per_week INTEGER NOT NULL DEFAULT 300,
            goal TEXT NOT NULL DEFAULT '',
            topics TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'active',
            plan_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS preparation_activities (
            id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            topic TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            estimated_minutes INTEGER NOT NULL DEFAULT 30,
            week_number INTEGER NOT NULL DEFAULT 1,
            day_label TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            completed_at TEXT,
            created_at TEXT NOT NULL
        )""",
    ):
        connection.execute(statement)


def reset_database() -> None:
    path = database_path()
    if path.exists():
        path.unlink()
    init_db()
