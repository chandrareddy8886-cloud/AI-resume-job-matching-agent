"""Evidence-preserving fallback that builds a clean, role-focused resume."""
import re
from app.services.matcher import match_resume_to_job

SECTION_ALIASES = {
    "professional summary": ("professional summary", "summary", "profile", "career objective", "objective"),
    "technical skills": ("technical skills", "skills", "technical expertise", "core competencies", "relevant skills"),
    "experience": ("professional experience", "work experience", "experience", "internship"),
    "projects": ("projects", "academic projects", "personal projects", "projects python"),
    "education": ("education", "academic details", "qualification"),
    "certifications": ("certifications", "certificates", "licenses", "certifications and self study"),
    "achievements": ("achievements", "awards", "accomplishments"),
    "languages": ("languages",),
}
HEADING_NAMES = {alias for aliases in SECTION_ALIASES.values() for alias in aliases}
HEADING_RE = re.compile(
    r"(?i)(?=\b(?:" + "|".join(re.escape(x) for x in sorted(HEADING_NAMES, key=len, reverse=True)) +
    r"|resume details)\b)"
)


def _normalize_line(line):
    return re.sub(r"\s+", " ", line or "").strip(" |:-•▪")


def _section_name(line):
    cleaned = re.sub(r"[^a-z ]", "", line.lower()).strip()
    for canonical, aliases in SECTION_ALIASES.items():
        if cleaned in aliases:
            return canonical
    return None


def _split_sections(text):
    expanded = []
    for raw_line in (text or "").replace("\r", "\n").split("\n"):
        line = _normalize_line(raw_line)
        if not line:
            continue
        for piece in (p for p in HEADING_RE.split(line) if p and p.strip()):
            expanded.append(_normalize_line(piece))

    header, sections, current = [], {}, None
    for line in expanded:
        if line.lower() == "resume details":
            current = None
            continue
        name = _section_name(line)
        if name:
            current = name
            sections.setdefault(current, [])
        elif current:
            sections[current].append(line)
        else:
            header.append(line)
    return header, sections


def _dedupe(lines):
    seen, result = set(), []
    for line in lines:
        value = _normalize_line(line)
        key = re.sub(r"[^a-z0-9]", "", value.lower())
        if value and key and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _target_title(job_description):
    labelled = re.search(r"(?im)^\s*(?:\*\*)?job title\s*:\s*([^\n*]+)", job_description or "")
    return labelled.group(1).strip(" *:#") if labelled else "the target role"


def _build_summary(job_description, matched, sections):
    title = _target_title(job_description)
    evidence = " and ".join(matched[:4]) if matched else "documented technical projects"
    project_text = " ".join(sections.get("projects", []))
    project_evidence = []
    for term in ("FastAPI", "PostgreSQL", "MySQL", "Docker", "GitHub Actions", "SQLAlchemy", "Python"):
        if re.search(r"(?i)\b" + re.escape(term) + r"\b", project_text):
            project_evidence.append(term)
    detail = ", ".join(dict.fromkeys(project_evidence[:5]))
    summary = (
        f"Computer Science graduate with hands-on project experience relevant to {title}. "
        f"Demonstrated skills include {evidence}."
    )
    if detail:
        summary += f" Built and documented software projects using {detail}."
    summary += " Seeking an entry-level opportunity to apply these skills and develop further in a production environment."
    return summary


def _dedupe_preserving_structure(lines):
    result, seen = [], set()
    for line in lines:
        value = _normalize_line(line)
        if not value:
            if result and result[-1] != "":
                result.append("")
            continue
        key = re.sub(r"[^a-z0-9]", "", value.lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def build_local_tailored_resume(resume_text: str, job_description: str) -> str:
    """Reorder and rewrite existing evidence; never append the raw resume a second time."""
    match = match_resume_to_job(resume_text, job_description)
    matched = [s for s in match.get("matched_skills", []) if s]
    header, sections = _split_sections(resume_text)
    header = _dedupe(header)[:6]
    sections = {key: _dedupe(value) for key, value in sections.items()}

    if not sections:
        body = _dedupe((resume_text or "").splitlines())
        return "\n".join(header + ["", "PROFILE", "Entry-level candidate with project-based technical experience.",
                                    "", "ADDITIONAL INFORMATION"] + body[:18]).strip()

    lines = header[:]
    lines.extend(["", "PROFESSIONAL SUMMARY", _build_summary(job_description, matched, sections)])

    skills = sections.get("technical skills", [])
    if skills:
        lines.extend(["", "TECHNICAL SKILLS"])
        skill_text = " ".join(skills)
        ordered = [s for s in matched if re.search(r"(?i)\b" + re.escape(s) + r"\b", skill_text)]
        if ordered:
            lines.append("Relevant: " + " | ".join(dict.fromkeys(ordered)))
        lines.extend(x for x in skills if x.lower() not in {s.lower() for s in ordered})

    if sections.get("experience"):
        lines.extend(["", "PROFESSIONAL EXPERIENCE"] + sections["experience"])

    if sections.get("projects"):
        project_lines = sections["projects"]
        if matched:
            indexed = list(enumerate(project_lines))
            indexed.sort(key=lambda pair: (-sum(1 for skill in matched if re.search(
                r"(?i)\b" + re.escape(skill) + r"\b", pair[1])), pair[0]))
            project_lines = [item for _, item in indexed]
        lines.extend(["", "SELECTED PROJECTS"] + project_lines)

    for section, heading in (("education", "EDUCATION"), ("certifications", "CERTIFICATIONS"),
                             ("achievements", "ACHIEVEMENTS"), ("languages", "LANGUAGES")):
        content = sections.get(section, [])
        if content:
            lines.extend(["", heading] + content)

    return "\n".join(_dedupe_preserving_structure(lines)).strip()
