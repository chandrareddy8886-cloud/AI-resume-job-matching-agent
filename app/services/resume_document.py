"""Build clean, single-column ATS-friendly resume files with clickable contact links."""
from io import BytesIO
import re
from urllib.parse import urlparse

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
BULLET_PREFIXES = ("-", "•", "*", "▪", "●")

# Match explicit web links, email addresses and phone-like contact numbers.
LINK_PATTERN = re.compile(
    r"(?P<url>(?:(?:https?://|www\.)[^\s<>]+|"
    r"(?:linkedin\.com|github\.com|gitlab\.com|credly\.com|"
    r"coursera\.org|credentials\.databricks\.com)/[^\s<>]+))"
    r"|(?P<email>[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})"
    r"|(?P<phone>(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w))",
    re.IGNORECASE,
)


def _is_heading(line):
    value = re.sub(r"[^a-z ]", "", line.lower()).strip()
    return value in HEADINGS or (
        line.isupper() and 2 <= len(line.split()) <= 5 and len(line) < 48
    )


def _clean_lines(resume_text):
    lines = [
        re.sub(r"[ \t\f\v]+", " ", line).strip()
        for line in (resume_text or "").replace("\r", "\n").split("\n")
    ]
    return [line for line in lines if line]


def _link_target(kind, value):
    value = value.strip().rstrip(".,;:)")
    if kind == "url":
        return value if value.lower().startswith(("http://", "https://")) else "https://" + value
    if kind == "email":
        return "mailto:" + value
    digits = re.sub(r"\D", "", value)
    return "tel:" + (("+" if value.strip().startswith("+") else "") + digits)


def _segments(text):
    """Yield (plain_text, target_or_none) without changing visible resume text."""
    cursor = 0
    for match in LINK_PATTERN.finditer(text):
        start, end = match.span()
        if start > cursor:
            yield text[cursor:start], None
        kind = "url" if match.group("url") else "email" if match.group("email") else "phone"
        visible = match.group(kind)
        # Strip terminal punctuation from the link but retain it as plain text.
        clean = visible.rstrip(".,;:)")
        suffix = visible[len(clean):]
        yield clean, _link_target(kind, clean)
        if suffix:
            yield suffix, None
        cursor = end
    if cursor < len(text):
        yield text[cursor:], None


def _add_docx_link(paragraph, text, target):
    part = paragraph.part
    relationship = part.relate_to(
        target,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = paragraph._p.add_hyperlink(text, relationship) if hasattr(paragraph._p, "add_hyperlink") else None
    if hyperlink is None:
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        hyperlink = OxmlElement("w:hyperlink")
        hyperlink.set(qn("r:id"), relationship)
        run = OxmlElement("w:r")
        properties = OxmlElement("w:rPr")
        color = OxmlElement("w:color")
        color.set(qn("w:val"), "0563C1")
        properties.append(color)
        underline = OxmlElement("w:u")
        underline.set(qn("w:val"), "single")
        properties.append(underline)
        run.append(properties)
        node = OxmlElement("w:t")
        node.text = text
        run.append(node)
        hyperlink.append(run)
        paragraph._p.append(hyperlink)


def _add_docx_linkified(paragraph, text):
    for visible, target in _segments(text):
        if target:
            _add_docx_link(paragraph, visible, target)
        else:
            paragraph.add_run(visible)


def build_ats_docx(resume_text: str) -> bytes:
    lines = _clean_lines(resume_text)
    if not lines:
        raise ValueError("The generated resume is empty.")

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.62)
    section.bottom_margin = Inches(0.62)
    section.left_margin = Inches(0.72)
    section.right_margin = Inches(0.72)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(9.5)
    normal.font.color.rgb = RGBColor(35, 35, 35)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.08

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(3)
    run = title.add_run(lines[0])
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(17)

    for index, line in enumerate(lines[1:], start=1):
        if _is_heading(line):
            paragraph = doc.add_paragraph()
            paragraph.paragraph_format.space_before = Pt(9)
            paragraph.paragraph_format.space_after = Pt(4)
            paragraph.paragraph_format.keep_with_next = True
            run = paragraph.add_run(line.upper())
            run.bold = True
            run.font.name = "Arial"
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(31, 78, 121)
            continue

        is_bullet = line.startswith(BULLET_PREFIXES)
        text = line.lstrip("".join(BULLET_PREFIXES) + " ").strip() if is_bullet else line
        paragraph = doc.add_paragraph(style="List Bullet" if is_bullet else "Normal")
        paragraph.paragraph_format.space_after = Pt(3)
        if is_bullet:
            paragraph.paragraph_format.left_indent = Inches(0.2)
            paragraph.paragraph_format.first_line_indent = Inches(-0.12)
        _add_docx_linkified(paragraph, text)

    output = BytesIO()
    doc.save(output)
    return output.getvalue()


def _reportlab_markup(text):
    parts = []
    for visible, target in _segments(text):
        safe_text = escape(visible)
        if target:
            parts.append(f'<link href="{escape(target, {chr(34): "&quot;"})}" color="#0563C1">{safe_text}</link>')
        else:
            parts.append(safe_text)
    return "".join(parts)


def build_ats_pdf(resume_text: str) -> bytes:
    lines = _clean_lines(resume_text)
    if not lines:
        raise ValueError("The generated resume is empty.")

    output = BytesIO()
    pdf = SimpleDocTemplate(
        output, pagesize=letter,
        rightMargin=0.62 * inch, leftMargin=0.62 * inch,
        topMargin=0.55 * inch, bottomMargin=0.55 * inch,
        title="NextRole ATS Tailored Resume",
    )
    styles = getSampleStyleSheet()
    name_style = ParagraphStyle(
        "ResumeName", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=15, leading=18, alignment=TA_CENTER, spaceAfter=5,
    )
    contact_style = ParagraphStyle(
        "ResumeContact", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8.5, leading=11, alignment=TA_CENTER, spaceAfter=8,
    )
    heading_style = ParagraphStyle(
        "ResumeHeading", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=9.5, leading=11, spaceBefore=8, spaceAfter=4, keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "ResumeBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8.8, leading=11.5, spaceAfter=3,
    )

    story = [Paragraph(_reportlab_markup(lines[0]), name_style)]
    for index, line in enumerate(lines[1:], start=1):
        if _is_heading(line):
            story.append(Paragraph(_reportlab_markup(line.upper()), heading_style))
        else:
            is_bullet = line.startswith(BULLET_PREFIXES)
            text = line.lstrip("".join(BULLET_PREFIXES) + " ").strip() if is_bullet else line
            prefix = "&#8226; " if is_bullet else ""
            style = contact_style if index == 1 and ("@" in text or "|" in text) else body_style
            story.append(Paragraph(prefix + _reportlab_markup(text), style))
    pdf.build(story)
    return output.getvalue()
