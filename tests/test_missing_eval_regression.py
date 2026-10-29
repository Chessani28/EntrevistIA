import uuid

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


def complete_with_partial_evaluation(client, evaluate_count=9):
    created = client.post("/api/v1/interviews", json={"mode": "standard"})
    assert created.status_code == 200
    sid = created.json()["session_id"]
    assert client.post(f"/api/v1/interviews/{sid}/start").status_code == 200
    answered = 0
    while True:
        question = client.get(f"/api/v1/interviews/{sid}/current-question").json()["current_question"]
        if question is None:
            break
        submitted = client.post(
            f"/api/v1/interviews/{sid}/answers",
            json={"question_id": question["id"], "answer": "Respuesta de prueba"},
        )
        assert submitted.status_code == 200
        answered += 1
        if answered <= evaluate_count:
            evaluated = client.post(
                f"/api/v1/evaluations/{sid}/questions/{question['id']}/evaluate",
                json={},
            )
            assert evaluated.status_code == 200
    completed = client.post(f"/api/v1/interviews/{sid}/complete")
    assert completed.status_code == 200
    return sid, answered


def test_ten_answers_nine_evaluations_missing_detectable():
    client = make_client()
    sid, answered = complete_with_partial_evaluation(client, evaluate_count=9)
    assert answered == 10

    history = client.get(f"/api/v1/interviews/{sid}/history").json()
    assert len(history["items"]) == 10

    evaluations = client.get(f"/api/v1/evaluations/{sid}/evaluations").json()
    if isinstance(evaluations, dict):
        evaluations = evaluations.get("items", evaluations.get("evaluations", []))
    assert len(evaluations) == 9

    assert len(evaluations) < answered
    for ev in evaluations:
        assert ev.get("score") is not None

    response = client.get(f"/api/v1/reports/{sid}")
    assert response.status_code == 200
    assert response.status_code == 200
