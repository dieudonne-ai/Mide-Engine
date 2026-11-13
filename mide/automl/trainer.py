"""Automatic training of tabular models (LightGBM) with a simple baseline to beat."""

from __future__ import annotations

import time
import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, mean_absolute_error
from sklearn.model_selection import KFold, StratifiedKFold, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from mide.automl.task_detector import CLASSIFICATION, TIMESERIES, TaskInfo, detect_task
from mide.ingestion.profiling import ID_PATTERN, profile_dataframe

# Limits on model size / effort per hardware profile.
PROFILE_LIMITS: dict[str, dict[str, int]] = {
    "tiny": {"n_estimators": 80, "num_leaves": 7, "max_rows": 50_000, "n_jobs": 1, "cv_folds": 3},
    "small": {"n_estimators": 150, "num_leaves": 7, "max_rows": 200_000, "n_jobs": 2, "cv_folds": 4},
    "medium": {"n_estimators": 300, "num_leaves": 15, "max_rows": 500_000, "n_jobs": 4, "cv_folds": 5},
    "large": {"n_estimators": 500, "num_leaves": 15, "max_rows": 1_000_000, "n_jobs": 8, "cv_folds": 5},
}  # fmt: skip
MAX_CATEGORY_RATIO = 0.5  # text-like columns (almost unique values) are dropped
LAGS = (1, 7)
DATE_PARTS = ("month", "day_of_week", "day_of_year")


@dataclass
class TrainedModel:
    """A fitted model with everything needed to predict and to explain how good it is."""

    task: TaskInfo
    pipeline: Pipeline
    features: list[str]
    date_columns: list[str]
    metric: str  # "mae" (lower is better) or "accuracy" (higher is better)
    score: float  # cross-validated score of the model
    baseline_score: float  # cross-validated score of the baseline
    baseline_name: str
    seed: int
    profile: str
    n_rows: int
    train_seconds: float
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def beats_baseline(self) -> bool:
        if self.metric == "mae":
            return self.score < self.baseline_score
        return self.score > self.baseline_score

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict for rows of `df` (same columns as at training time)."""
        data = _prepare(df, self.task, self.date_columns, self.features)
        return self.pipeline.predict(data)


def _drop_columns(df: pd.DataFrame, target: str, date_col: str | None) -> list[str]:
    """Columns unusable as features: the target, identifiers and text-like columns."""
    dropped = [target]
    for col in df.columns:
        if col in dropped or col == date_col:
            continue
        series = df[col]
        is_text = not pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(
            series
        )
        if ID_PATTERN.search(col) or (
            is_text and series.nunique() / max(len(series), 1) > MAX_CATEGORY_RATIO
        ):
            dropped.append(col)
    return dropped


def _prepare(
    df: pd.DataFrame, task: TaskInfo, date_columns: list[str], features: list[str]
) -> pd.DataFrame:
    """Turn raw columns into model features (date parts, lags for time series)."""
    out = df.copy()
    for col in date_columns:
        dates = pd.to_datetime(out[col], errors="coerce", format="mixed")
        for part in DATE_PARTS:
            out[f"{col}_{part}"] = getattr(dates.dt, part)
    if task.task == TIMESERIES and task.date_column in out.columns:
        for lag in LAGS:
            out[f"{task.target}_lag{lag}"] = out[task.target].shift(lag)
        past = out[task.target].shift(1)
        out[f"{task.target}_roll7"] = past.rolling(7, min_periods=1).mean()
        out[f"{task.target}_roll28"] = past.rolling(28, min_periods=1).mean()
    for col in features:
        if col not in out.columns:
            out[col] = np.nan
    out = out[features]
    for col in out.columns:
        if out[col].dtype == bool:
            out[col] = out[col].astype(int)
        elif not pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].astype("object").where(out[col].notna(), np.nan)
    return out


def _n_estimators(limits: dict[str, int], n_rows: int) -> int:
    """Trees grow with the data (small tables overfit quickly), capped by the profile."""
    return min(limits["n_estimators"], max(50, n_rows // 4))


def _estimator(task: str, limits: dict[str, int], seed: int, n_rows: int):
    params = {
        "n_estimators": _n_estimators(limits, n_rows),
        "num_leaves": limits["num_leaves"],
        "learning_rate": 0.03,
        "min_child_samples": 20,
        "subsample": 0.8,
        "subsample_freq": 1,
        "colsample_bytree": 0.8,
        "reg_lambda": 1.0,
        "n_jobs": limits["n_jobs"],
        "random_state": seed,
        "deterministic": True,
        "force_row_wise": True,
        "verbose": -1,
    }
    return LGBMClassifier(**params) if task == CLASSIFICATION else LGBMRegressor(**params)


def _make_pipeline(data: pd.DataFrame, task: str, limits: dict[str, int], seed: int) -> Pipeline:
    cats = [c for c in data.columns if not pd.api.types.is_numeric_dtype(data[c])]
    encoder = OrdinalEncoder(
        handle_unknown="use_encoded_value", unknown_value=-1, encoded_missing_value=-1
    )
    pre = ColumnTransformer(
        [("cat", encoder, cats)], remainder="passthrough", verbose_feature_names_out=False
    )
    return Pipeline([("prep", pre), ("model", _estimator(task, limits, seed, len(data)))])


def _baseline_predict(
    task: TaskInfo, y_train: pd.Series, y_test: pd.Series, full: pd.Series | None
) -> np.ndarray:
    """Baseline: previous value (series), majority class (classification) or mean."""
    if task.task == TIMESERIES and full is not None:
        return full.shift(1).loc[y_test.index].fillna(y_train.iloc[-1]).to_numpy()
    if task.task == CLASSIFICATION:
        return np.repeat(y_train.mode().iloc[0], len(y_test))
    return np.repeat(y_train.mean(), len(y_test))


def _splitter(task: TaskInfo, y: pd.Series, folds: int, seed: int):
    if task.task == TIMESERIES:
        return TimeSeriesSplit(n_splits=folds)
    if task.task == CLASSIFICATION and y.value_counts().min() >= folds:
        return StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    return KFold(n_splits=folds, shuffle=True, random_state=seed)


def _score(task: TaskInfo, y_true: pd.Series, y_pred: np.ndarray) -> float:
    if task.task == CLASSIFICATION:
        return float(accuracy_score(y_true, y_pred))
    return float(mean_absolute_error(y_true, y_pred))


def train_model(
    df: pd.DataFrame,
    target: str,
    *,
    profile: str = "small",
    seed: int = 42,
    date_column: str | None = None,
    task: TaskInfo | None = None,
) -> TrainedModel:
    """Train a LightGBM model on `df` for `target` and compare it to a simple baseline."""
    if profile not in PROFILE_LIMITS:
        raise ValueError(f"Unknown profile '{profile}'. Choose from {list(PROFILE_LIMITS)}")
    limits = PROFILE_LIMITS[profile]
    start = time.monotonic()
    info = task or detect_task(df, target, date_column)
    data = df[df[target].notna()].reset_index(drop=True)
    if len(data) < 20:
        raise ValueError(f"Not enough rows to train ({len(data)}; at least 20 needed).")
    if len(data) > limits["max_rows"]:
        # Series keep the most recent rows; others are sampled (seeded).
        data = (
            data.sort_values(info.date_column).tail(limits["max_rows"])
            if info.task == TIMESERIES
            else data.sample(limits["max_rows"], random_state=seed).sort_index()
        ).reset_index(drop=True)
    if info.task == TIMESERIES:
        data = data.sort_values(info.date_column).reset_index(drop=True)

    dropped = _drop_columns(data, target, info.date_column)
    date_cols = profile_dataframe(data).date_columns
    date_cols = [c for c in date_cols if c not in dropped]
    raw = [c for c in data.columns if c not in dropped and c not in date_cols]
    features = raw + [f"{c}_{p}" for c in date_cols for p in DATE_PARTS]
    if info.task == TIMESERIES:
        features += [f"{target}_lag{lag}" for lag in LAGS] + [f"{target}_roll7", f"{target}_roll28"]
    X = _prepare(data, info, date_cols, features)
    y = data[target]
    if not features:
        raise ValueError("No usable feature columns found.")

    folds = min(limits["cv_folds"], max(2, len(data) // 10))
    scores, base_scores = [], []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for train_idx, test_idx in _splitter(info, y, folds, seed).split(X, y):
            model = _make_pipeline(X, info.task, limits, seed)
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            pred = model.predict(X.iloc[test_idx])
            scores.append(_score(info, y.iloc[test_idx], pred))
            base = _baseline_predict(info, y.iloc[train_idx], y.iloc[test_idx], y)
            base_scores.append(_score(info, y.iloc[test_idx], base))
        final = _make_pipeline(X, info.task, limits, seed)
        final.fit(X, y)

    baseline_name = {CLASSIFICATION: "majority class", TIMESERIES: "previous value"}.get(
        info.task, "mean"
    )
    return TrainedModel(
        task=info,
        pipeline=final,
        features=features,
        date_columns=date_cols,
        metric="accuracy" if info.task == CLASSIFICATION else "mae",
        score=float(np.mean(scores)),
        baseline_score=float(np.mean(base_scores)),
        baseline_name=baseline_name,
        seed=seed,
        profile=profile,
        n_rows=len(data),
        train_seconds=time.monotonic() - start,
        extra={"cv_folds": folds},
    )
