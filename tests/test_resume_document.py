from io import BytesIO

from docx import Document
from pypdf import PdfReader

from app.services.resume_document import build_ats_docx, build_ats_pdf


SAMPLE = """CHANDRA REDDY
Hyderabad | chandra@example.com | +91 9876543210
GitHub: github.com/chandrareddy8886-cloud
LinkedIn: https://www.linkedin.com/in/chandra-sekhar-reddy/
PROFESSIONAL SUMMARY
Python developer with FastAPI project experience.
PROJECTS
- Built a resume matching API.
EDUCATION
B.Tech Computer Science
CERTIFICATIONS
Python Essentials 1
ACHIEVEMENTS
First Prize at college hackathon
"""


def test_build_ats_docx_creates_readable_single_column_document():
    result = build_ats_docx(SAMPLE)
    doc = Document(BytesIO(result))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "CHANDRA REDDY" in text
    assert "PROFESSIONAL SUMMARY" in text
    assert "PROJECTS" in text
    assert "EDUCATION" in text
    assert "CERTIFICATIONS" in text
    assert "ACHIEVEMENTS" in text
    assert len(result) > 1000


def test_docx_contact_links_are_real_hyperlinks():
    doc = Document(BytesIO(build_ats_docx(SAMPLE)))
    rel_targets = [
        rel.target_ref for rel in doc.part.rels.values()
        if rel.reltype.endswith("/hyperlink")
    ]
    assert "mailto:chandra@example.com" in rel_targets
    assert "tel:+919876543210" in rel_targets
    assert "https://github.com/chandrareddy8886-cloud" in rel_targets
    assert "https://www.linkedin.com/in/chandra-sekhar-reddy/" in rel_targets


def test_pdf_contains_clickable_contact_links_and_sections():
    reader = PdfReader(BytesIO(build_ats_pdf(SAMPLE)))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "PROFESSIONAL SUMMARY" in text
    assert "CERTIFICATIONS" in text
    annotations = [
        annotation.get_object()
        for page in reader.pages
        for annotation in (page.get("/Annots") or [])
    ]
    uris = [
        annotation.get("/A", {}).get("/URI")
        for annotation in annotations
        if annotation.get("/A")
    ]
    assert "mailto:chandra@example.com" in uris
    assert "tel:+919876543210" in uris
    assert "https://github.com/chandrareddy8886-cloud" in uris


def test_empty_resume_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        build_ats_docx("  ")
    with pytest.raises(ValueError):
        build_ats_pdf("  ")
