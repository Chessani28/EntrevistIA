import pytest
from fastapi.testclient import TestClient

from backend.app.db import reset_database
from backend.app.main import create_app
from backend.app.providers.mock import MockLLM


@pytest.fixture(autouse=True)
def clean_db():
    reset_database()
    yield


def make_client():
    return TestClient(create_app(provider=MockLLM()))


def test_recovery_of_missing_evaluation():
    client = make_client()
    created = client.post("/api/v1/interviews", json={"mode": "quick"})
    sid = created.json()["session_id"]
    client.post(f"/api/v1/interviews/{sid}/start")
    q = client.get(f"/api/v1/interviews/{sid}/current-question").json()["current_question"]
    ans = client.post(f"/api/v1/interviews/{sid}/answers", json={"question_id": q["id"], "answer": "Respuesta"}).json()
    aid = ans["answer_id"] if "answer_id" in ans else None
    # find answer id via history if not present
    if aid is None:
        history = client.get(f"/api/v1/interviews/{sid}/history").json()["items"]
        aid = history[0]["answer_id"] if "answer_id" in history[0] else history[0]["id"]

    # no eval yet
    before = client.get(f"/api/v1/evaluations/answers/{aid}")
    assert before.status_code == 404

    # recover
    resp = client.post(f"/api/v1/evaluations/answers/{aid}/evaluate", json={})
    assert resp.status_code == 200
    assert resp.json().get("score") is not None or resp.json().get("overall_score") is not None

    # repeated recovery no duplicate
    resp2 = client.post(f"/api/v1/evaluations/answers/{aid}/evaluate", json={})
    assert resp2.status_code == 200
    evals = client.get(f"/api/v1/evaluations/{sid}/evaluations").json()
    items = evals.get("items", evals.get("evaluations", []))
    assert len(items) == 1


def test_recovery_already_evaluated_no_overwrite():
    client = make_client()
    created = client.post("/api/v1/interviews", json={"mode": "quick"})
    sid = created.json()["session_id"]
    client.post(f"/api/v1/interviews/{sid}/start")
    q = client.get(f"/api/v1/interviews/{sid}/current-question").json()["current_question"]
    client.post(f"/api/v1/interviews/{sid}/answers", json={"question_id": q["id"], "answer": "Respuesta"})
    history = client.get(f"/api/v1/interviews/{sid}/history").json()["items"]
    aid = history[0].get("answer_id", history[0].get("id"))

    # find answer id via answers table not exposed; use session/question evaluate
    first = client.post(f"/api/v1/evaluations/{sid}/questions/{q['id']}/evaluate", json={})
    assert first.status_code == 200
    second = client.post(f"/api/v1/evaluations/{sid}/questions/{q['id']}/evaluate", json={})
    assert second.status_code == 200
    assert first.json().get("evaluation_id") == second.json().get("evaluation_id")


def test_recovery_preserves_original_answer():
    client = make_client()
    created = client.post("/api/v1/interviews", json={"mode": "quick"})
    sid = created.json()["session_id"]
    client.post(f"/api/v1/interviews/{sid}/start")
    q = client.get(f"/api/v1/interviews/{sid}/current-question").json()["current_question"]
    client.post(f"/api/v1/interviews/{sid}/answers", json={"question_id": q["id"], "answer": "TEXTO ORIGINAL"})
    history = client.get(f"/api/v1/interviews/{sid}/history").json()["items"]
    aid = history[0].get("answer_id", history[0].get("id"))

    client.post(f"/api/v1/evaluations/{sid}/questions/{q['id']}/evaluate", json={})
    evals = client.get(f"/api/v1/evaluations/{sid}/evaluations").json()
    items = evals.get("items", evals.get("evaluations", []))
    assert items and items[0].get("original_answer") == "TEXTO ORIGINAL"
