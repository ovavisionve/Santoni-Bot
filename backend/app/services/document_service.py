"""
Document analysis service.

Reads uploaded files and extracts content for LLM processing.
- Images (PNG, JPG): returns base64 for Claude vision
- PDF: extracts text with pdfplumber
- Excel: reads with openpyxl, converts to text table
- CSV/TXT: reads as plain text
- Word: reads with python-docx
"""

import base64
import csv
import io
import logging
import os

logger = logging.getLogger("santonibot.documents")

UPLOAD_DIR = "/tmp/santonibot_uploads"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def read_document(file_id: str) -> dict | None:
    """
    Read an uploaded document and return its content.

    Returns:
        {
            "type": "image" | "text",
            "content": str (text content or base64 for images),
            "mime_type": str (for images),
            "filename": str,
        }
        or None if file not found.
    """
    file_path = os.path.join(UPLOAD_DIR, file_id)
    if not os.path.exists(file_path):
        logger.warning("Document not found: %s", file_id)
        return None

    ext = os.path.splitext(file_id)[1].lower()

    try:
        if ext in IMAGE_EXTENSIONS:
            return _read_image(file_path, ext)
        elif ext == ".pdf":
            return _read_pdf(file_path)
        elif ext in (".xlsx", ".xls"):
            return _read_excel(file_path)
        elif ext == ".csv":
            return _read_csv(file_path)
        elif ext in (".docx", ".doc"):
            return _read_word(file_path)
        elif ext == ".txt":
            return _read_text(file_path)
        else:
            return _read_text(file_path)
    except Exception as exc:
        logger.error("Error reading document %s: %s", file_id, exc)
        return None


def _read_image(file_path: str, ext: str) -> dict:
    """Read image as base64 for Claude vision."""
    with open(file_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return {
        "type": "image",
        "content": data,
        "mime_type": MIME_TYPES.get(ext, "image/png"),
        "filename": os.path.basename(file_path),
    }


def _read_pdf(file_path: str) -> dict:
    """Extract text from PDF."""
    import pdfplumber

    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages[:50], 1):  # Limit to 50 pages
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"--- Página {i} ---\n{page_text}")

    return {
        "type": "text",
        "content": "\n\n".join(text_parts) if text_parts else "(PDF sin texto extraíble)",
        "filename": os.path.basename(file_path),
    }


def _read_excel(file_path: str) -> dict:
    """Read Excel and convert to text tables."""
    from openpyxl import load_workbook

    wb = load_workbook(file_path, read_only=True, data_only=True)
    text_parts = []

    for sheet_name in wb.sheetnames[:5]:  # Limit to 5 sheets
        ws = wb[sheet_name]
        rows = []
        for row in ws.iter_rows(max_row=200, values_only=True):  # Limit rows
            cells = [str(c) if c is not None else "" for c in row]
            if any(cells):  # Skip empty rows
                rows.append(cells)

        if rows:
            # Format as markdown table
            header = "| " + " | ".join(rows[0]) + " |"
            separator = "| " + " | ".join("---" for _ in rows[0]) + " |"
            body = "\n".join("| " + " | ".join(r) + " |" for r in rows[1:])
            text_parts.append(f"### Hoja: {sheet_name}\n\n{header}\n{separator}\n{body}")

    wb.close()
    return {
        "type": "text",
        "content": "\n\n".join(text_parts) if text_parts else "(Excel vacío)",
        "filename": os.path.basename(file_path),
    }


def _read_csv(file_path: str) -> dict:
    """Read CSV and convert to text table."""
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = [row for i, row in enumerate(reader) if i < 200]

    if rows:
        header = "| " + " | ".join(rows[0]) + " |"
        separator = "| " + " | ".join("---" for _ in rows[0]) + " |"
        body = "\n".join("| " + " | ".join(r) + " |" for r in rows[1:])
        content = f"{header}\n{separator}\n{body}"
    else:
        content = "(CSV vacío)"

    return {
        "type": "text",
        "content": content,
        "filename": os.path.basename(file_path),
    }


def _read_word(file_path: str) -> dict:
    """Read Word document text."""
    from docx import Document

    doc = Document(file_path)
    text_parts = []
    for para in doc.paragraphs[:500]:  # Limit paragraphs
        if para.text.strip():
            text_parts.append(para.text)

    return {
        "type": "text",
        "content": "\n".join(text_parts) if text_parts else "(Documento vacío)",
        "filename": os.path.basename(file_path),
    }


def _read_text(file_path: str) -> dict:
    """Read plain text file."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read(100_000)  # Limit to 100KB of text

    return {
        "type": "text",
        "content": content if content.strip() else "(Archivo vacío)",
        "filename": os.path.basename(file_path),
    }
