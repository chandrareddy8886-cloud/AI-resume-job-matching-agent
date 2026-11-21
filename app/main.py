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
    version="1.1.0",
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
    # Prevent browsers and intermediary caches from serving an older landing page
    # immediately after a new frontend deployment.
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
async def match_file(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
):
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
async def tailor_file(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
):
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="A job description is required.")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Resume tailoring needs an OpenAI API key. Add OPENAI_API_KEY in Render Environment settings.",
        )
    try:
        content = await resume.read()
        resume_text = extract_text(resume.filename or "", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="No readable text was found in this resume.")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert resume editor. Tailor the candidate's resume to the job description. "
                        "Preserve every factual claim, employer, title, date, qualification, project, metric, and skill. "
                        "Never invent experience, skills, credentials, dates, or measurable results. "
                        "You may reorganize, clarify, and improve wording using only evidence in the original resume. "
                        "If a job requirement is not supported by the resume, do not add it. "
                        "Return only the complete tailored resume as clean plain text, with clear section headings."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "JOB DESCRIPTION:\n" + job_description[:16000]
                        + "\n\nORIGINAL RESUME:\n" + resume_text[:16000]
                    ),
                },
            ],
        )
        tailored = response.output_text.strip()
        if not tailored:
            raise ValueError("The AI returned an empty resume.")
        return {"tailored_resume": tailored, "note": "Review every detail before using or submitting this resume."}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Resume tailoring failed: {exc}")
