"""Versioned storage of trained models in ``~/.mide/models_trained/``."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib

from mide.automl.trainer import TrainedModel

MODEL_FILE = "model.joblib"
META_FILE = "metadata.json"
_VERSION_RE = re.compile(r"^v(\d+)$")


class RegistryError(Exception):
    """Unknown model or corrupted registry entry."""


@dataclass(frozen=True)
class ModelRecord:
    """Metadata of one saved model version."""

    name: str
    version: int
    path: Path
    metadata: dict[str, Any]


def slugify(name: str) -> str:
    """Make a safe folder name from a dataset/target label."""
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._")
    if not slug:
        raise RegistryError(f"Invalid model name: {name!r}")
    return slug


def _versions(model_dir: Path) -> list[int]:
    if not model_dir.is_dir():
        return []
    found = [int(m.group(1)) for p in model_dir.iterdir() if (m := _VERSION_RE.match(p.name))]
    return sorted(found)


def save_model(
    trained: TrainedModel,
    registry_dir: Path,
    name: str,
    extra: dict[str, Any] | None = None,
) -> ModelRecord:
    """Save ``trained`` as the next version of ``name`` and return its record."""
    name = slugify(name)
    model_dir = registry_dir / name
    versions = _versions(model_dir)
    version = (versions[-1] + 1) if versions else 1
    path = model_dir / f"v{version}"
    path.mkdir(parents=True)
    joblib.dump(trained, path / MODEL_FILE)
    metadata: dict[str, Any] = {
        "name": name,
        "version": version,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "task": trained.task.task.value,
        "target": trained.task.target,
        "date_column": trained.task.date_column,
        "profile": trained.profile,
        "seed": trained.seed,
        "n_rows": trained.n_rows,
        "n_features": trained.n_features,
        "primary_metric": trained.primary_metric,
        "metrics": trained.metrics,
        "baseline_metrics": trained.baseline_metrics,
        "beats_baseline": trained.beats_baseline,
        "top_features": dict(list(trained.feature_importance.items())[:10]),
        **(extra or {}),
    }
    (path / META_FILE).write_text(json.dumps(metadata, indent=2, ensure_ascii=False), "utf-8")
    return ModelRecord(name, version, path, metadata)


def _record(model_dir: Path, version: int) -> ModelRecord:
    path = model_dir / f"v{version}"
    try:
        metadata = json.loads((path / META_FILE).read_text("utf-8"))
    except (OSError, ValueError) as exc:
        raise RegistryError(f"Corrupted registry entry: {path}") from exc
    return ModelRecord(model_dir.name, version, path, metadata)


def list_models(registry_dir: Path) -> list[ModelRecord]:
    """Every saved version of every model, sorted by name then version."""
    if not registry_dir.is_dir():
        return []
    records: list[ModelRecord] = []
    for model_dir in sorted(p for p in registry_dir.iterdir() if p.is_dir()):
        for version in _versions(model_dir):
            try:
                records.append(_record(model_dir, version))
            except RegistryError:
                continue  # skip corrupted entries
    return records


def load_model(
    registry_dir: Path, name: str, version: int | None = None
) -> tuple[TrainedModel, ModelRecord]:
    """Load a saved model (latest version unless ``version`` is given)."""
    model_dir = registry_dir / slugify(name)
    versions = _versions(model_dir)
    if not versions:
        raise RegistryError(f"No saved model named '{name}'")
    if version is None:
        version = versions[-1]
    elif version not in versions:
        raise RegistryError(f"Model '{name}' has no version {version}")
    record = _record(model_dir, version)
    try:
        trained = joblib.load(record.path / MODEL_FILE)
    except Exception as exc:
        raise RegistryError(f"Cannot load model {record.path}: {exc}") from exc
    return trained, record
