from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.services.ai_client import AIProviderError, chat_completion
from app.services.parser import extract_text
from app.services.matcher import match_resume_to_job
from app.services.llm import generate_ai_analysis
from app.services.local_tailor import build_local_tailored_resume
from app.services.resume_quality import validate_tailored_resume

app = FastAPI(
    title="AI Resume & Job Matching Agent",
    version="1.5.0",
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
    result = await run_in_threadpool(analyze_resume, resume_text, job_description)
    result["resume_text"] = resume_text
    return result


@app.post("/tailor-file")
async def tailor_file(resume: UploadFile = File(...), job_description: str = Form(...)):
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="A job description is required.")
    resume_text = await read_resume(resume)
    match_result = await run_in_threadpool(match_resume_to_job, resume_text, job_description)

    system_prompt = (
        "You are a senior ATS resume writer. Produce a COMPLETE, polished, one-page-or-two-page "
        "ATS-friendly resume tailored to the supplied job description. Return only the resume text, "
        "not commentary or a report. Use standard headings: candidate name/contact, professional "
        "summary, technical skills, projects or experience, education, certifications, achievements. "
        "Only include sections supported by the source resume. Prioritize the exact matched skills and "
        "the strongest evidence identified by the matching engine. Reorder and rewrite existing bullets "
        "to foreground relevant tools, actions, and outcomes. Preserve all factual details, dates, "
        "employers, project names, qualifications, and metrics. Never invent skills, experience, "
        "certifications, employers, dates, or numerical results. Do not list missing job skills as if "
        "the candidate has them. Do not include match percentages, gap-analysis notes, or the original "
        "resume pasted wholesale. Use concise ATS-readable bullets, no columns, tables, icons, graphics, "
        "or decorative characters. Keep contact details from the source."
    )
    user_prompt = (
        "Create the tailored ATS resume using the match report as prioritization guidance.\n\n"
        f"TARGET JOB DESCRIPTION:\n{job_description[:12000]}\n\n"
        f"MATCH REPORT:\nOverall match: {match_result.get('overall_match_score', 0)}%\n"
        f"Skill match: {match_result.get('skill_match_score', 0)}%\n"
        f"Matched skills (candidate has evidence): {', '.join(match_result.get('matched_skills', []))}\n"
        f"Missing skills (DO NOT claim these): {', '.join(match_result.get('missing_skills', []))}\n"
        f"Relevant resume evidence: {match_result.get('retrieved_resume_evidence', [])}\n\n"
        f"ORIGINAL RESUME (sole source of candidate facts):\n{resume_text[:14000]}"
    )
    generation_mode = "ai"
    note = "ATS-formatted resume generated using your match report. Verify every claim before applying."
    try:
        tailored = await run_in_threadpool(
            chat_completion,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=7000,
        )
        if len(tailored.strip()) < 300 or "as an ai" in tailored.lower()[:500]:
            raise AIProviderError("Provider returned an incomplete resume.")
        quality = validate_tailored_resume(resume_text, tailored)
        if not quality.passed:
            correction_prompt = (
                "Your previous resume draft failed deterministic factuality checks. "
                "Rewrite it now. Fix EVERY issue listed below. Do not add tools, skills, dates, "
                "metrics, employers, or qualifications unless they appear in the original resume. "
                "Retain every original year, number, email address, and URL exactly. "
                "Return only the corrected complete resume.\n\n"
                "QUALITY ISSUES:\n- " + "\n- ".join(quality.issues) +
                "\n\nORIGINAL RESUME (only source of facts):\n" + resume_text[:14000] +
                "\n\nPREVIOUS DRAFT (for correction only):\n" + tailored[:14000]
            )
            tailored = await run_in_threadpool(
                chat_completion,
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": correction_prompt},
                ],
                max_tokens=7000,
            )
            quality = validate_tailored_resume(resume_text, tailored)
            if len(tailored.strip()) < 300 or not quality.passed:
                issues = "; ".join(quality.issues) or "Provider returned an incomplete resume."
                raise AIProviderError("AI draft failed factuality checks after correction: " + issues)
    except AIProviderError as exc:
        tailored = build_local_tailored_resume(resume_text, job_description)
        generation_mode = "evidence_based_fallback"
        note = (
            "AI draft did not pass the resume quality gate (" + str(exc) + "). "
            "A structured fallback was used to preserve source evidence. Review the result before applying."
        )

    from app.services.resume_document import build_ats_docx, build_ats_pdf
    import base64

    docx_bytes, pdf_bytes = await run_in_threadpool(
        lambda: (build_ats_docx(tailored), build_ats_pdf(tailored))
    )
    return {
        "tailored_resume": tailored,
        "generation_mode": generation_mode,
        "note": note,
        "downloads": {
            "docx": {
                "filename": "NextRole_ATS_Tailored_Resume.docx",
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "base64": base64.b64encode(docx_bytes).decode("ascii"),
            },
            "pdf": {
                "filename": "NextRole_ATS_Tailored_Resume.pdf",
                "mime_type": "application/pdf",
                "base64": base64.b64encode(pdf_bytes).decode("ascii"),
            },
            "txt": {
                "filename": "NextRole_ATS_Tailored_Resume.txt",
                "mime_type": "text/plain;charset=utf-8",
                "base64": base64.b64encode(tailored.encode("utf-8")).decode("ascii"),
            },
        },
    }
