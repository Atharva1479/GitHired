from io import BytesIO

from fastapi import HTTPException


async def extract_text_from_bytes(content: bytes, filename: str) -> str:
    name_lower = (filename or "").lower()
    try:
        if name_lower.endswith(".pdf"):
            text = _extract_pdf(content)
        elif name_lower.endswith(".docx"):
            text = _extract_docx(content)
        elif name_lower.endswith(".txt"):
            text = content.decode("utf-8", errors="replace")
        else:
            raise HTTPException(400, "Unsupported file type — upload .pdf, .docx, or .txt")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Failed to extract text: {e}") from e

    if len(text.strip()) < 50:
        raise HTTPException(400, "Extracted text too short — file may be image-based or empty")
    return text


def _extract_pdf(content: bytes) -> str:
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(x_tolerance=3, y_tolerance=3)
            if page_text:
                pages.append(page_text)

    if pages:
        return "\n".join(pages)

    # Fallback to pdfminer if pdfplumber returns nothing (image-heavy PDFs)
    from pdfminer.high_level import extract_text as pdfminer_extract
    return pdfminer_extract(BytesIO(content)) or ""


def _extract_docx(content: bytes) -> str:
    from docx import Document

    doc = Document(BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs)
