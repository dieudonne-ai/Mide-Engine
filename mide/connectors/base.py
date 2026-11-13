"""Connector interface and source authorization checks.

Nothing is ever read unless it is listed in ``sources.yaml`` (explicit consent).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path
from typing import Any


class SourceNotAuthorizedError(PermissionError):
    """Raised when something outside the authorized sources is requested."""


def is_url(source: str) -> bool:
    """Return True for SQL-style URLs (``scheme://...``)."""
    return "://" in source


def normalize_source(source: str) -> str:
    """Return a canonical form: absolute resolved path for files, unchanged for URLs."""
    if is_url(source):
        return source
    return str(Path(source).expanduser().resolve())


def is_authorized(target: str | Path, sources: Iterable[str]) -> bool:
    """Return True if ``target`` is a listed source or lives inside a listed folder."""
    target_s = str(target)
    if is_url(target_s):
        return target_s in set(sources)
    resolved = Path(target_s).expanduser().resolve()
    for src in sources:
        if is_url(src):
            continue
        root = Path(src).expanduser().resolve()
        if resolved == root or root in resolved.parents:
            return True
    return False


def ensure_authorized(target: str | Path, sources: Iterable[str]) -> None:
    """Raise :class:`SourceNotAuthorizedError` unless ``target`` is authorized."""
    if not is_authorized(target, sources):
        raise SourceNotAuthorizedError(f"Source not authorized: {target}")


class BaseConnector(ABC):
    """Read-only access to one authorized source."""

    def __init__(self, source: str, authorized_sources: Iterable[str]) -> None:
        ensure_authorized(source, list(authorized_sources))
        self.source = source
        self.authorized_sources = list(authorized_sources)

    @abstractmethod
    def discover(self) -> list[str]:
        """List the readable items (files, sheets, tables) of the source."""

    @abstractmethod
    def read(self, item: str) -> Any:
        """Read one item returned by :meth:`discover` (never modifies the source)."""

    @abstractmethod
    def metadata(self, item: str) -> dict[str, Any]:
        """Return descriptive metadata (type, size, schema...) for one item."""
