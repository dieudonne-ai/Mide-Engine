"""Model evaluation: metrics (MAE/MAPE, accuracy/F1/AUC) and feature importance."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    roc_auc_score,
)

from mide.automl.task_detector import CLASSIFICATION
from mide.automl.trainer import TrainedModel


def mape(y_true: Any, y_pred: Any) -> float:
    """Mean absolute percentage error, ignoring rows where the true value is 0."""
    true, pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    mask = true != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((true[mask] - pred[mask]) / true[mask])))


def regression_metrics(y_true: Any, y_pred: Any) -> dict[str, float]:
    return {"mae": float(mean_absolute_error(y_true, y_pred)), "mape": mape(y_true, y_pred)}


def classification_metrics(
    y_true: Any, y_pred: Any, proba: np.ndarray | None = None, classes: Any = None
) -> dict[str, float]:
    """Accuracy and weighted F1; AUC when probabilities are given (binary or multiclass)."""
    out = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
    }
    if proba is not None and classes is not None and len(np.unique(y_true)) > 1:
        try:
            if len(classes) == 2:
                out["auc"] = float(roc_auc_score(y_true, proba[:, 1]))
            else:
                out["auc"] = float(
                    roc_auc_score(
                        y_true, proba, multi_class="ovr", labels=list(classes), average="weighted"
                    )
                )
        except ValueError:  # e.g. a class missing from y_true
            pass
    return out


def feature_importance(model: TrainedModel) -> dict[str, float]:
    """Normalized (sum = 1) LightGBM split-gain importance per feature, highest first."""
    pre = model.pipeline.named_steps["prep"]
    booster = model.pipeline.named_steps["model"]
    names = list(pre.get_feature_names_out())
    gains = np.asarray(booster.booster_.feature_importance(importance_type="gain"), dtype=float)
    total = gains.sum()
    if total > 0:
        gains = gains / total
    ranked = sorted(zip(names, gains, strict=False), key=lambda kv: kv[1], reverse=True)
    return {name: round(float(value), 6) for name, value in ranked}


def evaluate_model(model: TrainedModel, df: pd.DataFrame) -> dict[str, float]:
    """Compute the task metrics of ``model`` on ``df`` (must contain the target column)."""
    target = model.task.target
    data = df[df[target].notna()]
    if data.empty:
        raise ValueError("No rows with a target value to evaluate on.")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pred = model.predict(data)
        y = data[target]
        if model.task.task == CLASSIFICATION:
            proba = None
            if hasattr(model.pipeline, "predict_proba"):
                from mide.automl.trainer import _prepare

                x = _prepare(data, model.task, model.date_columns, model.features)
                proba = model.pipeline.predict_proba(x)
            classes = getattr(model.pipeline.named_steps["model"], "classes_", None)
            return classification_metrics(y, pred, proba, classes)
    return regression_metrics(y, pred)
