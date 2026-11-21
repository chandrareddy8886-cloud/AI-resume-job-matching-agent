import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AIProviderError(RuntimeError):
    pass


def _provider_config():
    """Choose Gemini when a Gemini key is configured; otherwise use Groq."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = (
        os.getenv("GROQ_API_KEY")
        or os.getenv("GROK_API_KEY")  # temporary compatibility for the old typo
        or os.getenv("OPENAI_API_KEY")
    )

    if gemini_key:
        return (
            gemini_key,
            os.getenv(
                "GEMINI_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta/openai",
            ).rstrip("/"),
            os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            "Gemini",
        )

    if groq_key:
        return (
            groq_key,
            os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/"),
            os.getenv("OPENAI_MODEL", "openai/gpt-oss-20b"),
            "Groq",
        )

    raise AIProviderError(
        "No AI API key configured. Add GEMINI_API_KEY (recommended) or GROQ_API_KEY in Render."
    )


def _error_detail(raw_body):
    """Extract provider error messages across common OpenAI/Gemini response shapes."""
    try:
        body = json.loads(raw_body.decode("utf-8", errors="replace"))
    except Exception:
        return raw_body.decode("utf-8", errors="replace").strip()[:500] or "Empty provider response"

    if isinstance(body, dict):
        err = body.get("error", {})
        if isinstance(err, dict):
            message = err.get("message") or err.get("status") or err.get("code")
            if message:
                return str(message)[:500]
        elif err:
            return str(err)[:500]
        message = body.get("message") or body.get("detail")
        if message:
            return str(message)[:500]
    return json.dumps(body, ensure_ascii=False)[:500]


def chat_completion(messages, *, response_format=None, max_tokens=6000):
    """Call a Gemini or Groq OpenAI-compatible Chat Completions endpoint."""
    api_key, base_url, model, provider = _provider_config()

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
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
        detail = _error_detail(exc.read())
        if exc.code in (401, 403):
            raise AIProviderError(
                f"{provider} rejected authentication or model access (HTTP {exc.code}): {detail}. "
                "Check that the key belongs to this provider and that the selected model is enabled."
            ) from None
        raise AIProviderError(
            f"{provider} API returned HTTP {exc.code}: {detail}"
        ) from None
    except (URLError, TimeoutError) as exc:
        raise AIProviderError(
            f"Could not reach {provider}: {type(exc).__name__}."
        ) from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise AIProviderError(
            f"{provider} returned an invalid JSON response."
        ) from None

    choices = data.get("choices") or []
    if not choices:
        raise AIProviderError(f"{provider} returned no completion choices.")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict)
        )
    content = (content or "").strip()
    if not content:
        raise AIProviderError(
            f"{provider} returned no text. Check the configured model and token limits."
        )
    return content
