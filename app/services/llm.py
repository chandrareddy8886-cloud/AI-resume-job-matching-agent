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
    groq_key = os.getenv("GROQ_API_KEY")
    api_key = groq_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "provider": "local-fallback",
            "summary": "AI analysis is disabled because no provider API key is configured.",
            "strengths": result.get("matched_skills", []),
            "gaps": result.get("missing_skills", []),
            "recommendations": ["Configure GROQ_API_KEY or OPENAI_API_KEY in Render Environment."],
        }

    is_groq = bool(groq_key) or "groq" in os.getenv("OPENAI_BASE_URL", "").lower()
    base_url = os.getenv("OPENAI_BASE_URL") or ("https://api.groq.com/openai/v1" if is_groq else None)
    try:
        from openai import OpenAI
        client_args = {"api_key": api_key}
        if base_url:
            client_args["base_url"] = base_url
        client = OpenAI(**client_args)
        model = os.getenv("OPENAI_MODEL", "openai/gpt-oss-20b" if is_groq else "gpt-4o-mini")
        prompt = (
            "Analyze this resume against the job description. Return ONLY valid JSON with keys: "
            "summary (string), strengths (array of strings), gaps (array of strings), "
            "recommendations (array of strings). Be specific, concise, and truthful. "
            "Do not claim skills or experience absent from the resume.\n\n"
            f"MATCH DATA:\n{json.dumps(result, ensure_ascii=False)}\n\n"
            f"RESUME:\n{resume_text[:10000]}\n\nJOB DESCRIPTION:\n{job_description[:10000]}"
        )
        completion = client.chat.completions.create(
            model=model,
            temperature=0.2,
            max_completion_tokens=2500,
            reasoning_effort="low" if is_groq else None,
            include_reasoning=False if is_groq else None,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a careful, evidence-based career analyst. Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
        )
        content = completion.choices[0].message.content if completion.choices else ""
        analysis = _extract_json(content or "")
        if not analysis:
            raise ValueError("The model returned empty or invalid JSON.")
        analysis["provider"] = "groq" if is_groq else "openai"
        return analysis
    except Exception as exc:
        return {
            "provider": "local-fallback",
            "summary": "AI analysis is temporarily unavailable; deterministic matching results are shown.",
            "strengths": result.get("matched_skills", []),
            "gaps": result.get("missing_skills", []),
            "recommendations": ["Retry AI analysis later or check provider/model settings."],
            "error_type": type(exc).__name__,
        }
