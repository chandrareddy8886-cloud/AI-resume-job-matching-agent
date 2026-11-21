"""Build clean, single-column ATS-friendly resume files (DOCX and PDF)."""
from io import BytesIO
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from xml.sax.saxutils import escape

HEADINGS = {
    "professional summary", "summary", "profile", "career objective",
    "technical skills", "relevant skills", "skills", "core competencies",
    "experience", "professional experience", "work experience", "projects",
    "education", "certifications", "certificates", "achievements", "awards",
    "languages",
}


def _is_heading(line):
    value = re.sub(r"[^a-z ]", "", line.lower()).strip()
    return value in HEADINGS or (line.isupper() and 2 <= len(line.split()) <= 5 and len(line) < 48)


def _clean_lines(resume_text):
    lines = [re.sub(r"\s+", " ", line).strip() for line in resume_text.replace("\r", "\n").split("\n")]
    return [line for line in lines if line]


def build_ats_docx(resume_text: str) -> bytes:
    lines = _clean_lines(resume_text)
    if not lines:
        raise ValueError("The generated resume is empty.")
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

    first = doc.add_paragraph()
    first.alignment = WD_ALIGN_PARAGRAPH.CENTER
    first.paragraph_format.space_after = Pt(2)
    run = first.add_run(lines[0][:120])
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(16)
    for index, line in enumerate(lines[1:], start=1):
        if _is_heading(line):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(3)
            r = p.add_run(line.upper())
            r.bold = True
            r.font.name = "Arial"
            r.font.size = Pt(10)
            continue
        bullet = line.startswith(("-", "•", "*", "▪"))
        text = line.lstrip("-•*▪ ").strip() if bullet else line
        p = doc.add_paragraph(style="Normal")
        if bullet:
            p.style = doc.styles["List Bullet"]
            p.paragraph_format.left_indent = Inches(0.18)
        p.add_run(text)
        if index == 1 and len(text) < 160 and ("@" in text or "|" in text):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    out = BytesIO()
    doc.save(out)
    return out.getvalue()


def build_ats_pdf(resume_text: str) -> bytes:
    lines = _clean_lines(resume_text)
    if not lines:
        raise ValueError("The generated resume is empty.")
    out = BytesIO()
    pdf = SimpleDocTemplate(
        out, pagesize=letter, rightMargin=0.62*inch, leftMargin=0.62*inch,
        topMargin=0.55*inch, bottomMargin=0.55*inch,
        title="NextRole ATS Tailored Resume",
    )
    styles = getSampleStyleSheet()
    name_style = ParagraphStyle(
        "ResumeName", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=15, leading=18, alignment=TA_CENTER, spaceAfter=4,
    )
    contact_style = ParagraphStyle(
        "ResumeContact", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8.5, leading=10, alignment=TA_CENTER, spaceAfter=5,
    )
    heading_style = ParagraphStyle(
        "ResumeHeading", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=9.5, leading=11, spaceBefore=8, spaceAfter=3, keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "ResumeBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8.7, leading=11, spaceAfter=2,
    )
    story = [Paragraph(escape(lines[0][:120]), name_style)]
    for i, line in enumerate(lines[1:], start=1):
        if _is_heading(line):
            story.append(Paragraph(escape(line.upper()), heading_style))
        else:
            bullet = line.startswith(("-", "•", "*", "▪"))
            text = line.lstrip("-•*▪ ").strip() if bullet else line
            prefix = "&#8226; " if bullet else ""
            style = contact_style if i == 1 and len(text) < 160 and ("@" in text or "|" in text) else body_style
            story.append(Paragraph(prefix + escape(text), style))
    pdf.build(story)
    return out.getvalue()
