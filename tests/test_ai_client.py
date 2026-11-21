import json
from unittest.mock import patch

import pytest

from app.services.ai_client import AIProviderError, chat_completion
from app.services.llm import generate_ai_analysis


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_chat_completion_sends_groq_payload(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "openai/gpt-oss-20b")
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = request.headers
        captured["payload"] = json.loads(request.data)
        return FakeResponse({"choices": [{"message": {"content": "A tailored resume"}}]})

    with patch("app.services.ai_client.urlopen", fake_urlopen):
        text = chat_completion([{"role": "user", "content": "test"}])

    assert text == "A tailored resume"
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["payload"]["model"] == "openai/gpt-oss-20b"
    assert "include_reasoning" not in captured["payload"]


def test_chat_completion_rejects_empty_model_output(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    with patch("app.services.ai_client.urlopen", lambda *a, **k: FakeResponse({"choices": [{"message": {"content": ""}}]})):
        with pytest.raises(AIProviderError):
            chat_completion([{"role": "user", "content": "test"}])


def test_ai_analysis_parses_json(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    payload = {"summary": "Good fit", "strengths": ["Python"], "gaps": ["AWS"], "recommendations": ["Add project detail"]}
    with patch("app.services.llm.chat_completion", return_value=json.dumps(payload)):
        result = generate_ai_analysis("Python project", "Python and AWS", {"matched_skills": ["python"], "missing_skills": ["aws"]})
    assert result["summary"] == "Good fit"
    assert result["provider"] == "groq"


def test_ai_analysis_falls_back_with_clear_status(monkeypatch):
    with patch("app.services.llm.chat_completion", side_effect=AIProviderError("provider unavailable")):
        result = generate_ai_analysis("Python project", "Python role", {"matched_skills": ["python"], "missing_skills": []})
    assert result["provider"] == "local-fallback"
    assert result["strengths"] == ["python"]
