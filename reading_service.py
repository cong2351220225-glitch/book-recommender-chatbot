from __future__ import annotations

from pathlib import Path
from typing import Any

from config import READING_DIR

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB max safe file size


def validate_local_file(local_file: str) -> Path | None:
    """Validate a library reading file against the configured safe directory."""
    if not local_file or not str(local_file).strip():
        return None
    raw_value = str(local_file).strip()
    # Block path traversal
    if ".." in Path(raw_value).parts or ".." in raw_value:
        return None
    if Path(raw_value).is_absolute():
        return None
    candidate = (READING_DIR / raw_value).resolve()
    root = READING_DIR.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    if candidate.suffix.lower() not in {".pdf", ".epub"}:
        return None
    try:
        if candidate.stat().st_size > MAX_FILE_SIZE_BYTES:
            return None
    except OSError:
        return None
    return candidate


def get_book_reading_file(book: dict[str, Any]) -> Path | None:
    """Find a verified local reading file for a book record."""
    # 1. Direct local_file field if provided
    local_file = str(book.get("local_file", "")).strip()
    if local_file:
        validated = validate_local_file(local_file)
        if validated:
            return validated

    # 2. Check {book_id}.pdf or {book_id}.epub
    book_id = str(book.get("book_id", "")).strip()
    if book_id:
        for ext in [".pdf", ".epub"]:
            validated = validate_local_file(f"{book_id}{ext}")
            if validated:
                return validated

    # 3. Universal sample document if available
    fallback = validate_local_file("sample_reading.pdf")
    if fallback:
        return fallback

    return None


def get_book_specific_reading_file(book: dict[str, Any]) -> Path | None:
    """Find a book-specific local reading file, excluding universal demo fallbacks."""
    local_file = str(book.get("local_file", "")).strip()
    if local_file and local_file.lower() != "sample_reading.pdf":
        validated = validate_local_file(local_file)
        if validated:
            return validated

    book_id = str(book.get("book_id", "")).strip()
    if book_id:
        for ext in [".pdf", ".epub"]:
            validated = validate_local_file(f"{book_id}{ext}")
            if validated:
                return validated

    return None


def can_read(book: dict[str, Any]) -> bool:
    """Return whether the book has a legal, allowed local reading file."""
    return get_book_reading_file(book) is not None


def reading_status(book: dict[str, Any]) -> str:
    """Return a user-facing status for the reading availability of a book."""
    if can_read(book):
        return "Có thể đọc trong thư viện"
    return "📖 Sách này hiện chưa có bản điện tử trong thư viện."


def extract_reading_text(book: dict[str, Any], max_chars: int = 10000, specific_only: bool = True) -> str:
    """Extract readable text from a book's local reading file up to max_chars."""
    file_path = get_book_specific_reading_file(book) if specific_only else get_book_reading_file(book)
    if not file_path or not file_path.exists():
        return ""

    try:
        raw_bytes = file_path.read_bytes()
        # Decode as latin1 to safely parse PDF streams
        raw_content = raw_bytes.decode("latin1", errors="ignore")
        import re
        streams = re.findall(r"stream[\r\n]+(.*?)[\r\n]+endstream", raw_content, re.DOTALL)
        text_snippets: list[str] = []
        for s in streams:
            matches = re.findall(r"\((.*?)\)\s*Tj", s, re.DOTALL)
            if matches:
                text_snippets.extend(matches)
        if text_snippets:
            full_extracted = "\n".join(text_snippets)
            return full_extracted[:max_chars].strip()
        # Fallback to general printable characters if standard TJ format differs
        printable = re.sub(r"[^\x20-\x7E\n\r\t]", " ", raw_content)
        cleaned = re.sub(r"\s+", " ", printable).strip()
        return cleaned[:max_chars]
    except Exception:
        return ""

