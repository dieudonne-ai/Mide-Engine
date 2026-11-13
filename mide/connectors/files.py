"""Read-only connector for documents: folders of TXT/MD, DOCX and PDF files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from mide.connectors.base import BaseConnector, ensure_authorized

logger = logging.getLogger("mide.connectors.files")

TEXT_EXTENSIONS = {".txt", ".md"}
DOCUMENT_EXTENSIONS = TEXT_EXTENSIONS | {".docx", ".pdf"}


class DocumentReadError(Exception):
    """Raised when a document is corrupted or unreadable."""


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def _read_docx(path: Path) -> str:
    from docx import Document

    try:
        doc = Document(str(path))
    except Exception as exc:  # corrupted zip/xml
        raise DocumentReadError(f"Cannot read DOCX {path}: {exc}") from exc
    return "\n".join(p.text for p in doc.paragraphs)


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise DocumentReadError(f"Cannot read PDF {path}: {exc}") from exc


class DocumentConnector(BaseConnector):
    """Walks an authorized folder (recursively) and reads TXT/MD/DOCX/PDF files."""

    def __init__(
        self,
        source: str,
        authorized_sources: list[str],
        extensions: set[str] | None = None,
        max_file_size_mb: float = 50,
    ) -> None:
        super().__init__(source, authorized_sources)
        self.extensions = {e.lower() for e in (extensions or DOCUMENT_EXTENSIONS)}
        self.max_bytes = int(max_file_size_mb * 1024 * 1024)

    def discover(self) -> list[str]:
        root = Path(self.source).expanduser().resolve()
        if root.is_file():
            candidates = [root]
        elif root.is_dir():
            candidates = sorted(p for p in root.rglob("*") if p.is_file())
        else:
            raise FileNotFoundError(f"Source not found: {self.source}")
        items: list[str] = []
        for path in candidates:
            if path.suffix.lower() not in self.extensions:
                continue
            if path.stat().st_size > self.max_bytes:
                logger.warning("Skipping %s: larger than the size limit", path)
                continue
            items.append(str(path))
        return items

    def read(self, item: str) -> str:
        ensure_authorized(item, self.authorized_sources)
        path = Path(item).resolve()
        suffix = path.suffix.lower()
        if suffix in TEXT_EXTENSIONS:
            return _read_text(path)
        if suffix == ".docx":
            return _read_docx(path)
        if suffix == ".pdf":
            return _read_pdf(path)
        raise DocumentReadError(f"Unsupported document type: {path.suffix}")

    def read_all(self) -> dict[str, str]:
        """Read every discovered document; corrupted ones are skipped with a log."""
        out: dict[str, str] = {}
        for item in self.discover():
            try:
                out[item] = self.read(item)
            except DocumentReadError as exc:
                logger.warning("Skipping corrupted document: %s", exc)
        return out

    def metadata(self, item: str) -> dict[str, Any]:
        ensure_authorized(item, self.authorized_sources)
        path = Path(item).resolve()
        return {
            "type": path.suffix.lower().lstrip("."),
            "path": str(path),
            "size_bytes": path.stat().st_size,
        }
