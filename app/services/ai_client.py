import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AIProviderError(RuntimeError):
    pass


def chat_completion(messages, *, response_format=None, max_tokens=6000):
    """Call Groq's OpenAI-compatible Chat Completions API without SDK-version coupling."""
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AIProviderError("No API key configured. Set GROQ_API_KEY in Render.")

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "openai/gpt-oss-20b")

    payload = {
        "model": model,
        "messages": messages,
        "max_completion_tokens": max_tokens,
        "reasoning_effort": "low",
        "include_reasoning": False,
    }
    if response_format:
        payload["response_format"] = response_format

    request = Request(
        base_url + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=75) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            detail = body.get("error", {}).get("message") or body.get("message") or "Provider rejected the request."
        except Exception:
            detail = "Provider rejected the request."
        # Provider messages are safe to show; never include request headers or API keys.
        raise AIProviderError(f"AI provider HTTP {exc.code}: {detail[:350]}") from None
    except (URLError, TimeoutError) as exc:
        raise AIProviderError(f"Could not reach the AI provider: {type(exc).__name__}.") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise AIProviderError("AI provider returned an invalid response.") from None

    choices = data.get("choices") or []
    if not choices:
        raise AIProviderError("AI provider returned no completion choices.")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    content = (content or "").strip()
    if not content:
        raise AIProviderError(
            "AI model returned no final text. Try again or check the configured model and token limits."
        )
    return content
