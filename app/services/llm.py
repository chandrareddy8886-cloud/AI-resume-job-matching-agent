import json
import os
from typing import Dict


def _extract_json(text: str) -> Dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                value = json.loads(text[start:end + 1])
                return value if isinstance(value, dict) else {}
            except json.JSONDecodeError:
                pass
    return {}


def generate_ai_analysis(resume_text: str, job_description: str, result: Dict) -> Dict:
    # Prefer Groq when GROQ_API_KEY is configured. OPENAI_API_KEY remains
    # supported for a direct OpenAI connection.
    groq_key = os.getenv("GROQ_API_KEY")
    api_key = groq_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "provider": "local-fallback",
            "summary": "AI analysis is disabled because no provider API key is configured.",
            "strengths": [],
            "gaps": result.get("missing_skills", []),
            "recommendations": ["Configure GROQ_API_KEY or OPENAI_API_KEY in Render Environment."],
        }

    is_groq = bool(groq_key) or "groq" in os.getenv("OPENAI_BASE_URL", "").lower()
    base_url = os.getenv("OPENAI_BASE_URL")
    if is_groq and not base_url:
        base_url = "https://api.groq.com/openai/v1"

    try:
        from openai import OpenAI

        client_args = {"api_key": api_key}
        if base_url:
            client_args["base_url"] = base_url
        client = OpenAI(**client_args)

        default_model = "openai/gpt-oss-20b" if is_groq else "gpt-4o-mini"
        model = os.getenv("OPENAI_MODEL", default_model)
        prompt = (
            "Analyze this resume against the job description. Return ONLY valid JSON with keys: "
            "summary (string), strengths (array of strings), gaps (array of strings), "
            "recommendations (array of strings). Be specific, concise, and truthful. "
            "Do not claim the candidate has skills or experience absent from the resume.\n\n"
            f"DETERMINISTIC MATCH DATA:\n{json.dumps(result, ensure_ascii=False)}\n\n"
            f"RESUME:\n{resume_text[:12000]}\n\n"
            f"JOB DESCRIPTION:\n{job_description[:12000]}"
        )
        completion = client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a careful, evidence-based career and resume analyst."},
                {"role": "user", "content": prompt},
            ],
        )
        analysis = _extract_json(completion.choices[0].message.content or "")
        if not analysis:
            raise ValueError("The model returned invalid JSON.")
        analysis["provider"] = "groq" if is_groq else "openai"
        return analysis
    except Exception as exc:
        # Keep deterministic results available, but make provider failure visible
        # without leaking secrets or request headers into the API response.
        return {
            "provider": "local-fallback",
            "summary": "AI analysis is temporarily unavailable; deterministic matching results are shown.",
            "strengths": result.get("matched_skills", []),
            "gaps": result.get("missing_skills", []),
            "recommendations": ["Retry AI analysis later or check provider/model settings."],
            "error_type": type(exc).__name__,
        }
