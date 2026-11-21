from pathlib import Path
import os

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.services.parser import extract_text
from app.services.matcher import match_resume_to_job
from app.services.llm import generate_ai_analysis

app = FastAPI(
    title="AI Resume & Job Matching Agent",
    version="1.3.0",
    description="Resume parsing, job matching, and evidence-based resume tailoring API.",
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class JobMatchRequest(BaseModel):
    resume_text: str
    job_description: str


def analyze_resume(resume_text: str, job_description: str):
    if not resume_text.strip() or not job_description.strip():
        raise HTTPException(status_code=400, detail="Resume text and job description are required.")
    result = match_resume_to_job(resume_text, job_description)
    result["ai_analysis"] = generate_ai_analysis(resume_text, job_description, result)
    return result


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-resume-job-matching-agent"}


@app.post("/match")
def match_text(payload: JobMatchRequest):
    return analyze_resume(payload.resume_text, payload.job_description)


@app.post("/match-file")
async def match_file(resume: UploadFile = File(...), job_description: str = Form(...)):
    try:
        content = await resume.read()
        resume_text = extract_text(resume.filename or "", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="No readable text was found in this resume.")
    result = analyze_resume(resume_text, job_description)
    result["resume_text"] = resume_text
    return result


@app.post("/tailor-file")
async def tailor_file(resume: UploadFile = File(...), job_description: str = Form(...)):
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="A job description is required.")
    groq_key = os.getenv("GROQ_API_KEY")
    api_key = groq_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Add GROQ_API_KEY or OPENAI_API_KEY in Render Environment settings.")

    try:
        content = await resume.read()
        resume_text = extract_text(resume.filename or "", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="No readable text was found in this resume.")

    try:
        from openai import OpenAI
        is_groq = bool(groq_key) or "groq" in os.getenv("OPENAI_BASE_URL", "").lower()
        base_url = os.getenv("OPENAI_BASE_URL") or ("https://api.groq.com/openai/v1" if is_groq else None)
        client_args = {"api_key": api_key}
        if base_url:
            client_args["base_url"] = base_url
        client = OpenAI(**client_args)
        model = os.getenv("OPENAI_MODEL", "openai/gpt-oss-20b" if is_groq else "gpt-4o-mini")

        completion = client.chat.completions.create(
            model=model,
            temperature=0.2,
            max_completion_tokens=6000,
            reasoning_effort="low" if is_groq else None,
            include_reasoning=False if is_groq else None,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert resume editor. Return the complete tailored resume as plain text. "
                        "Preserve every factual claim, employer, title, date, qualification, project, metric, and skill. "
                        "Never invent experience, skills, credentials, dates, or measurable results. "
                        "You may reorganize, clarify, and improve wording using only evidence in the original resume. "
                        "Do not add unsupported job requirements. Keep useful contact details and section headings."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Tailor this resume to the job description.\n\nJOB DESCRIPTION:\n"
                        + job_description[:12000]
                        + "\n\nORIGINAL RESUME:\n"
                        + resume_text[:12000]
                    ),
                },
            ],
        )
        choice = completion.choices[0] if completion.choices else None
        tailored = ((choice.message.content or "").strip() if choice and choice.message else "")
        if not tailored and choice and choice.message:
            tailored = (getattr(choice.message, "refusal", None) or "").strip()
        if not tailored:
            finish = getattr(choice, "finish_reason", "unknown") if choice else "no_choices"
            raise ValueError(f"Model returned no resume text (finish_reason={finish}).")
        return {"tailored_resume": tailored, "note": "Review every detail before using or submitting this resume."}
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Resume tailoring failed: {type(exc).__name__}: {str(exc)[:300]}",
        )
