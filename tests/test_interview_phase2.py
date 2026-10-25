import pytest
from fastapi.testclient import TestClient

from backend.app.db import reset_database
from backend.app.main import create_app
from backend.app.providers.mock import MockLLM


@pytest.fixture(autouse=True)
def clean_db():
    reset_database()
    yield


def test_session_creation():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    response = client.post("/api/v1/interviews", json={"mode": "quick"})
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "quick"
    assert data["question_count"] == 5
    assert data["status"] == "created"


def test_interview_modes():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    for mode, count in (("quick", 5), ("standard", 10), ("complete", 15)):
        response = client.post("/api/v1/interviews", json={"mode": mode})
        assert response.status_code == 200
        assert response.json()["question_count"] == count


def test_question_selection_and_mandatory():
    from backend.app.services.question_bank_service import QuestionBankService

    bank = QuestionBankService()
    bank.seed_questions()
    assert bank.count_base() >= 30
    complete = [q["id"] for q in bank.select_questions("complete")]
    assert "ts-01" in complete
    for mode, expected in (("quick", 5), ("standard", 10), ("complete", 15)):
        selected = bank.select_questions(mode)
        assert len(selected) == expected


def test_answer_submission_and_duplicate():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    sid = client.post("/api/v1/interviews", json={"mode": "quick"}).json()["session_id"]
    client.post(f"/api/v1/interviews/{sid}/start")
    question = client.get(f"/api/v1/interviews/{sid}/current-question").json()["current_question"]
    response = client.post(f"/api/v1/interviews/{sid}/answers", json={"question_id": question["id"], "answer": "respuesta"})
    assert response.status_code == 200
    duplicate = client.post(f"/api/v1/interviews/{sid}/answers", json={"question_id": question["id"], "answer": "otra"})
    assert duplicate.status_code == 409


def test_context_preservation():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    sid = client.post("/api/v1/interviews", json={"mode": "quick"}).json()["session_id"]
    client.post(f"/api/v1/interviews/{sid}/start")
    first = client.get(f"/api/v1/interviews/{sid}/current-question").json()["current_question"]
    client.post(f"/api/v1/interviews/{sid}/answers", json={"question_id": first["id"], "answer": "contexto importante"})
    second = client.get(f"/api/v1/interviews/{sid}/current-question").json()["current_question"]
    assert second is not None
    assert second["id"] != first["id"]


def test_followup_generation():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    sid = client.post("/api/v1/interviews", json={"mode": "quick"}).json()["session_id"]
    client.post(f"/api/v1/interviews/{sid}/start")
    question = client.get(f"/api/v1/interviews/{sid}/current-question").json()["current_question"]
    client.post(f"/api/v1/interviews/{sid}/answers", json={"question_id": question["id"], "answer": "respuesta"})
    response = client.post(f"/api/v1/interviews/{sid}/follow-up")
    assert response.status_code == 200
    assert response.json()["should_ask"] is True
    assert response.json()["followup_question"] is not None


def test_db_persistence_and_restoration():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    sid = client.post("/api/v1/interviews", json={"mode": "quick"}).json()["session_id"]
    client.post(f"/api/v1/interviews/{sid}/start")
    question = client.get(f"/api/v1/interviews/{sid}/current-question").json()["current_question"]
    client.post(f"/api/v1/interviews/{sid}/answers", json={"question_id": question["id"], "answer": "persistida"})

    restored_app = create_app(provider=MockLLM())
    restored_client = TestClient(restored_app)
    status = restored_client.get(f"/api/v1/interviews/{sid}").json()
    assert status["status"] == "in_progress"
    history = restored_client.get(f"/api/v1/interviews/{sid}/history").json()
    assert len(history["items"]) == 1


def test_invalid_requests():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    response = client.post("/api/v1/interviews", json={"mode": "invalid"})
    assert response.status_code == 422
    response = client.post("/api/v1/interviews", json={"answer": "x"})
    assert response.status_code == 422


def test_ollama_unavailable():
    class UnavailableProvider:
        name = "ollama"
        model = "x"

        async def is_available(self):
            return False

        async def ensure_available(self):
            from backend.app.providers.base import ProviderUnavailableError

            raise ProviderUnavailableError()

        async def generate(self, message):
            from backend.app.providers.base import ProviderUnavailableError

            raise ProviderUnavailableError()

        async def generate_with_system(self, system, user):
            from backend.app.providers.base import ProviderUnavailableError

            raise ProviderUnavailableError()

    app = create_app(provider=UnavailableProvider())
    client = TestClient(app)
    sid = client.post("/api/v1/interviews", json={"mode": "quick"}).json()["session_id"]
    client.post(f"/api/v1/interviews/{sid}/start")
    question = client.get(f"/api/v1/interviews/{sid}/current-question").json()["current_question"]
    client.post(f"/api/v1/interviews/{sid}/answers", json={"question_id": question["id"], "answer": "respuesta"})
    response = client.post(f"/api/v1/interviews/{sid}/follow-up")
    assert response.status_code == 503


def test_malformed_llm_output():
    class BadProvider:
        name = "mock"
        model = "mock"

        async def is_available(self):
            return True

        async def ensure_available(self):
            return None

        async def generate(self, message):
            return "bad"

        async def generate_with_system(self, system, user):
            return "{not json"

    app = create_app(provider=BadProvider())
    client = TestClient(app)
    sid = client.post("/api/v1/interviews", json={"mode": "quick"}).json()["session_id"]
    client.post(f"/api/v1/interviews/{sid}/start")
    question = client.get(f"/api/v1/interviews/{sid}/current-question").json()["current_question"]
    client.post(f"/api/v1/interviews/{sid}/answers", json={"question_id": question["id"], "answer": "respuesta"})
    response = client.post(f"/api/v1/interviews/{sid}/follow-up")
    assert response.status_code == 502


def test_interview_completion():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    sid = client.post("/api/v1/interviews", json={"mode": "quick"}).json()["session_id"]
    client.post(f"/api/v1/interviews/{sid}/start")
    while True:
        question = client.get(f"/api/v1/interviews/{sid}/current-question").json()["current_question"]
        if question is None:
            break
        client.post(f"/api/v1/interviews/{sid}/answers", json={"question_id": question["id"], "answer": "respuesta"})
    response = client.post(f"/api/v1/interviews/{sid}/complete")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
