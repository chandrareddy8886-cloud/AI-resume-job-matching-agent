import json
from typing import Dict

from app.services.ai_client import chat_completion


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
    prompt = (
        "Analyze this resume against the job description. Return ONLY valid JSON with keys: "
        "summary (string), strengths (array of strings), gaps (array of strings), "
        "recommendations (array of strings). Be specific, concise, and truthful. "
        "Do not claim skills or experience absent from the resume.\n\n"
        f"MATCH DATA:\n{json.dumps(result, ensure_ascii=False)}\n\n"
        f"RESUME:\n{resume_text[:10000]}\n\nJOB DESCRIPTION:\n{job_description[:10000]}"
    )
    try:
        content = chat_completion(
            [
                {"role": "system", "content": "You are a careful, evidence-based career analyst. Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=3000,
        )
        analysis = _extract_json(content)
        if not analysis:
            raise ValueError("The model returned invalid JSON.")
        analysis.setdefault("summary", "Resume and job description compared.")
        analysis.setdefault("strengths", result.get("matched_skills", []))
        analysis.setdefault("gaps", result.get("missing_skills", []))
        analysis.setdefault("recommendations", [])
        analysis["provider"] = "groq"
        return analysis
    except Exception as exc:
        return {
            "provider": "local-fallback",
            "summary": "AI analysis is temporarily unavailable; deterministic matching results are shown.",
            "strengths": result.get("matched_skills", []),
            "gaps": result.get("missing_skills", []),
            "recommendations": ["AI analysis failed. Check the provider configuration and retry."],
            "error_type": type(exc).__name__,
        }
