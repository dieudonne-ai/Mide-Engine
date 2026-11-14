"""Configuration loading and validation (pydantic)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mide.utils.paths import app_dir

_REPO_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
PACKAGED_DEFAULTS_DIR = Path(__file__).resolve().parent / "_defaults"
CONFIG_FILES = ("default.yaml", "models.yaml", "sources.yaml")
# Source checkout: use the repo ``config/`` folder. Installed package (pip/Docker wheel):
# use ``<app dir>/config``, seeded from the defaults shipped inside the package.
DEFAULT_CONFIG_DIR = (
    _REPO_CONFIG_DIR if _REPO_CONFIG_DIR.is_dir() else app_dir(create=False) / "config"
)
PROFILE_NAMES = ("tiny", "small", "medium", "large")


class ConfigError(Exception):
    """Raised when a configuration file is missing, unreadable or invalid."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GeneralConfig(_Strict):
    language: Literal["fr", "en"] = "fr"
    max_file_size_mb: int = Field(default=50, gt=0)
    chunk_size: int = Field(default=800, gt=0)
    chunk_overlap: int = Field(default=100, ge=0)


class LLMSpec(_Strict):
    repo: str
    file: str


class ProfileModels(_Strict):
    llm: LLMSpec
    embeddings: str
    lora: bool = False


class ModelsConfig(_Strict):
    profiles: dict[Literal["tiny", "small", "medium", "large"], ProfileModels] = {}


class SourcesConfig(_Strict):
    sources: list[str] = []


class Config(_Strict):
    general: GeneralConfig = GeneralConfig()
    models: ModelsConfig = ModelsConfig()
    sources: SourcesConfig = SourcesConfig()
    app_dir: Path

    @property
    def language(self) -> str:
        return self.general.language


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a mapping at top level.")
    return data


def _validate(model: type[BaseModel], data: dict[str, Any], path: Path) -> Any:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or '<root>'}: {e['msg']}" for e in exc.errors()
        )
        raise ConfigError(f"Invalid configuration in {path}: {details}") from exc


def seed_default_config(config_dir: Path) -> None:
    """Copy the packaged default config files into ``config_dir`` if they are missing."""
    if config_dir != DEFAULT_CONFIG_DIR or config_dir == _REPO_CONFIG_DIR:
        return
    config_dir.mkdir(parents=True, exist_ok=True)
    for name in CONFIG_FILES:
        target = config_dir / name
        if not target.exists():
            target.write_bytes((PACKAGED_DEFAULTS_DIR / name).read_bytes())


def load_config(config_dir: Path | None = None, create_app_dir: bool = True) -> Config:
    """Load ``default.yaml``, ``models.yaml`` and ``sources.yaml`` from ``config_dir``."""
    cdir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
    seed_default_config(cdir)
    parts = {}
    for key, model in (
        ("general", GeneralConfig),
        ("models", ModelsConfig),
        ("sources", SourcesConfig),
    ):
        filename = "default.yaml" if key == "general" else f"{key}.yaml"
        path = cdir / filename
        parts[key] = _validate(model, _read_yaml(path), path)
    return Config(app_dir=app_dir(create=create_app_dir), **parts)
