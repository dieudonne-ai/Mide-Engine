"""Automatic training: data preparation, cross-validation, LightGBM vs. a naive baseline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from mide.automl.task_detector import TaskInfo, TaskType, detect_task
from mide.hardware.profiler import Profile

ID_UNIQUE_RATIO = 0.9  # text columns with this share of unique values are treated as identifiers
MAX_CATEGORIES = 50  # text columns with more distinct values are dropped
DATE_PARTS = ("year", "month", "day_of_week", "day_of_year", "day")


@dataclass(frozen=True)
class TrainingLimits:
    """Resource limits derived from the hardware profile."""

    n_estimators: int
    num_leaves: int
    max_rows: int
    cv_splits: int
    n_jobs: int


LIMITS: dict[str, TrainingLimits] = {
    "tiny": TrainingLimits(80, 7, 50_000, 3, 1),
    "small": TrainingLimits(150, 15, 200_000, 4, 2),
    "medium": TrainingLimits(300, 31, 1_000_000, 5, 4),
    "large": TrainingLimits(500, 63, 2_000_000, 5, 8),
}


@dataclass
class FeaturePrep:
    """Turns a raw dataframe into a numeric feature matrix, remembering the fitted layout."""

    target: str
    date_column: str | None = None
    numeric: list[str] = field(default_factory=list)
    categorical: dict[str, list[str]] = field(default_factory=dict)
    dates: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)

    def fit(self, df: pd.DataFrame) -> FeaturePrep:
        for col in df.columns:
            if col == self.target:
                continue
            s = df[col]
            if col == self.date_column or _looks_like_date(s):
                self.dates.append(col)
            elif pd.api.types.is_bool_dtype(s) or pd.api.types.is_numeric_dtype(s):
                if s.nunique(dropna=True) > 1:
                    self.numeric.append(col)
            else:
                n = s.nunique(dropna=True)
                if 1 < n <= MAX_CATEGORIES and n / max(len(s), 1) < ID_UNIQUE_RATIO:
                    self.categorical[col] = sorted(s.dropna().astype(str).unique())
        self.columns = list(self.transform(df).columns)
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out: dict[str, Any] = {}
        for col in self.numeric:
            out[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
        for col, cats in self.categorical.items():
            out[col] = df[col].astype(str).map({c: i for i, c in enumerate(cats)}).fillna(-1).astype(float)
        for col in self.dates:
            parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
            for part in DATE_PARTS:
                out[f"{col}_{part}"] = getattr(parsed.dt, part).astype(float)
            out[f"{col}_ordinal"] = (parsed - pd.Timestamp("2000-01-01")).dt.days.astype(float)
        frame = pd.DataFrame(out, index=df.index)
        if self.columns:
            frame = frame.reindex(columns=self.columns)
        return frame


def _looks_like_date(s: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(s):
        return True
    if pd.api.types.is_numeric_dtype(s) or s.dtype == bool:
        return False
    sample = s.dropna().astype(str).head(50)
    if sample.empty or not sample.str.match(r"^\d{4}-\d{2}(-\d{2})?").all():
        return False
    return bool(pd.to_datetime(sample, errors="coerce", format="mixed").notna().all())


@dataclass
class TrainedModel:
    """A fitted model plus everything needed to predict and to report."""

    task: TaskInfo
    prep: FeaturePrep
    model: Any
    classes: list[Any] | None
    metrics: dict[str, float]
    baseline_metrics: dict[str, float]
    primary_metric: str
    beats_baseline: bool
    n_rows: int
    n_features: int
    seed: int
    profile: str
    feature_importance: dict[str, float]

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict for rows of ``df`` (class labels for classification)."""
        pred = self.model.predict(self.prep.transform(df))
        if self.classes is not None:
            return np.asarray(self.classes, dtype=object)[np.asarray(pred).astype(int)]
        return np.asarray(pred)


def _aggregate_series(df: pd.DataFrame, info: TaskInfo) -> pd.DataFrame:
    """One row per period (sum of the target), sorted by date."""
    assert info.date_column is not None
    dates = pd.to_datetime(df[info.date_column], errors="coerce", format="mixed")
    work = pd.DataFrame({info.date_column: dates, info.target: df[info.target]}).dropna(
        subset=[info.date_column]
    )
    freq = info.frequency or "D"
    grouped = work.set_index(info.date_column)[info.target].resample(freq).sum().reset_index()
    return grouped


def _splits(task: TaskType, y: np.ndarray, n_splits: int, seed: int):
    from sklearn.model_selection import KFold, StratifiedKFold, TimeSeriesSplit

    if task is TaskType.TIME_SERIES:
        return TimeSeriesSplit(n_splits=n_splits)
    if task is TaskType.CLASSIFICATION:
        smallest = int(pd.Series(y).value_counts().min())
        return StratifiedKFold(max(2, min(n_splits, smallest)), shuffle=True, random_state=seed)
    return KFold(n_splits, shuffle=True, random_state=seed)


def _make_model(task: TaskType, limits: TrainingLimits, seed: int, n_classes: int):
    import lightgbm as lgb

    params = {
        "n_estimators": limits.n_estimators,
        "num_leaves": limits.num_leaves,
        "learning_rate": 0.05,
        "min_child_samples": 5,
        "subsample": 0.9,
        "subsample_freq": 1,
        "colsample_bytree": 0.9,
        "random_state": seed,
        "n_jobs": limits.n_jobs,
        "deterministic": True,
        "force_row_wise": True,
        "verbose": -1,
    }
    if task is TaskType.CLASSIFICATION:
        return lgb.LGBMClassifier(**params)
    return lgb.LGBMRegressor(**params)


def _baseline_predict(task: TaskType, y_train: np.ndarray, n: int) -> np.ndarray:
    if task is TaskType.CLASSIFICATION:
        return np.full(n, pd.Series(y_train).mode().iloc[0])
    if task is TaskType.TIME_SERIES:
        return np.full(n, y_train[-1])  # naive: repeat the last observation
    return np.full(n, float(np.mean(y_train)))


def _score(task: TaskType, y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error

    if task is TaskType.CLASSIFICATION:
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        }
    return {"mae": float(mean_absolute_error(y_true, y_pred))}


def _mean(rows: list[dict[str, float]]) -> dict[str, float]:
    return {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}


def train(
    df: pd.DataFrame,
    target: str,
    *,
    profile: Profile | str = "small",
    seed: int = 42,
    task: TaskInfo | None = None,
    date_column: str | None = None,
) -> TrainedModel:
    """Train a LightGBM model on ``df`` and compare it with a naive baseline by cross-validation.

    Resource usage (trees, leaves, rows, folds, threads) follows the hardware ``profile``.
    Time series are aggregated per period and validated with forward-chaining splits.
    """
    if profile not in LIMITS:
        raise ValueError(f"Unknown profile '{profile}'")
    limits = LIMITS[profile]
    info = task or detect_task(df, target, date_column)
    work = df.dropna(subset=[target]).reset_index(drop=True)
    if info.task is TaskType.TIME_SERIES:
        if info.date_column is None:
            raise ValueError("A time series task needs a date column")
        work = _aggregate_series(work, info)
    elif len(work) > limits.max_rows:
        work = work.sample(limits.max_rows, random_state=seed).reset_index(drop=True)
    if len(work) < 20:
        raise ValueError(f"Not enough rows to train ({len(work)}); at least 20 are needed")

    prep = FeaturePrep(target, info.date_column if info.task is TaskType.TIME_SERIES else None)
    prep.fit(work)
    if not prep.columns:
        raise ValueError("No usable feature columns found")
    X = prep.transform(work)

    classes: list[Any] | None = None
    if info.task is TaskType.CLASSIFICATION:
        codes, uniques = pd.factorize(work[target], sort=True)
        y = codes
        classes = list(uniques)
    else:
        y = work[target].to_numpy(dtype=float)

    model_scores: list[dict[str, float]] = []
    base_scores: list[dict[str, float]] = []
    splitter = _splits(info.task, y, limits.cv_splits, seed)
    for tr, te in splitter.split(X, y):
        if info.task is TaskType.CLASSIFICATION and len(np.unique(y[tr])) < 2:
            continue
        fold = _make_model(info.task, limits, seed, len(classes or []))
        fold.fit(X.iloc[tr], y[tr])
        model_scores.append(_score(info.task, y[te], fold.predict(X.iloc[te])))
        base_scores.append(_score(info.task, y[te], _baseline_predict(info.task, y[tr], len(te))))
    if not model_scores:
        raise ValueError("Cross-validation failed: dataset too small or degenerate")

    metrics, baseline = _mean(model_scores), _mean(base_scores)
    if info.task is TaskType.CLASSIFICATION:
        primary, beats = "accuracy", metrics["accuracy"] > baseline["accuracy"]
    else:
        primary, beats = "mae", metrics["mae"] < baseline["mae"]

    final = _make_model(info.task, limits, seed, len(classes or []))
    final.fit(X, y)
    total = float(sum(final.feature_importances_)) or 1.0
    importance = {
        c: float(i) / total
        for c, i in sorted(zip(prep.columns, final.feature_importances_, strict=True),
                           key=lambda t: -t[1])
    }
    return TrainedModel(
        task=info, prep=prep, model=final, classes=classes, metrics=metrics,
        baseline_metrics=baseline, primary_metric=primary, beats_baseline=bool(beats),
        n_rows=len(work), n_features=len(prep.columns), seed=seed, profile=str(profile),
        feature_importance=importance,
    )
