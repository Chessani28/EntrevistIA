from fastapi.testclient import TestClient
from backend.app.main import create_app


def test_phase5_candidate_profile_and_questions():
    client = TestClient(create_app())
    candidate = client.post("/api/v1/candidates", json={
        "full_name": "Perfil Smoke",
        "academic_background": "Ingenieria",
        "professional_background": "Desarrollo",
    })
    assert candidate.status_code == 200
    candidate_id = candidate.json()["id"]
    fetched = client.get(f"/api/v1/candidates/{candidate_id}")
    assert fetched.status_code == 200
    assert fetched.json()["full_name"] == "Perfil Smoke"
    updated = client.patch(f"/api/v1/candidates/{candidate_id}", json={
        "full_name": "Perfil Actualizado",
        "academic_background": "Maestria",
        "professional_background": "IA",
    })
    assert updated.status_code == 200
    assert updated.json()["academic_profile"]["academic_background"] == "Maestria"
    questions = client.get("/api/v1/questions")
    assert questions.status_code == 200
    assert len(questions.json()) == 30
    filtered = client.get("/api/v1/questions", params={"category": "motivation"})
    assert filtered.status_code == 200
    assert all(item["category"] == "motivation" for item in filtered.json())


def test_phase5_sessions_list():
    client = TestClient(create_app())
    created = client.post("/api/v1/interviews", json={"mode": "quick", "full_name": "Sesion Smoke"})
    assert created.status_code == 200
    sessions = client.get("/api/v1/sessions")
    assert sessions.status_code == 200
    assert any(item["id"] == created.json()["session_id"] for item in sessions.json())
