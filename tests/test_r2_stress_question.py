import pytest
from fastapi.testclient import TestClient

from backend.app.db import reset_database
from backend.app.main import create_app
from backend.app.providers.mock import MockLLM
from backend.app.services.question_bank_service import QuestionBankService


@pytest.fixture(autouse=True)
def clean_db():
    reset_database()
    yield


def test_stress_question_present_once_in_every_mode():
    bank = QuestionBankService()
    bank.seed_questions()
    for mode, expected in (("quick", 5), ("standard", 10), ("complete", 15)):
        selected = [q["id"] for q in bank.select_questions(mode)]
        assert len(selected) == expected
        assert selected.count("ts-01") == 1


def test_quick_interview_completion_with_stress_question():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    sid = client.post("/api/v1/interviews", json={"mode": "quick"}).json()["session_id"]
    client.post(f"/api/v1/interviews/{sid}/start")
    question_ids = []
    while True:
        question = client.get(f"/api/v1/interviews/{sid}/current-question").json()["current_question"]
        if question is None:
            break
        question_ids.append(question["id"])
        client.post(
            f"/api/v1/interviews/{sid}/answers",
            json={"question_id": question["id"], "answer": "respuesta"},
        )
    assert "ts-01" in question_ids
    response = client.post(f"/api/v1/interviews/{sid}/complete")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_session_restoration_after_stress_question_change():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    sid = client.post("/api/v1/interviews", json={"mode": "quick"}).json()["session_id"]
    client.post(f"/api/v1/interviews/{sid}/start")
    first = client.get(f"/api/v1/interviews/{sid}/current-question").json()["current_question"]
    client.post(
        f"/api/v1/interviews/{sid}/answers",
        json={"question_id": first["id"], "answer": "contexto importante"},
    )
    restored_app = create_app(provider=MockLLM())
    restored_client = TestClient(restored_app)
    status = restored_client.get(f"/api/v1/interviews/{sid}").json()
    assert status["status"] == "in_progress"
    history = restored_client.get(f"/api/v1/interviews/{sid}/history").json()
    assert len(history["items"]) == 1
