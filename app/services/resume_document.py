"""Generate clean, single-column ATS-friendly DOCX resumes."""
from io import BytesIO
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION


HEADINGS = {
    "professional summary", "summary", "profile", "career objective",
    "technical skills", "skills", "core competencies", "experience",
    "professional experience", "work experience", "projects", "education",
    "certifications", "certificates", "achievements", "awards",
}


def _is_heading(line):
    value = re.sub(r"[^a-z ]", "", line.lower()).strip()
    return value in HEADINGS or (line.isupper() and 2 <= len(line.split()) <= 5 and len(line) < 48)


def build_ats_docx(resume_text: str) -> bytes:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.55)
    section.left_margin = Inches(0.68)
    section.right_margin = Inches(0.68)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(9.5)
    normal.font.color.rgb = RGBColor(35, 35, 35)
    normal.paragraph_format.space_after = Pt(2.5)
    normal.paragraph_format.line_spacing = 1.02

    lines = [re.sub(r"\s+", " ", line).strip() for line in resume_text.replace("\r", "\n").split("\n")]
    lines = [line for line in lines if line]
    if not lines:
        raise ValueError("The generated resume is empty.")

    first = doc.add_paragraph()
    first.alignment = WD_ALIGN_PARAGRAPH.CENTER
    first.paragraph_format.space_after = Pt(2)
    run = first.add_run(lines[0][:120])
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(17)
    run.font.color.rgb = RGBColor(20, 20, 20)

    for index, line in enumerate(lines[1:], start=1):
        if _is_heading(line):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(3)
            r = p.add_run(line.upper())
            r.bold = True
            r.font.name = "Arial"
            r.font.size = Pt(10)
            r.font.color.rgb = RGBColor(35, 55, 35)
            continue
        bullet = line.startswith(("-", "•", "*"))
        text = line.lstrip("-•* ").strip() if bullet else line
        p = doc.add_paragraph(style="Normal")
        if bullet:
            p.style = doc.styles["List Bullet"]
            p.paragraph_format.left_indent = Inches(0.18)
        r = p.add_run(text)
        r.font.name = "Arial"
        r.font.size = Pt(9.5)
        if index == 1 and len(text) < 160 and ("@" in text or "|" in text):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    out = BytesIO()
    doc.save(out)
    return out.getvalue()
