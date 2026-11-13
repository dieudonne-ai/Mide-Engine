"""Model evaluation: metrics (MAE/MAPE/RMSE/R2, accuracy/F1/AUC) and feature importance."""

from __future__ import annotations

import numpy as np
import pandas as pd

from mide.automl.task_detector import TaskType
from mide.automl.trainer import TrainedModel, _aggregate_series


def _prepare(model: TrainedModel, df: pd.DataFrame) -> pd.DataFrame:
    """Apply the same row preparation as training (time series -> one row per period)."""
    target = model.task.target
    work = df.dropna(subset=[target]).reset_index(drop=True)
    if model.task.task is TaskType.TIME_SERIES:
        work = _aggregate_series(work, model.task)
    return work


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean absolute percentage error in %, ignoring rows where the truth is 0."""
    mask = y_true != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def evaluate(model: TrainedModel, df: pd.DataFrame) -> dict[str, float]:
    """Score ``model`` on ``df`` (which must contain the target column)."""
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        mean_absolute_error,
        mean_squared_error,
        r2_score,
        roc_auc_score,
    )

    work = _prepare(model, df)
    if work.empty:
        raise ValueError("No rows to evaluate")
    target = model.task.target
    pred = model.predict(work)
    if model.task.task is TaskType.CLASSIFICATION:
        y = work[target].to_numpy(dtype=object)
        out = {
            "accuracy": float(accuracy_score(y, pred)),
            "f1_macro": float(f1_score(y, pred, average="macro", zero_division=0)),
        }
        classes = model.classes or []
        if len(classes) >= 2 and len(set(y)) >= 2:
            proba = model.model.predict_proba(model.prep.transform(work))
            try:
                if len(classes) == 2:
                    out["auc"] = float(roc_auc_score(y == classes[1], proba[:, 1]))
                else:
                    out["auc"] = float(
                        roc_auc_score(y, proba, multi_class="ovr", labels=classes)
                    )
            except ValueError:
                pass  # AUC undefined for this sample
        return out
    y = work[target].to_numpy(dtype=float)
    pred = pred.astype(float)
    out = {
        "mae": float(mean_absolute_error(y, pred)),
        "mape": mape(y, pred),
        "rmse": float(np.sqrt(mean_squared_error(y, pred))),
    }
    if len(y) > 1:
        out["r2"] = float(r2_score(y, pred))
    return out


def feature_importance(model: TrainedModel, top: int | None = None) -> dict[str, float]:
    """Normalized (sum = 1) importance of each feature, largest first."""
    items = sorted(model.feature_importance.items(), key=lambda t: -t[1])
    return dict(items[:top] if top else items)
