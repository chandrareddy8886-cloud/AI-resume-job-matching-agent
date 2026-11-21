from app.services.resume_document import build_ats_docx
from docx import Document
from io import BytesIO


def test_build_ats_docx_creates_readable_single_column_document():
    content = "CHANDRA REDDY\nHyderabad | email@example.com\n\nPROFESSIONAL SUMMARY\nPython developer with FastAPI project experience.\n\nTECHNICAL SKILLS\n- Python\n- SQL"
    result = build_ats_docx(content)
    doc = Document(BytesIO(result))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "CHANDRA REDDY" in text
    assert "PROFESSIONAL SUMMARY" in text
    assert "Python" in text
    assert len(result) > 1000
