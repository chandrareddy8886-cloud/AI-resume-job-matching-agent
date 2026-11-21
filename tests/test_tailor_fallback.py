from fastapi.testclient import TestClient

from app.main import app
from app.services.ai_client import AIProviderError


def test_tailor_file_returns_local_draft_when_ai_provider_is_down(monkeypatch):
    def unavailable(*args, **kwargs):
        raise AIProviderError("Gemini API returned HTTP 503: temporarily unavailable")

    monkeypatch.setattr("app.main.chat_completion", unavailable)
    client = TestClient(app)
    resume = (
        "Candidate Name\n"
        "Python FastAPI PostgreSQL\n"
        "Built REST API endpoints using FastAPI and PostgreSQL.\n"
    )
    response = client.post(
        "/tailor-file",
        files={"resume": ("resume.txt", resume.encode("utf-8"), "text/plain")},
        data={"job_description": "Python FastAPI Docker backend development"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["generation_mode"] == "local_fallback"
    assert "ROLE-TARGETED RESUME DRAFT" in payload["tailored_resume"]
    assert " ".join(resume.split()) in " ".join(payload["tailored_resume"].split())
