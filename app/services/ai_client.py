"""Small OpenAI-compatible client with bounded multi-provider failover.

Provider order defaults to Groq -> OpenRouter. Google Gemini is optional and
is never selected unless explicitly configured as AI_PROVIDER=gemini or
AI_ENABLE_GEMINI_FALLBACK=true.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AIProviderError(RuntimeError):
    pass


def _provider_configs():
    groq_key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    configs = {
        "groq": {
            "key": groq_key,
            "base_url": os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        },
        "openrouter": {
            "key": openrouter_key,
            "base_url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free"),
        },
        "gemini": {
            "key": gemini_key,
            "base_url": os.getenv(
                "GEMINI_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta/openai",
            ),
            "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        },
    }

    preferred = os.getenv("AI_PROVIDER", "groq").strip().lower()
    if preferred not in configs:
        raise AIProviderError("AI_PROVIDER must be groq, openrouter, or gemini.")

    order = [preferred] + [name for name in ("groq", "openrouter", "gemini") if name != preferred]
    if preferred != "gemini" and os.getenv("AI_ENABLE_GEMINI_FALLBACK", "false").lower() not in ("1", "true", "yes"):
        order = [name for name in order if name != "gemini"]

    return [(name, configs[name]) for name in order if configs[name]["key"]]


def ai_provider_status():
    """Return safe configuration metadata; never expose credentials."""
    configured = {name for name, _ in _provider_configs()}
    preferred = os.getenv("AI_PROVIDER", "groq").strip().lower()
    return {
        "primary": preferred,
        "configured": [name for name in ("groq", "openrouter", "gemini") if name in configured],
        "ready": bool(configured),
    }


def _error_detail(raw_body):
    try:
        body = json.loads(raw_body.decode("utf-8", errors="replace"))
    except Exception:
        return raw_body.decode("utf-8", errors="replace").strip()[:300] or "Empty provider response"
    error = body.get("error", {}) if isinstance(body, dict) else {}
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or error)[:300]
    return str(error or body.get("message") or "Provider request failed")[:300]


def chat_completion(messages, *, response_format=None, max_tokens=6000):
    """Call the preferred provider, then fail over quickly to configured providers."""
    providers = _provider_configs()
    if not providers:
        raise AIProviderError(
            "No AI provider configured. Add GROQ_API_KEY and OPENROUTER_API_KEY in Render."
        )

    timeout = max(3.0, min(float(os.getenv("AI_REQUEST_TIMEOUT_SECONDS", "8")), 15.0))
    failures = []

    for provider, config in providers:
        payload = {
            "model": config["model"],
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        if response_format:
            payload["response_format"] = response_format

        request = Request(
            config["base_url"].rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + config["key"],
                "Content-Type": "application/json",
                "Accept": "application/json",
                "HTTP-Referer": os.getenv("APP_PUBLIC_URL", "https://ai-resume-job-matching-agent.onrender.com"),
                "X-Title": "NextRole",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            choices = data.get("choices") or []
            if not choices:
                raise AIProviderError("Provider returned no completion choices.")
            message = choices[0].get("message") or {}
            content = message.get("content")
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
            content = (content or "").strip()
            if not content:
                raise AIProviderError("Provider returned an empty completion.")
            return content
        except HTTPError as exc:
            detail = _error_detail(exc.read())
            failures.append(f"{provider} HTTP {exc.code}: {detail}")
            # Auth/model errors are provider-specific; try the next configured provider.
            continue
        except (URLError, TimeoutError, OSError, json.JSONDecodeError, AIProviderError) as exc:
            failures.append(f"{provider}: {str(exc)[:250]}")
            continue

    raise AIProviderError(
        "All configured AI providers failed. " + " | ".join(failures)
    )
