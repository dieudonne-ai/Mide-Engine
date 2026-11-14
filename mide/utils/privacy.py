"""Privacy report: what MIDE reads, what it stores, and what it sends (nothing)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from mide.config import Config
from mide.connectors.base import is_url
from mide.connectors.sources import list_sources


@dataclass
class StoredLocation:
    """A folder under the application directory holding MIDE-generated data."""

    name: str
    path: Path
    size_bytes: int
    purpose: str


@dataclass
class PrivacyReport:
    """What is read (authorized sources only) and what is stored (``~/.mide``)."""

    sources: list[str] = field(default_factory=list)
    stored: list[StoredLocation] = field(default_factory=list)
    network: str = ""
    read_only: str = ""

    def to_text(self, language: str = "fr") -> str:
        fr = language == "fr"
        lines = ["Sources lues (autorisées uniquement) :" if fr else "Data read (authorized sources only):"]
        lines += [f"  - {_mask(s)}" for s in self.sources] or [
            "  (aucune)" if fr else "  (none)"]
        lines.append("Données stockées localement :" if fr else "Data stored locally:")
        lines += [f"  - {s.path} ({s.size_bytes} o) : {s.purpose}" if fr
                  else f"  - {s.path} ({s.size_bytes} B): {s.purpose}" for s in self.stored]
        lines += [self.network, self.read_only]
        return "\n".join(lines)


def _mask(source: str) -> str:
    """Hide credentials embedded in a database URL."""
    if is_url(source) and "@" in source:
        scheme, rest = source.split("://", 1)
        return f"{scheme}://***@{rest.rsplit('@', 1)[1]}"
    return source


def _dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.exists() else 0


_PURPOSES = {
    "models": ("LLM/embedding weights", "poids des modèles"),
    "index": ("vector index of your documents", "index vectoriel de vos documents"),
    "models_trained": ("trained predictive models", "modèles prédictifs entraînés"),
}


def build_privacy_report(cfg: Config, config_dir: Path | None = None) -> PrivacyReport:
    """Collect the privacy report for the current configuration."""
    fr = cfg.language == "fr"
    stored = [
        StoredLocation(name, cfg.app_dir / name, _dir_size(cfg.app_dir / name),
                       purposes[1] if fr else purposes[0])
        for name, purposes in _PURPOSES.items()
    ]
    return PrivacyReport(
        sources=list_sources(config_dir),
        stored=stored,
        network=("Réseau : aucun appel en exécution (seul le téléchargement initial des "
                 "modèles, avec confirmation). Aucune télémétrie." if fr else
                 "Network: no calls at runtime (only the initial model download, with "
                 "confirmation). No telemetry."),
        read_only=("Sources en lecture seule : fichiers jamais modifiés, SQL limité à SELECT."
                   if fr else "Sources are read-only: files never modified, SQL limited to SELECT."),
    )
