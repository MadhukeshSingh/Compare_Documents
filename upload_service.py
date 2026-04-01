"""
Upload / Validation Service
Stateless — no database, no disk storage.
Validates file bytes and returns metadata.
"""
import hashlib
import io
import logging
import re
import zipfile
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Supported extensions (must stay in sync with diff_service.ALL_SUPPORTED)
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {
    # Documents
    '.pdf', '.docx', '.doc', '.txt', '.md',
    # Code / data
    '.py', '.cpp', '.java', '.js', '.ts', '.c', '.h',
    '.json', '.xml', '.csv', '.html', '.htm',
    '.cs', '.go', '.rb', '.rs', '.swift', '.kt', '.php',
    '.sh', '.yaml', '.yml', '.toml', '.ini', '.cfg',
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

class FileValidator:
    """Validates uploaded files (extension + size)."""

    @staticmethod
    def validate(filename: str, file_size: int) -> Tuple[bool, Optional[str]]:
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, (
                f"File type '{ext}' is not supported. "
                f"Supported types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
        if file_size > MAX_FILE_SIZE:
            mb = file_size / (1024 * 1024)
            return False, f"File size {mb:.1f} MB exceeds the 50 MB limit."
        return True, None


class FileHasher:
    """SHA-256 hash of file bytes."""

    @staticmethod
    def hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# MIME sniffing helpers (kept for API compatibility)
# ---------------------------------------------------------------------------

def _looks_like_docx(data: bytes) -> bool:
    if not data.startswith(b"PK\x03\x04"):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile:
        return False
    return "[Content_Types].xml" in names and "word/document.xml" in names


def _looks_like_pdf(data: bytes) -> bool:
    return data.startswith(b"%PDF-")


def _looks_like_text(data: bytes) -> bool:
    if not data:
        return False
    sample = data[:4096]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def detect_mime(filename: str, data: bytes) -> str:
    """Return a best-guess MIME type string."""
    if _looks_like_pdf(data):
        return "application/pdf"
    if _looks_like_docx(data):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ext = Path(filename).suffix.lower()
    _EXT_MIME = {
        ".doc":  "application/msword",
        ".txt":  "text/plain",
        ".md":   "text/markdown",
        ".py":   "text/x-python",
        ".js":   "text/javascript",
        ".ts":   "text/typescript",
        ".html": "text/html",
        ".htm":  "text/html",
        ".json": "application/json",
        ".xml":  "application/xml",
        ".csv":  "text/csv",
        ".cpp":  "text/x-c++",
        ".c":    "text/x-c",
        ".java": "text/x-java",
    }
    if ext in _EXT_MIME:
        return _EXT_MIME[ext]
    if _looks_like_text(data):
        return "text/plain"
    return "application/octet-stream"


# ---------------------------------------------------------------------------
# Main in-memory processor
# ---------------------------------------------------------------------------

class FileProcessor:
    """
    Stateless file processor.
    Takes raw bytes, validates, hashes, returns metadata dict.
    No disk I/O or database calls.
    """

    def __init__(self):
        self.validator = FileValidator()
        self.hasher = FileHasher()

    def process(self, filename: str, data: bytes) -> dict:
        """
        Validate and inspect a file.

        Returns a dict with:
            ok          bool
            error       str | None
            filename    str
            file_size   int
            checksum    str
            mime_type   str
        """
        filename = _sanitize_filename(filename)
        size = len(data)

        ok, error = self.validator.validate(filename, size)
        if not ok:
            return {"ok": False, "error": error, "filename": filename,
                    "file_size": size, "checksum": None, "mime_type": None}

        checksum = self.hasher.hash(data)
        mime = detect_mime(filename, data)

        return {
            "ok": True,
            "error": None,
            "filename": filename,
            "file_size": size,
            "checksum": checksum,
            "mime_type": mime,
        }


def _sanitize_filename(filename: str) -> str:
    """Basic sanitization — remove path separators and null bytes."""
    import unicodedata
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")
    filename = filename.replace("\x00", "")
    filename = filename.replace("/", "_").replace("\\", "_").replace("..", "_")
    # Keep only safe chars in stem
    path = Path(filename)
    ext = path.suffix.lower()
    stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", path.stem)
    stem = re.sub(r"_+", "_", stem).strip("_") or "file"
    stem = stem[:100]
    return f"{stem}{ext}"
