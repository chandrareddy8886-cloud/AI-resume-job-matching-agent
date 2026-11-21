from io import BytesIO

import pytest
from docx import Document

from app.services.parser import extract_text


def test_plain_text_extraction_preserves_resume_lines():
    assert extract_text("resume.txt", b"Python\nFastAPI") == "Python\nFastAPI"


def test_markdown_extraction_preserves_resume_lines():
    assert extract_text("resume.md", b"# Resume\nSQL and Python") == "# Resume\nSQL and Python"


def test_docx_paragraph_and_table_extraction():
    buffer = BytesIO()
    doc = Document()
    doc.add_paragraph("Python developer")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "FastAPI"
    table.cell(0, 1).text = "SQL"
    doc.save(buffer)
    result = extract_text("resume.docx", buffer.getvalue())
    assert "Python developer" in result
    assert "FastAPI | SQL" in result


def test_empty_file_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        extract_text("resume.txt", b"")


def test_unsupported_extension_is_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        extract_text("resume.exe", b"data")
