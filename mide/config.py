"""Configuration loading and validation (pydantic)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mide.utils.paths import app_dir

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
PROFILE_NAMES = ("tiny", "small", "medium", "large")


class ConfigError(Exception):
    """Raised when a configuration file is missing, unreadable or invalid."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GeneralConfig(_Strict):
    language: Literal["fr", "en"] = "fr"
    max_file_size_mb: int = Field(default=50, gt=0)


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


def load_config(config_dir: Path | None = None, create_app_dir: bool = True) -> Config:
    """Load ``default.yaml``, ``models.yaml`` and ``sources.yaml`` from ``config_dir``."""
    cdir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
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
