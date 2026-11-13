"""Sales analytics: forecasts, top/flop products, trends and seasonality.

All functions take a transactions DataFrame (one row per order line) and work
with plain pandas/numpy so they stay light on small machines. Every result
carries the figures that justify it (explainability).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DEFAULT_HORIZONS = (30, 60, 90)


def daily_series(df: pd.DataFrame, date_col: str = "date",
                 amount_col: str = "amount") -> pd.Series:
    """Total amount per calendar day (missing days filled with 0)."""
    dates = pd.to_datetime(df[date_col], errors="coerce")
    amounts = pd.to_numeric(df[amount_col], errors="coerce")
    series = amounts.groupby(dates.dt.normalize()).sum()
    series = series[series.index.notna()].sort_index()
    if series.empty:
        raise ValueError("No valid dates/amounts to analyse")
    return series.asfreq("D", fill_value=0.0)


# --------------------------------------------------------------------- forecast


@dataclass
class Forecast:
    """Daily forecast and its totals per horizon."""

    daily: pd.Series
    totals: dict[int, float]
    previous_totals: dict[int, float]
    growth_pct: dict[int, float | None]
    history_days: int = 0
    notes: list[str] = field(default_factory=list)


def _design(dates: pd.DatetimeIndex, origin: pd.Timestamp, yearly: bool) -> np.ndarray:
    t = ((dates - origin).days.to_numpy() / 365.0)[:, None]
    weekday = np.eye(7)[dates.day_of_week.to_numpy()]  # one column per weekday (no intercept)
    cols = [t, weekday]
    if yearly:
        angle = 2 * np.pi * dates.day_of_year.to_numpy() / 365.25
        cols.append(np.column_stack([np.sin(angle), np.cos(angle)]))
    return np.hstack(cols)


def forecast_sales(df: pd.DataFrame, horizons: tuple[int, ...] = DEFAULT_HORIZONS,
                   date_col: str = "date", amount_col: str = "amount") -> Forecast:
    """Forecast daily sales with trend + weekday + yearly seasonality (least squares).

    Outlier days (|residual| > 3 sigma, e.g. outages or flash sales) are excluded
    from a second fit so they do not distort the forecast.
    """
    series = daily_series(df, date_col, amount_col)
    notes: list[str] = []
    if len(series) < 28:
        raise ValueError("At least 28 days of history are needed to forecast")
    yearly = len(series) >= 365
    if not yearly:
        notes.append("Less than one year of history: yearly seasonality not modelled.")
    origin = series.index[0]
    x = _design(series.index, origin, yearly)
    y = series.to_numpy(dtype=float)
    keep = np.ones(len(y), dtype=bool)
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    for _ in range(2):
        resid = y - x @ beta
        sigma = resid[keep].std() or 1.0
        keep = np.abs(resid) <= 3 * sigma
        beta = np.linalg.lstsq(x[keep], y[keep], rcond=None)[0]
    if (~keep).any():
        notes.append(f"{int((~keep).sum())} anomalous day(s) excluded from the fit.")

    horizon_max = max(horizons)
    future_idx = pd.date_range(series.index[-1] + pd.Timedelta(days=1),
                               periods=horizon_max, freq="D")
    pred = np.clip(_design(future_idx, origin, yearly) @ beta, 0, None)
    daily = pd.Series(pred, index=future_idx)

    totals, previous, growth = {}, {}, {}
    for h in horizons:
        totals[h] = float(daily.iloc[:h].sum())
        prev = float(series.iloc[-h:].sum()) if len(series) >= h else float("nan")
        previous[h] = prev
        growth[h] = (totals[h] / prev - 1) * 100 if prev and not np.isnan(prev) else None
    return Forecast(daily, totals, previous, growth, len(series), notes)


# ------------------------------------------------------------------- products


def product_ranking(df: pd.DataFrame, n: int = 3, product_col: str = "product_id",
                    amount_col: str = "amount") -> dict[str, pd.DataFrame]:
    """Top and flop products by revenue, with their share of total revenue."""
    revenue = (pd.to_numeric(df[amount_col], errors="coerce")
               .groupby(df[product_col]).sum().sort_values(ascending=False))
    table = revenue.rename("revenue").to_frame()
    table["share_pct"] = table["revenue"] / table["revenue"].sum() * 100
    return {"top": table.head(n), "flop": table.tail(n).iloc[::-1]}


# --------------------------------------------------------------------- trends


@dataclass
class Trend:
    """Monthly revenue, recent momentum and year-over-year change."""

    monthly: pd.Series
    last_3m_growth_pct: float | None
    yoy_growth_pct: float | None
    direction: str  # "up" | "down" | "flat"


def sales_trend(df: pd.DataFrame, date_col: str = "date",
                amount_col: str = "amount") -> Trend:
    """Monthly totals, last-3-months vs previous-3-months growth and YoY growth."""
    daily = daily_series(df, date_col, amount_col)
    monthly = daily.resample("MS").sum()
    # Ignore a partial last month so it does not look like a drop.
    if len(daily) and daily.index[-1] != daily.index[-1] + pd.offsets.MonthEnd(0):
        monthly = monthly.iloc[:-1]
    last_3m = None
    if len(monthly) >= 6:
        recent, before = monthly.iloc[-3:].sum(), monthly.iloc[-6:-3].sum()
        last_3m = float((recent / before - 1) * 100) if before else None
    yoy = None
    if len(monthly) >= 24:
        recent, before = monthly.iloc[-12:].sum(), monthly.iloc[-24:-12].sum()
        yoy = float((recent / before - 1) * 100) if before else None
    ref = yoy if yoy is not None else last_3m
    direction = "flat" if ref is None or abs(ref) < 3 else ("up" if ref > 0 else "down")
    return Trend(monthly, last_3m, yoy, direction)


# ---------------------------------------------------------------- seasonality


@dataclass
class Seasonality:
    """Seasonal indices (1.0 = average) and the detected peaks."""

    monthly_index: dict[str, float]
    weekday_index: dict[str, float]
    peak_month: str
    trough_month: str
    peak_weekday: str
    has_yearly_seasonality: bool
    amplitude: float


def detect_seasonality(df: pd.DataFrame, date_col: str = "date",
                       amount_col: str = "amount",
                       threshold: float = 0.15) -> Seasonality:
    """Seasonal indices per month and weekday after removing the linear trend.

    Yearly seasonality is flagged when the gap between the highest and lowest
    monthly index exceeds ``threshold`` and at least 12 months are available.
    """
    daily = daily_series(df, date_col, amount_col)
    t = np.arange(len(daily), dtype=float)
    slope, intercept = np.polyfit(t, daily.to_numpy(), 1)
    trend = np.clip(slope * t + intercept, 1e-9, None)
    ratio = pd.Series(daily.to_numpy() / trend, index=daily.index)
    # Median-based clipping keeps outage days / flash sales from skewing the indices.
    ratio = ratio.clip(upper=ratio.quantile(0.99), lower=ratio.quantile(0.01))
    by_month = ratio.groupby(ratio.index.month).mean()
    by_weekday = ratio.groupby(ratio.index.day_of_week).mean()
    month_idx = by_month / by_month.mean()
    week_idx = by_weekday / by_weekday.mean()
    amplitude = float(month_idx.max() - month_idx.min())
    return Seasonality(
        monthly_index={MONTH_NAMES[m - 1]: float(v) for m, v in month_idx.items()},
        weekday_index={WEEKDAY_NAMES[d]: float(v) for d, v in week_idx.items()},
        peak_month=MONTH_NAMES[int(month_idx.idxmax()) - 1],
        trough_month=MONTH_NAMES[int(month_idx.idxmin()) - 1],
        peak_weekday=WEEKDAY_NAMES[int(week_idx.idxmax())],
        has_yearly_seasonality=bool(len(by_month) == 12 and len(daily) >= 365
                                    and amplitude >= threshold),
        amplitude=amplitude,
    )
