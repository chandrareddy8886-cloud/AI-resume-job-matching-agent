from io import BytesIO
from pathlib import Path
import re


def _clean(text: str) -> str:
    """Normalize whitespace without destroying resume section boundaries."""
    lines = []
    for line in (text or "").replace("\r", "\n").split("\n"):
        normalized = re.sub(r"[ \t\f\v]+", " ", line).strip()
        if normalized:
            lines.append(normalized)
        elif lines and lines[-1] != "":
            lines.append("")
    return "\n".join(lines).strip()


def extract_text(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if not content:
        raise ValueError("The uploaded file is empty.")

    if ext in {".txt", ".md"}:
        return _clean(content.decode("utf-8-sig", errors="replace"))

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(content), strict=False)
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text(extraction_mode="layout") or page.extract_text() or "")
            return _clean("\n".join(pages))
        except Exception as exc:
            raise ValueError(f"Could not read PDF. Make sure it is a valid, non-password-protected PDF. ({type(exc).__name__})")

    if ext == ".docx":
        try:
            from docx import Document
            document = Document(BytesIO(content))
            parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
            for table in document.tables:
                for row in table.rows:
                    parts.append(" | ".join(cell.text.strip() for cell in row.cells))
            return _clean("\n".join(parts))
        except Exception as exc:
            raise ValueError(f"Could not read DOCX. Make sure it is a valid Word document. ({type(exc).__name__})")

    raise ValueError("Unsupported file type. Upload a PDF, DOCX, TXT, or MD file.")
