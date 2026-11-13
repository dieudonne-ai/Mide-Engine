"""Detect the machine-learning task (regression / classification / time series)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd

from mide.ingestion.profiling import profile_dataframe

MAX_CLASSES_NUMERIC = 10  # integer-valued targets with <= this many values are classes
MIN_DATES_FOR_SERIES = 10  # distinct timestamps needed to talk about a series


class TaskType(str, Enum):
    """Supported learning tasks."""

    REGRESSION = "regression"
    CLASSIFICATION = "classification"
    TIME_SERIES = "time_series"


@dataclass
class TaskInfo:
    """Result of task detection."""

    task: TaskType
    target: str
    reason: str
    date_column: str | None = None
    frequency: str | None = None  # pandas offset alias for time series (D, W, MS...)
    n_classes: int | None = None


def _is_class_like_numeric(series: pd.Series) -> bool:
    values = series.dropna()
    if values.empty or values.nunique() > MAX_CLASSES_NUMERIC:
        return False
    return bool((values % 1 == 0).all())


def _infer_frequency(dates: pd.Series) -> str:
    """Rough frequency of a date column: D, W, MS (monthly) or D by default."""
    unique = pd.Series(pd.to_datetime(dates, errors="coerce").dropna().unique()).sort_values()
    if len(unique) < 3:
        return "D"
    median_gap = unique.diff().dropna().dt.days.median()
    if median_gap >= 25:
        return "MS"
    if median_gap >= 6:
        return "W"
    return "D"


def _find_date_column(df: pd.DataFrame, target: str, date_column: str | None) -> str | None:
    if date_column is not None:
        if date_column not in df.columns:
            raise ValueError(f"Date column '{date_column}' not found in dataset")
        return date_column
    dates = [c for c in profile_dataframe(df).date_columns if c != target]
    return dates[0] if dates else None


def detect_task(
    df: pd.DataFrame, target: str, date_column: str | None = None
) -> TaskInfo:
    """Decide which task fits ``target`` in ``df``.

    - non-numeric or boolean target, or few integer values -> classification;
    - continuous numeric target with a usable date column -> time series
      (rows are aggregated per period by the trainer);
    - otherwise -> regression.
    """
    if target not in df.columns:
        raise ValueError(f"Target column '{target}' not found in dataset")
    series = df[target]
    if series.dropna().empty:
        raise ValueError(f"Target column '{target}' has no values")

    if not pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
        n = int(series.nunique(dropna=True))
        if n < 2:
            raise ValueError(f"Target column '{target}' has fewer than 2 distinct values")
        return TaskInfo(
            TaskType.CLASSIFICATION, target, f"non-numeric target with {n} classes", n_classes=n
        )
    if _is_class_like_numeric(series):
        n = int(series.nunique(dropna=True))
        if n < 2:
            raise ValueError(f"Target column '{target}' has fewer than 2 distinct values")
        return TaskInfo(
            TaskType.CLASSIFICATION, target, f"integer target with only {n} values", n_classes=n
        )

    date_col = _find_date_column(df, target, date_column)
    if date_col is not None:
        parsed = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
        if parsed.nunique() >= MIN_DATES_FOR_SERIES:
            return TaskInfo(
                TaskType.TIME_SERIES,
                target,
                f"numeric target with date column '{date_col}'",
                date_column=date_col,
                frequency=_infer_frequency(parsed),
            )
    return TaskInfo(TaskType.REGRESSION, target, "continuous numeric target, no usable date column")
