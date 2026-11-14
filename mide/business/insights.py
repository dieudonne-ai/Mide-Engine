"""Business insights: headline KPIs and anomaly detection on daily sales.

Anomalies are detected on the daily revenue series after removing the weekday
pattern and the slow trend/season (centered rolling median), using a robust
(MAD-based) z-score. Consecutive anomalous days are merged into one event.
Every result carries the figures that justify it (explainability).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from mide.business.sales import daily_series

ROLLING_WINDOW = 29  # days, centered; odd so the window is symmetric
MIN_DAYS = 35
DEFAULT_THRESHOLD = 4.0  # robust z-score
MIN_RELATIVE_DEVIATION = 0.4  # ignore deviations smaller than 40% of expected


@dataclass
class Kpis:
    """Headline figures for a transactions table."""

    total_revenue: float
    orders: int
    avg_order_value: float
    customers: int | None
    start: pd.Timestamp
    end: pd.Timestamp
    last_30d_revenue: float
    previous_30d_revenue: float
    growth_30d: float | None  # relative change, None if no previous period
    best_day: pd.Timestamp
    best_day_revenue: float

    def to_dict(self) -> dict:
        return {k: (str(v.date()) if isinstance(v, pd.Timestamp) else v)
                for k, v in self.__dict__.items()}


@dataclass
class Anomaly:
    """A run of consecutive abnormal days."""

    start: pd.Timestamp
    end: pd.Timestamp
    kind: str  # "drop" or "spike"
    actual: float  # total over the run
    expected: float
    ratio: float  # actual / expected
    score: float  # peak robust z-score
    days: int = 1

    def describe(self) -> str:
        period = (str(self.start.date()) if self.start == self.end
                  else f"{self.start.date()} -> {self.end.date()}")
        return (f"{self.kind} on {period}: {self.actual:,.0f} vs "
                f"{self.expected:,.0f} expected ({self.ratio:.0%})")


@dataclass
class InsightReport:
    """KPIs plus detected anomalies."""

    kpis: Kpis
    anomalies: list[Anomaly] = field(default_factory=list)


def compute_kpis(df: pd.DataFrame, date_col: str = "date", amount_col: str = "amount",
                 order_col: str | None = "order_id",
                 customer_col: str | None = "customer_id") -> Kpis:
    """Total revenue, orders, average order value, recent growth, best day."""
    series = daily_series(df, date_col, amount_col)
    total = float(series.sum())
    if order_col and order_col in df.columns:
        orders = int(df[order_col].nunique())
    else:
        orders = len(df)
    customers = (int(df[customer_col].nunique())
                 if customer_col and customer_col in df.columns else None)
    last = float(series.iloc[-30:].sum())
    prev_slice = series.iloc[-60:-30]
    previous = float(prev_slice.sum()) if len(prev_slice) else 0.0
    growth = (last - previous) / previous if len(prev_slice) == 30 and previous > 0 else None
    best = series.idxmax()
    return Kpis(
        total_revenue=total, orders=orders,
        avg_order_value=total / orders if orders else 0.0,
        customers=customers, start=series.index[0], end=series.index[-1],
        last_30d_revenue=last, previous_30d_revenue=previous, growth_30d=growth,
        best_day=best, best_day_revenue=float(series.max()),
    )


def _expected(series: pd.Series) -> pd.Series:
    """Expected daily value: weekday factor x centered rolling median level."""
    weekday = series.groupby(series.index.day_of_week).transform("median")
    factor = weekday / weekday.mean() if weekday.mean() > 0 else pd.Series(1.0, index=series.index)
    factor = factor.replace(0, 1.0)
    level = (series / factor).rolling(ROLLING_WINDOW, center=True, min_periods=7).median()
    return (level * factor).clip(lower=1e-9)


def detect_anomalies(series: pd.Series, threshold: float = DEFAULT_THRESHOLD,
                     min_deviation: float = MIN_RELATIVE_DEVIATION) -> list[Anomaly]:
    """Find abnormal drops/spikes in a daily series (index = consecutive days)."""
    series = series.astype(float)
    if len(series) < MIN_DAYS:
        raise ValueError(f"Need at least {MIN_DAYS} days of data to detect anomalies")
    expected = _expected(series)
    resid = np.log((series.clip(lower=0) + 1.0) / (expected + 1.0))
    mad = float(np.median(np.abs(resid - np.median(resid))))
    scale = max(1.4826 * mad, 0.02)
    z = (resid - np.median(resid)) / scale
    ratio = series / expected
    flagged = (z.abs() >= threshold) & ((ratio - 1).abs() >= min_deviation)

    anomalies: list[Anomaly] = []
    run: list[pd.Timestamp] = []

    def close() -> None:
        if not run:
            return
        idx = pd.DatetimeIndex(run)
        actual, exp = float(series[idx].sum()), float(expected[idx].sum())
        anomalies.append(Anomaly(
            start=idx[0], end=idx[-1], kind="drop" if actual < exp else "spike",
            actual=actual, expected=exp, ratio=actual / exp if exp else float("inf"),
            score=float(z[idx].abs().max()), days=len(idx)))
        run.clear()

    for day, hit in flagged.items():
        if hit and run and (day - run[-1]).days == 1 and (z[day] > 0) == (z[run[-1]] > 0):
            run.append(day)
        else:
            close()
            if hit:
                run.append(day)
    close()
    return anomalies


def analyze(df: pd.DataFrame, date_col: str = "date", amount_col: str = "amount",
            threshold: float = DEFAULT_THRESHOLD, **kpi_kwargs) -> InsightReport:
    """KPIs and anomalies for a transactions table."""
    series = daily_series(df, date_col, amount_col)
    return InsightReport(
        kpis=compute_kpis(df, date_col, amount_col, **kpi_kwargs),
        anomalies=detect_anomalies(series, threshold),
    )
