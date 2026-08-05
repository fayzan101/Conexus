from __future__ import annotations

import re
from pathlib import Path


def extract_text_from_bytes(data: bytes, filename: str = "", content_type: str = "") -> str:
    """Parse uploaded bytes into plain text for indexing."""
    name = (filename or "").lower()
    ctype = (content_type or "").lower()

    if name.endswith(".pdf") or "pdf" in ctype:
        return _extract_pdf(data)
    if name.endswith(".docx") or "wordprocessingml" in ctype:
        return _extract_docx(data)
    return _extract_plain(data)


def _extract_plain(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            text = data.decode(encoding)
            if text.strip():
                return text
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        import io

        reader = PdfReader(io.BytesIO(data))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        text = "\n".join(parts).strip()
        if text:
            return text
    except Exception:
        pass
    # Fallback: pull readable strings
    return _extract_plain(data)


def _extract_docx(data: bytes) -> str:
    try:
        import io
        from docx import Document as DocxDocument

        doc = DocxDocument(io.BytesIO(data))
        text = "\n".join(p.text for p in doc.paragraphs if p.text).strip()
        if text:
            return text
    except Exception:
        pass
    return _extract_plain(data)


def guess_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
