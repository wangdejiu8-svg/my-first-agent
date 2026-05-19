from pathlib import Path

from docx import Document
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".docx", ".pdf"}
MAX_DOCUMENT_CHARS = 12000


def is_supported_document(filename):
    return Path(filename or "").suffix.lower() in SUPPORTED_EXTENSIONS


def read_document_text(file_path, original_name, max_chars=MAX_DOCUMENT_CHARS):
    suffix = Path(original_name or file_path).suffix.lower()
    path = Path(file_path)
    if suffix == ".docx":
        text = _read_docx(path)
    elif suffix == ".pdf":
        text = _read_pdf(path)
    else:
        raise ValueError("当前只支持读取 .docx 和 .pdf 文件。")

    text = _normalize_text(text)
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n\n[内容过长，已截取前 {max_chars} 个字符。]"


def _read_docx(path):
    document = Document(path)
    parts = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def _read_pdf(path):
    reader = PdfReader(path)
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(f"[第 {index} 页]\n{text}")
    return "\n\n".join(pages)


def _normalize_text(text):
    lines = [line.strip() for line in (text or "").splitlines()]
    normalized = []
    last_blank = False
    for line in lines:
        if not line:
            if not last_blank:
                normalized.append("")
            last_blank = True
            continue
        normalized.append(line)
        last_blank = False
    return "\n".join(normalized).strip()
