from app.services.matcher import match_resume_to_job


def build_local_tailored_resume(resume_text: str, job_description: str) -> str:
    """Create a conservative role-focused draft without an external AI provider.

    The original resume is retained verbatim. The only generated material is a
    short profile and skill emphasis derived from exact resume/job overlap and
    retrieved resume evidence, so the fallback cannot invent credentials.
    """
    match = match_resume_to_job(resume_text, job_description)
    matched = match.get("matched_skills", [])
    evidence = match.get("retrieved_resume_evidence", [])
    skills = ", ".join(matched[:8]) if matched else "the technical skills listed in the resume"
    evidence_lines = []
    for item in evidence[:5]:
        text = (item.get("text") or "").strip()
        if text and text not in evidence_lines:
            evidence_lines.append(text)
    lines = [
        "ROLE-TARGETED RESUME DRAFT",
        "",
        "PROFILE",
        f"Entry-level candidate with documented project and technical experience involving {skills}. "
        "The profile below emphasizes evidence from the original resume that is most relevant to the target role.",
        "",
        "MATCHED SKILLS (present in both the job description and original resume)",
    ]
    if matched:
        lines.extend(f"- {skill}" for skill in matched[:8])
    else:
        lines.append("See the original resume for documented technical skills.")
    if evidence_lines:
        lines.extend(["", "MOST RELEVANT RESUME EVIDENCE"])
        lines.extend(f"- {item}" for item in evidence_lines)
    lines.extend([
        "",
        "ORIGINAL RESUME (preserved; no qualifications, employers, dates, or metrics added)",
        resume_text.strip(),
    ])
    return "\n".join(lines)
