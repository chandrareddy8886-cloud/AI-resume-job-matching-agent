from io import BytesIO
from app.services.resume_document import build_ats_pdf, build_ats_docx
from pypdf import PdfReader
from docx import Document


RESUME = "CHANDRA REDDY\nHyderabad | email@example.com\n\nPROFESSIONAL SUMMARY\nPython developer with FastAPI experience.\n\nTECHNICAL SKILLS\n- Python\n- SQL"


def test_pdf_export_contains_resume_text():
    result = build_ats_pdf(RESUME)
    reader = PdfReader(BytesIO(result))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "CHANDRA REDDY" in text
    assert "PROFESSIONAL SUMMARY" in text
    assert "Python developer" in text


def test_docx_export_contains_resume_text():
    result = build_ats_docx(RESUME)
    doc = Document(BytesIO(result))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "CHANDRA REDDY" in text
    assert "TECHNICAL SKILLS" in text
