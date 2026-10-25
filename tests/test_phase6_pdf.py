import io
import uuid

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from backend.app.db import reset_database
from backend.app.main import create_app
from backend.app.providers.mock import MockLLM


@pytest.fixture(autouse=True)
def clean_db():
    reset_database()
    yield


def make_client():
    return TestClient(create_app(provider=MockLLM()))


def complete_session(client, full_name="Candidata Prueba Ñoño", answer_text="Respuesta de prueba con acentos: áéíóú ñ.", evaluate=False):
    created = client.post("/api/v1/interviews", json={"mode": "quick", "full_name": full_name})
    assert created.status_code == 200
    sid = created.json()["session_id"]
    assert client.post(f"/api/v1/interviews/{sid}/start").status_code == 200
    while True:
        question = client.get(f"/api/v1/interviews/{sid}/current-question").json()["current_question"]
        if question is None:
            break
        submitted = client.post(
            f"/api/v1/interviews/{sid}/answers",
            json={"question_id": question["id"], "answer": answer_text},
        )
        assert submitted.status_code == 200
        if evaluate:
            evaluated = client.post(
                f"/api/v1/evaluations/{sid}/questions/{question['id']}/evaluate",
                json={},
            )
            assert evaluated.status_code == 200
    completed = client.post(f"/api/v1/interviews/{sid}/complete")
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    return sid


def pdf_text(response):
    reader = PdfReader(io.BytesIO(response.content))
    return reader, "\n".join(page.extract_text() or "" for page in reader.pages)


def test_pdf_generation_completed_session():
    client = make_client()
    sid = complete_session(client, evaluate=True)
    response = client.get(f"/api/v1/reports/{sid}")
    assert response.status_code == 200
    reader, text = pdf_text(response)
    assert len(reader.pages) >= 1
    assert "Candidata Prueba" in text
    assert "Preguntas completadas: 5" in text
    assert "Evaluaciones disponibles: 5" in text
    assert "AI Admission Simulator" in text


def test_pdf_spanish_characters():
    client = make_client()
    sid = complete_session(client, full_name="María José Peña", evaluate=True)
    response = client.get(f"/api/v1/sessions/{sid}/report")
    assert response.status_code == 200
    _, text = pdf_text(response)
    assert "María José Peña" in text


def test_pdf_multipage_long_answers():
    client = make_client()
    long_answer = "Esta es una respuesta extensa. " * 120
    sid = complete_session(client, answer_text=long_answer, evaluate=True)
    response = client.get(f"/api/v1/interviews/{sid}/pdf")
    assert response.status_code == 200
    reader, text = pdf_text(response)
    assert len(reader.pages) > 1
    assert "Pagina 1 de" in text or "Página 1 de" in text


def test_pdf_missing_evaluations():
    client = make_client()
    sid = complete_session(client, evaluate=False)
    response = client.get(f"/api/v1/reports/{sid}")
    assert response.status_code == 200
    _, text = pdf_text(response)
    assert "No disponible" in text


def test_pdf_incomplete_interview():
    client = make_client()
    created = client.post("/api/v1/interviews", json={"mode": "quick", "full_name": "Incompleto"})
    sid = created.json()["session_id"]
    client.post(f"/api/v1/interviews/{sid}/start")
    response = client.get(f"/api/v1/reports/{sid}")
    assert response.status_code == 409


def test_pdf_invalid_session():
    client = make_client()
    response = client.get(f"/api/v1/reports/{uuid.uuid4()}")
    assert response.status_code == 404


def test_pdf_candidate_isolation():
    client = make_client()
    sid1 = complete_session(client, full_name="Candidato Uno", evaluate=True)
    sid2 = complete_session(client, full_name="Candidato Dos", evaluate=True)
    response1 = client.get(f"/api/v1/reports/{sid1}")
    response2 = client.get(f"/api/v1/reports/{sid2}")
    text1 = pdf_text(response1)[1]
    text2 = pdf_text(response2)[1]
    assert "Candidato Uno" in text1
    assert "Candidato Dos" not in text1
    assert "Candidato Dos" in text2
    assert "Candidato Uno" not in text2


def test_pdf_response_headers_and_filename():
    client = make_client()
    sid = complete_session(client, full_name="../../etc/passwd", evaluate=True)
    response = client.get(f"/api/v1/reports/{sid}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    disposition = response.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert ".pdf" in disposition
    assert "/" not in disposition.split("filename=")[-1].strip('"')
    assert "\\" not in disposition.split("filename=")[-1].strip('"')
