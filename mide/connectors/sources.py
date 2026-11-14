"""Management of the authorized sources stored in ``sources.yaml``."""

from __future__ import annotations

from pathlib import Path

import yaml

from mide.config import DEFAULT_CONFIG_DIR, ConfigError, SourcesConfig, seed_default_config
from mide.connectors.base import is_url, normalize_source

HEADER = "# Authorized data sources. Nothing outside this list is ever read.\n"


def _sources_file(config_dir: Path | None) -> Path:
    cdir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
    seed_default_config(cdir)
    return cdir / "sources.yaml"


def list_sources(config_dir: Path | None = None) -> list[str]:
    """Return the authorized sources."""
    path = _sources_file(config_dir)
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return SourcesConfig.model_validate(data).sources
    except Exception as exc:  # invalid yaml / schema
        raise ConfigError(f"Invalid sources file {path}: {exc}") from exc


def _save(sources: list[str], config_dir: Path | None) -> None:
    path = _sources_file(config_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump({"sources": sources}, allow_unicode=True, sort_keys=False)
    path.write_text(HEADER + body, encoding="utf-8")


def add_source(source: str, config_dir: Path | None = None) -> str:
    """Authorize a path or SQL URL. Returns the stored (normalized) value."""
    if is_url(source):
        from urllib.parse import urlsplit

        if urlsplit(source).password:
            raise ValueError(
                "Do not put a password in the URL; use an environment variable "
                "(e.g. ${DB_PASSWORD})."
            )
    elif not Path(source).expanduser().exists():
        raise FileNotFoundError(f"Path does not exist: {source}")
    value = normalize_source(source)
    sources = list_sources(config_dir)
    if value not in sources:
        sources.append(value)
        _save(sources, config_dir)
    return value


def remove_source(source: str, config_dir: Path | None = None) -> bool:
    """Revoke a source. Returns False if it was not listed."""
    value = normalize_source(source)
    sources = list_sources(config_dir)
    if value not in sources:
        return False
    sources.remove(value)
    _save(sources, config_dir)
    return True
