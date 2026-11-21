"""Evidence-preserving local fallback that creates a usable role-focused resume."""
import re
from app.services.matcher import match_resume_to_job

SECTION_ALIASES = {
    "professional summary": ("professional summary", "summary", "profile", "career objective"),
    "technical skills": ("technical skills", "skills", "technical expertise", "core competencies"),
    "experience": ("professional experience", "work experience", "experience", "internship"),
    "projects": ("projects", "academic projects", "personal projects"),
    "education": ("education", "academic details", "qualification"),
    "certifications": ("certifications", "certificates", "licenses"),
    "achievements": ("achievements", "awards", "accomplishments"),
}
HEADING_RE = re.compile(
    r"(?i)(?=\b(?:professional summary|summary|profile|career objective|technical skills|"
    r"skills|technical expertise|core competencies|professional experience|work experience|"
    r"experience|internship|projects|academic projects|personal projects|education|"
    r"academic details|qualification|certifications|certificates|achievements|awards)\b)"
)


def _section_name(line):
    cleaned = re.sub(r"[^a-z ]", "", line.lower()).strip()
    for canonical, aliases in SECTION_ALIASES.items():
        if cleaned in aliases:
            return canonical
    return None


def _split_sections(text):
    raw = [re.sub(r"\s+", " ", line).strip() for line in text.replace("\r", "\n").split("\n")]
    expanded = []
    for line in raw:
        if not line:
            expanded.append("")
            continue
        # PDF extraction sometimes places multiple section headings on one line.
        pieces = HEADING_RE.split(line)
        expanded.extend(piece.strip(" |:-") for piece in pieces if piece.strip(" |:-"))
    header, sections, current = [], {}, None
    for line in expanded:
        name = _section_name(line)
        if name:
            current = name
            sections.setdefault(current, [])
        elif current:
            sections[current].append(line)
        elif line:
            header.append(line)
    return header, sections


def build_local_tailored_resume(resume_text: str, job_description: str) -> str:
    """Reorder existing resume sections and bullets using the computed role match."""
    match = match_resume_to_job(resume_text, job_description)
    matched = [s for s in match.get("matched_skills", []) if s]
    missing = [s for s in match.get("missing_skills", []) if s]
    header, sections = _split_sections(resume_text)

    if not sections:
        # Keep the source intact when its layout cannot be reliably segmented.
        return "\n".join([
            *header[:4],
            "",
            "PROFESSIONAL SUMMARY",
            "Entry-level candidate with documented project and technical experience. "
            "Relevant evidence is retained below and prioritized for the target role.",
            "",
            "RELEVANT SKILLS",
            *[f"- {skill}" for skill in matched],
            "",
            "RESUME DETAILS",
            resume_text.strip(),
        ]).strip()

    summary_evidence = ", ".join(matched[:8]) or "documented technical and project experience"
    ordered = [
        "professional summary", "technical skills", "experience", "projects",
        "education", "certifications", "achievements",
    ]
    lines = header[:5]
    if "professional summary" not in sections:
        lines.extend(["", "PROFESSIONAL SUMMARY",
                      f"Entry-level candidate with documented experience in {summary_evidence}. "
                      "Relevant projects and technical evidence are prioritized for the target role."])
    for section in ordered:
        content = sections.get(section)
        if not content:
            continue
        lines.extend(["", section.upper()])
        if section == "technical skills" and matched:
            # Move proven, role-relevant skills to the front without adding any new skills.
            original = " ".join(content)
            found = [s for s in matched if re.search(r"(?i)\b" + re.escape(s) + r"\b", original)]
            remainder = [line for line in content if line.strip()]
            lines.append(" | ".join(found + [x for x in remainder if x.lower() not in {s.lower() for s in found}]))
        else:
            lines.extend(line for line in content if line.strip())
    # Do not insert missing skills into the resume; they remain in the match report.
    return "\n".join(lines).strip()
