from base64 import b64decode
from io import BytesIO
from docx import Document
from fastapi.testclient import TestClient

from app.main import app
from app.services.ai_client import AIProviderError


def test_tailor_file_returns_editable_docx_when_ai_provider_is_down(monkeypatch):
    def unavailable(*args, **kwargs):
        raise AIProviderError("Provider temporarily unavailable")

    monkeypatch.setattr("app.main.chat_completion", unavailable)
    client = TestClient(app)
    resume = (
        "Candidate Name\n"
        "TECHNICAL SKILLS\nPython FastAPI PostgreSQL\n"
        "PROJECTS\nBuilt REST API endpoints using FastAPI and PostgreSQL.\n"
    )
    response = client.post(
        "/tailor-file",
        files={"resume": ("resume.txt", resume.encode("utf-8"), "text/plain")},
        data={"job_description": "Python FastAPI Docker backend development"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["generation_mode"] == "evidence_based_fallback"
    assert "PROFESSIONAL SUMMARY" in payload["tailored_resume"]
    assert payload["download_filename"].endswith(".docx")
    document = Document(BytesIO(b64decode(payload["docx_base64"])))
    document_text = "\n".join(p.text for p in document.paragraphs)
    assert "Candidate Name" in document_text
    assert "FastAPI" in document_text
