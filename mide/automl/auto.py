"""Scheduled auto-learning: scan, incremental indexing, conditional retraining, report."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from mide.automl.evaluator import evaluate
from mide.automl.registry import list_models, save_model
from mide.automl.trainer import TrainedModel, train
from mide.hardware.profiler import Profile

logger = logging.getLogger("mide.automl.auto")

STATE_NAME = "auto_state.json"


@dataclass
class ModelOutcome:
    """What happened to one registered model during an auto run."""

    name: str
    status: str  # unchanged | kept | promoted | skipped | error
    detail: str = ""
    old_score: float | None = None
    new_score: float | None = None


@dataclass
class AutoReport:
    """Outcome of one `mide auto` run."""

    n_datasets: int = 0
    index_summary: str = ""
    outcomes: list[ModelOutcome] = field(default_factory=list)

    @property
    def retrained(self) -> list[ModelOutcome]:
        return [o for o in self.outcomes if o.status in ("promoted", "kept")]


def fingerprint(df: pd.DataFrame) -> str:
    """Content hash of a dataframe (stable across runs)."""
    row_hashes = pd.util.hash_pandas_object(df, index=False).to_numpy().tobytes()
    payload = json.dumps([list(map(str, df.columns)), len(df)]).encode() + row_hashes
    return hashlib.sha256(payload).hexdigest()


def _load_state(path: Path) -> dict[str, str]:
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def _save_state(path: Path, state: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), "utf-8")


def _find_frame(frames: dict[str, pd.DataFrame], dataset: str) -> pd.DataFrame | None:
    """Match a model's dataset label (file stem or table) to a loaded frame."""
    for item, df in frames.items():
        if dataset in (item, Path(item.split("::")[0]).stem, Path(item).name):
            return df
    return None


def _is_better(new: TrainedModel, old_score: float, old_primary: str) -> bool:
    """Higher-is-better comparison on the primary metric (errors are stored negated by name)."""
    new_score = new.metrics.get(old_primary)
    if new_score is None:
        return False
    lower_better = old_primary.lower() in {"mae", "rmse", "mape", "logloss"}
    return new_score < old_score if lower_better else new_score > old_score


def retrain_if_changed(
    frames: dict[str, pd.DataFrame],
    registry_dir: Path,
    state_path: Path,
    profile: Profile | str = "small",
    seed: int = 42,
) -> list[ModelOutcome]:
    """Retrain registered models whose dataset changed; promote only if better.

    The previous version stays the latest one unless the candidate beats it, so an
    unchanged dataset never triggers any training and a worse model is never saved.
    """
    state = _load_state(state_path)
    latest: dict[str, dict] = {}
    for rec in list_models(registry_dir):
        latest[rec.name] = rec.metadata
    outcomes: list[ModelOutcome] = []
    for name, meta in sorted(latest.items()):
        dataset = meta.get("dataset") or name.rsplit("-", 1)[0]
        df = _find_frame(frames, dataset)
        if df is None:
            outcomes.append(ModelOutcome(name, "skipped", "dataset no longer available"))
            continue
        digest = fingerprint(df)
        if (state.get(name) or meta.get("data_hash")) == digest:
            outcomes.append(ModelOutcome(name, "unchanged"))
            continue
        old_primary = meta["primary_metric"]
        old_score = meta["metrics"][old_primary]
        try:
            candidate = train(
                df,
                meta["target"],
                profile=profile,
                seed=seed,
                date_column=meta.get("date_column"),
            )
            new_score = candidate.metrics.get(old_primary)
            if _is_better(candidate, old_score, old_primary):
                extra = {"evaluation": evaluate(candidate, df), "dataset": dataset, "data_hash": digest}
                save_model(candidate, registry_dir, name, extra)
                outcomes.append(ModelOutcome(name, "promoted", "new model is better", old_score, new_score))
            else:
                outcomes.append(ModelOutcome(name, "kept", "previous model kept", old_score, new_score))
        except Exception as exc:  # noqa: BLE001 - one failing model must not stop the run
            outcomes.append(ModelOutcome(name, "error", str(exc)))
            continue
        state[name] = digest
    _save_state(state_path, state)
    return outcomes
