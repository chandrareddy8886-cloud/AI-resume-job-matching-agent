"""Evidence-preserving fallback that creates a structured, role-focused resume."""
import re

from app.services.matcher import match_resume_to_job

SECTION_ALIASES = {
    "professional summary": ("professional summary", "summary", "profile", "career objective", "objective"),
    "technical skills": ("technical skills", "skills", "technical expertise", "core competencies", "relevant skills"),
    "experience": ("professional experience", "work experience", "experience", "internship"),
    "projects": ("projects", "selected projects", "academic projects", "personal projects"),
    "education": ("education", "academic details", "qualification"),
    "certifications": ("certifications", "certificates", "licenses", "certifications and self study"),
    "achievements": ("achievements", "awards", "accomplishments"),
    "languages": ("languages",),
}
ALIASES = {alias: section for section, values in SECTION_ALIASES.items() for alias in values}
BULLET_RE = re.compile(r"^\s*(?:[-*•▪●■]|\d+[.)])\s*")


def _clean(line):
    return re.sub(r"\s+", " ", line or "").strip()


def _heading(line):
    value = re.sub(r"[^a-z ]", "", line.casefold()).strip()
    return ALIASES.get(value)


def _split_sections(text):
    header, sections, current = [], {}, None
    for raw in (text or "").replace("\r", "\n").split("\n"):
        line = _clean(raw)
        if not line or line.casefold() == "resume details":
            continue
        section = _heading(line)
        if section:
            current = section
            sections.setdefault(section, [])
        elif current:
            sections[current].append(line)
        else:
            header.append(line)
    return header, sections


def _dedupe(lines):
    result, seen = [], set()
    for line in lines:
        line = _clean(line)
        key = re.sub(r"[^a-z0-9]", "", line.casefold())
        if line and key and key not in seen:
            seen.add(key)
            result.append(line)
    return result


def _target_title(job_description):
    match = re.search(r"(?im)^\s*(?:\*\*)?job title\s*:\s*([^\n*]+)", job_description or "")
    return match.group(1).strip(" *:#") if match else ""


def _summary(matched, sections, job_description=""):
    title = _target_title(job_description)
    skill_text = " ".join(sections.get("technical skills", []))
    evidenced = [skill for skill in matched if re.search(
        r"(?<!\w)" + re.escape(skill) + r"(?!\w)", skill_text, re.I
    )]
    projects = sections.get("projects", [])
    experience = sections.get("experience", [])
    evidence = " and ".join(evidenced[:4])
    target = f" Targeting an entry-level {title} opportunity." if title else ""
    if evidence and projects:
        return f"Computer Science graduate with hands-on project experience using {evidence}. Built and documented software projects, with experience demonstrated through the selected projects below.{target}"
    if evidence and experience:
        return f"Computer Science graduate with documented experience and skills in {evidence}. Relevant experience and technical evidence are detailed below."
    if evidence:
        return f"Computer Science graduate with project-based technical skills in {evidence}. Relevant implementation details are demonstrated in the projects below."
    if projects:
        return "Computer Science graduate with hands-on academic and personal project experience. Project descriptions below summarize the documented technical work."
    return "Computer Science graduate with documented technical and academic experience detailed below."


def _project_groups(lines):
    """Keep each project title attached to its own bullets instead of sorting loose lines."""
    groups, current = [], []
    for line in lines:
        if BULLET_RE.match(line):
            if not current:
                current = ["Projects"]
            current.append(line)
        else:
            if current:
                groups.append(current)
            current = [line]
    if current:
        groups.append(current)
    return groups


def _group_score(group, matched):
    text = " ".join(group)
    return sum(bool(re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", text, re.I)) for skill in matched)


def _ordered_projects(lines, matched):
    groups = _project_groups(_dedupe(lines))
    indexed = list(enumerate(groups))
    indexed.sort(key=lambda item: (-_group_score(item[1], matched), item[0]))
    return [line for _, group in indexed for line in group]


def _ordered_skill_lines(lines, matched):
    lines = _dedupe(lines)
    def score(line):
        return sum(bool(re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", line, re.I)) for skill in matched)
    indexed = list(enumerate(lines))
    indexed.sort(key=lambda item: (-score(item[1]), item[0]))
    return [line for _, line in indexed]


def build_local_tailored_resume(resume_text: str, job_description: str) -> str:
    """Reorder existing evidence, preserving project-to-bullet relationships and facts."""
    match = match_resume_to_job(resume_text, job_description)
    matched = [skill for skill in match.get("matched_skills", []) if skill]
    header, raw_sections = _split_sections(resume_text)
    header = _dedupe(header)[:5]
    sections = {name: _dedupe(lines) for name, lines in raw_sections.items()}

    if not sections:
        body = _dedupe((resume_text or "").splitlines())
        return "\n".join(header + ["", "PROFESSIONAL SUMMARY",
            "Computer Science graduate with documented project-based technical experience.",
            "", "ADDITIONAL INFORMATION"] + body[:20]).strip()

    output = header[:]
    output += ["", "PROFESSIONAL SUMMARY", _summary(matched, sections, job_description)]

    skills = sections.get("technical skills", [])
    if skills:
        output += ["", "TECHNICAL SKILLS"] + _ordered_skill_lines(skills, matched)

    if sections.get("experience"):
        output += ["", "PROFESSIONAL EXPERIENCE"] + sections["experience"]

    if sections.get("projects"):
        output += ["", "SELECTED PROJECTS"] + _ordered_projects(sections["projects"], matched)

    for section, title in (
        ("education", "EDUCATION"),
        ("certifications", "CERTIFICATIONS"),
        ("achievements", "ACHIEVEMENTS"),
        ("languages", "LANGUAGES"),
    ):
        if sections.get(section):
            output += ["", title] + sections[section]

    # Keep section spacing while removing repeated content.
    result, seen = [], set()
    for line in output:
        line = _clean(line)
        if not line:
            if result and result[-1] != "":
                result.append("")
            continue
        key = re.sub(r"[^a-z0-9]", "", line.casefold())
        if key in seen:
            continue
        seen.add(key)
        result.append(line)
    return "\n".join(result).strip()
