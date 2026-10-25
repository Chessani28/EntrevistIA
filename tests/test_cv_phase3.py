import pytest
from fastapi.testclient import TestClient

from backend.app.db import reset_database
from backend.app.main import create_app
from backend.app.providers.mock import MockLLM


def make_pdf(text: str) -> bytes:
    content = "BT\n/F1 12 Tf\n100 700 Td\n(" + text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ") Tj\nET\n"
    objects = [
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
        "4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        "5 0 obj\n<< /Length %d >>\nstream\n%s\nendstream\nendobj\n" % (len(content), content),
    ]
    body = ""
    offsets = [0]
    for obj in objects:
        offsets.append(len(body) + len("%PDF-1.4\n"))
        body += obj
    xref_pos = len("%PDF-1.4\n") + len(body)
    xref = "xref\n0 6\n0000000000 65535 f \n"
    for i in range(1, 6):
        xref += "%010d 00000 n \n" % offsets[i]
    pdf = "%PDF-1.4\n" + body + xref + "trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(xref_pos) + "\n%%EOF\n"
    return pdf.encode("latin-1")


@pytest.fixture(autouse=True)
def clean_db():
    reset_database()
    yield


def test_cv_upload_valid():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    pdf = make_pdf("Licenciatura en Informatica. Python SQL bases de datos.")
    response = client.post("/api/v1/cv", files={"file": ("cv.pdf", pdf, "application/pdf")}, data={"full_name": "Ana"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "uploaded"
    assert data["file_name"].endswith(".pdf")

def test_cv_invalid_file_type():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    response = client.post("/api/v1/cv", files={"file": ("cv.txt", b"hola", "text/plain")})
    assert response.status_code in (400, 415)


def test_cv_oversized_file():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    app.state.services["cv_analysis"].max_bytes = 10
    pdf = make_pdf("contenido")
    response = client.post("/api/v1/cv", files={"file": ("cv.pdf", pdf, "application/pdf")})
    assert response.status_code == 413


def test_cv_corrupted_pdf():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    response = client.post("/api/v1/cv", files={"file": ("cv.pdf", b"%PDF-1.4 broken", "application/pdf")})
    assert response.status_code in (400, 422)


def test_cv_empty_document():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    response = client.post("/api/v1/cv", files={"file": ("cv.pdf", b"", "application/pdf")})
    assert response.status_code in (400, 422)


def test_cv_text_extraction():
    from backend.app.services.cv_analysis_service import CVAnalysisService
    service = CVAnalysisService()
    pdf = make_pdf("Licenciatura en Informatica. Python SQL.")
    blocks, text, evidence, summary = service._validate_and_extract("cv.pdf", pdf)
    assert "Python" in evidence["programming_languages"]

def test_cv_evidence_classification():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    pdf = make_pdf("Licenciatura en Informatica. Python SQL bases de datos.")
    upload = client.post("/api/v1/cv", files={"file": ("cv.pdf", pdf, "application/pdf")}).json()
    aid = upload["id"]
    response = client.post(f"/api/v1/cv/{aid}/analyze")
    assert response.status_code == 200
    data = response.json()
    reqs = data["analysis"]["requirement_classification"]
    assert any(r["category"] == "mandatory" for r in reqs)
    assert all(r["status"] in {"evidence_found", "evidence_insufficient", "not_demonstrated"} for r in reqs)


def test_cv_structured_llm_output_validation():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    pdf = make_pdf("CV de prueba.")
    upload = client.post("/api/v1/cv", files={"file": ("cv.pdf", pdf, "application/pdf")}).json()
    aid = upload["id"]
    response = client.post(f"/api/v1/cv/{aid}/analyze")
    assert response.status_code == 200
    data = response.json()
    assert "strengths" in data["analysis"]
    assert "recommendations" in data["analysis"]


def test_cv_missing_information():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    pdf = make_pdf("Experiencia laboral generica sin titulo.")
    upload = client.post("/api/v1/cv", files={"file": ("cv.pdf", pdf, "application/pdf")}).json()
    aid = upload["id"]
    response = client.post(f"/api/v1/cv/{aid}/analyze")
    assert response.status_code == 200
    data = response.json()
    assert data["analysis"]["missing_or_unclear_evidence"]

def test_cv_ollama_unavailable():
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
    pdf = make_pdf("CV de prueba.")
    upload = client.post("/api/v1/cv", files={"file": ("cv.pdf", pdf, "application/pdf")}).json()
    aid = upload["id"]
    response = client.post(f"/api/v1/cv/{aid}/analyze")
    assert response.status_code == 503


def test_cv_db_persistence():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    pdf = make_pdf("Licenciatura en Informatica.")
    upload = client.post("/api/v1/cv", files={"file": ("cv.pdf", pdf, "application/pdf")}).json()
    aid = upload["id"]
    client.post(f"/api/v1/cv/{aid}/analyze")
    restored_app = create_app(provider=MockLLM())
    restored_client = TestClient(restored_app)
    status = restored_client.get(f"/api/v1/cv/{aid}/status").json()
    assert status["status"] == "completed"
    result = restored_client.get(f"/api/v1/cv/{aid}").json()
    assert result["analysis"]


def test_cv_deletion():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    pdf = make_pdf("CV de prueba.")
    upload = client.post("/api/v1/cv", files={"file": ("cv.pdf", pdf, "application/pdf")}).json()
    aid = upload["id"]
    response = client.delete(f"/api/v1/cv/{aid}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True
    missing = client.get(f"/api/v1/cv/{aid}")
    assert missing.status_code == 404


def test_cv_private_file_access_protection():
    app = create_app(provider=MockLLM())
    client = TestClient(app)
    pdf = make_pdf("CV de prueba.")
    upload = client.post("/api/v1/cv", files={"file": ("cv.pdf", pdf, "application/pdf")}).json()
    aid = upload["id"]
    response = client.get(f"/storage/cv_uploads/{aid}.pdf")
    assert response.status_code in (404, 403, 405)
    response2 = client.get(f"/api/v1/cv/{aid}/file")
    assert response2.status_code in (404, 405, 400)
