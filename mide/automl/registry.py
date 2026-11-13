"""Versioned storage of trained models in ``~/.mide/models_trained/``."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib

from mide.automl.trainer import TrainedModel

MODEL_FILE = "model.joblib"
META_FILE = "metadata.json"
_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass
class ModelRecord:
    """Metadata of one saved model version."""

    name: str
    version: int
    dataset: str
    target: str
    task: str
    metric: str
    score: float
    baseline_score: float
    beats_baseline: bool
    profile: str
    n_rows: int
    seed: int
    created_at: str
    metrics: dict[str, float]
    importance: dict[str, float]


def slugify(name: str) -> str:
    """Make a safe folder name from a dataset / target name."""
    slug = _SAFE.sub("_", name).strip("._")
    return slug or "model"


def model_name(dataset: str, target: str) -> str:
    """Registry name for a dataset item (``path`` or ``path::sheet``) and a target."""
    path, _, sheet = dataset.partition("::")
    parts = [Path(path).stem] + ([sheet] if sheet else []) + [target]
    return slugify("_".join(parts))


class ModelRegistry:
    """Save, list and load models. Layout: ``<root>/<name>/v<N>/{model.joblib,metadata.json}``."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _dir(self, name: str, version: int) -> Path:
        return self.root / slugify(name) / f"v{version}"

    def versions(self, name: str) -> list[int]:
        base = self.root / slugify(name)
        if not base.is_dir():
            return []
        found = [int(p.name[1:]) for p in base.iterdir() if re.fullmatch(r"v\d+", p.name)]
        return sorted(found)

    def save(
        self,
        model: TrainedModel,
        name: str,
        dataset: str = "",
        metrics: dict[str, float] | None = None,
        importance: dict[str, float] | None = None,
    ) -> ModelRecord:
        """Save ``model`` as the next version of ``name`` and return its record."""
        existing = self.versions(name)
        version = (existing[-1] + 1) if existing else 1
        folder = self._dir(name, version)
        folder.mkdir(parents=True)
        record = ModelRecord(
            name=slugify(name),
            version=version,
            dataset=dataset,
            target=model.task.target,
            task=model.task.task,
            metric=model.metric,
            score=model.score,
            baseline_score=model.baseline_score,
            beats_baseline=model.beats_baseline,
            profile=model.profile,
            n_rows=model.n_rows,
            seed=model.seed,
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
            metrics=metrics or {},
            importance=importance or {},
        )
        joblib.dump(model, folder / MODEL_FILE)
        (folder / META_FILE).write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")
        return record

    def record(self, name: str, version: int | None = None) -> ModelRecord:
        version = version or self._latest(name)
        meta = self._dir(name, version) / META_FILE
        if not meta.is_file():
            raise KeyError(f"Model not found: {name} v{version}")
        data: dict[str, Any] = json.loads(meta.read_text(encoding="utf-8"))
        return ModelRecord(**data)

    def _latest(self, name: str) -> int:
        versions = self.versions(name)
        if not versions:
            raise KeyError(f"Model not found: {name}")
        return versions[-1]

    def load(self, name: str, version: int | None = None) -> TrainedModel:
        """Load a model (latest version by default). Only load files created by MIDE."""
        version = version or self._latest(name)
        path = self._dir(name, version) / MODEL_FILE
        if not path.is_file():
            raise KeyError(f"Model not found: {name} v{version}")
        model = joblib.load(path)
        if not isinstance(model, TrainedModel):
            raise TypeError(f"Not a MIDE model: {path}")
        return model

    def list(self) -> list[ModelRecord]:
        """Every saved version, sorted by name then version."""
        if not self.root.is_dir():
            return []
        records = []
        for folder in sorted(p for p in self.root.iterdir() if p.is_dir()):
            for version in self.versions(folder.name):
                try:
                    records.append(self.record(folder.name, version))
                except (KeyError, ValueError, TypeError):
                    continue
        return records
