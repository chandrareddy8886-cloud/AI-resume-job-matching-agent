from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.services.ai_client import AIProviderError, chat_completion
from app.services.parser import extract_text
from app.services.matcher import match_resume_to_job
from app.services.llm import generate_ai_analysis

app = FastAPI(
    title="AI Resume & Job Matching Agent",
    version="1.4.0",
    description="Resume parsing, job matching, and evidence-based resume tailoring API.",
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class JobMatchRequest(BaseModel):
    resume_text: str
    job_description: str


def analyze_resume(resume_text: str, job_description: str):
    if not resume_text.strip() or not job_description.strip():
        raise HTTPException(status_code=400, detail="Resume text and job description are required.")
    try:
        result = match_resume_to_job(resume_text, job_description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    result["ai_analysis"] = generate_ai_analysis(resume_text, job_description, result)
    return result


async def read_resume(resume: UploadFile) -> str:
    filename = resume.filename or ""
    content = await resume.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Resume file exceeds the 10 MB upload limit.")
    try:
        text = extract_text(filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not text.strip():
        raise HTTPException(status_code=400, detail="No readable text was found. Scanned image-only PDFs need OCR first.")
    return text


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
    return {"status": "ok", "service": "ai-resume-job-matching-agent", "version": app.version}


@app.post("/match")
def match_text(payload: JobMatchRequest):
    return analyze_resume(payload.resume_text, payload.job_description)


@app.post("/match-file")
async def match_file(resume: UploadFile = File(...), job_description: str = Form(...)):
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="A job description is required.")
    resume_text = await read_resume(resume)
    result = analyze_resume(resume_text, job_description)
    result["resume_text"] = resume_text
    return result


@app.post("/tailor-file")
async def tailor_file(resume: UploadFile = File(...), job_description: str = Form(...)):
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="A job description is required.")
    resume_text = await read_resume(resume)

    system_prompt = (
        "You are an expert resume editor. Return the complete tailored resume as plain text. "
        "Preserve every factual claim, employer, title, date, qualification, project, metric, and skill. "
        "Never invent experience, skills, credentials, dates, or measurable results. "
        "You may reorganize, clarify, and improve wording using only evidence in the original resume. "
        "Do not add unsupported job requirements. Keep useful contact details and section headings."
    )
    user_prompt = (
        "Tailor this resume to the job description.\n\nJOB DESCRIPTION:\n"
        + job_description[:12000]
        + "\n\nORIGINAL RESUME:\n"
        + resume_text[:12000]
    )
    try:
        tailored = chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=7000,
        )
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {
        "tailored_resume": tailored,
        "note": "Review every detail before using or submitting this resume.",
    }
