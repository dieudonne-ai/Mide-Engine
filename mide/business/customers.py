"""Customer analytics: RFM segmentation and churn risk scoring.

Works on a transactions DataFrame (one row per order line). Every result keeps
the raw figures (recency, frequency, monetary, typical gap) that justify it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

HIGH_RISK = 0.7
MEDIUM_RISK = 0.4
# Churn risk is 0.5 when a customer is silent for this many "typical gaps".
HALF_RISK_GAPS = 3.0


def _score(values: pd.Series, higher_is_better: bool, bins: int = 5) -> pd.Series:
    """Score 1..bins by rank quantile (robust to ties and skewed data)."""
    ranks = values.rank(method="first", ascending=higher_is_better)
    n = len(values)
    scores = np.ceil(ranks / n * bins).clip(1, bins).astype(int)
    return pd.Series(scores, index=values.index)


def _segment(r: int, f: int, m: int) -> str:
    fm = (f + m) / 2
    if r >= 4 and fm >= 4:
        return "Champions"
    if r >= 3 and fm >= 3.5:
        return "Loyal"
    if r >= 4 and f <= 2:
        return "New / promising"
    if r <= 2 and fm >= 3.5:
        return "At risk"
    if r <= 2 and fm <= 2:
        return "Hibernating"
    return "Needs attention"


def customer_table(df: pd.DataFrame, customer_col: str = "customer_id",
                   date_col: str = "date", amount_col: str = "amount",
                   order_col: str = "order_id",
                   reference_date: pd.Timestamp | str | None = None) -> pd.DataFrame:
    """One row per customer: recency, frequency, monetary and purchase rhythm."""
    data = pd.DataFrame({
        "customer": df[customer_col],
        "date": pd.to_datetime(df[date_col], errors="coerce").dt.normalize(),
        "amount": pd.to_numeric(df[amount_col], errors="coerce"),
        "order": df[order_col] if order_col in df.columns else np.arange(len(df)),
    }).dropna(subset=["customer", "date", "amount"])
    if data.empty:
        raise ValueError("No valid customer transactions to analyse")
    ref = pd.Timestamp(reference_date) if reference_date is not None else data["date"].max()
    grouped = data.groupby("customer")
    table = pd.DataFrame({
        "last_purchase": grouped["date"].max(),
        "first_purchase": grouped["date"].min(),
        "frequency": grouped["order"].nunique(),
        "monetary": grouped["amount"].sum(),
    })
    table["recency_days"] = (ref - table["last_purchase"]).dt.days.clip(lower=0)
    span = (table["last_purchase"] - table["first_purchase"]).dt.days
    table["typical_gap_days"] = np.where(table["frequency"] > 1,
                                         span / (table["frequency"] - 1).clip(lower=1),
                                         np.nan)
    return table.sort_index()


def rfm_segments(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """RFM table with 1-5 scores and a named segment per customer."""
    table = customer_table(df, **kwargs)
    table["r_score"] = _score(table["recency_days"], higher_is_better=False)
    table["f_score"] = _score(table["frequency"], higher_is_better=True)
    table["m_score"] = _score(table["monetary"], higher_is_better=True)
    table["segment"] = [_segment(r, f, m) for r, f, m in
                        zip(table["r_score"], table["f_score"], table["m_score"])]
    return table


def segment_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    """Customers, revenue and share of revenue per segment."""
    summary = rfm.groupby("segment").agg(
        customers=("monetary", "size"),
        revenue=("monetary", "sum"),
        avg_recency_days=("recency_days", "mean"),
        avg_frequency=("frequency", "mean"),
    )
    summary["revenue_share_pct"] = (100 * summary["revenue"] / summary["revenue"].sum()).round(1)
    return summary.sort_values("revenue", ascending=False)


@dataclass
class ChurnReport:
    """Churn risk per customer and the figures behind it."""

    scores: pd.DataFrame
    high_risk: list[str] = field(default_factory=list)
    revenue_at_risk: float = 0.0
    notes: list[str] = field(default_factory=list)


def churn_risk(df: pd.DataFrame, **kwargs) -> ChurnReport:
    """Score churn risk in [0, 1] from silence relative to each customer's own rhythm.

    ratio = days since last purchase / typical gap between purchases (population
    median for customers with a single order); risk = 1 - 0.5 ** (ratio / 3), so
    3 typical gaps of silence = 50% risk.
    """
    table = customer_table(df, **kwargs)
    median_gap = table["typical_gap_days"].median()
    if pd.isna(median_gap):
        median_gap = 30.0
    gap = table["typical_gap_days"].fillna(median_gap).clip(lower=1.0)
    table["expected_gap_days"] = gap
    ratio = table["recency_days"] / gap
    table["risk"] = (1 - 0.5 ** (ratio / HALF_RISK_GAPS)).round(3)
    table["risk_level"] = pd.cut(table["risk"], [-0.01, MEDIUM_RISK, HIGH_RISK, 1.0],
                                 labels=["low", "medium", "high"]).astype(str)
    high = table[table["risk_level"] == "high"]
    notes = [(f"{len(high)} customers at high risk ({len(high) / len(table):.0%}), "
              f"representing {high['monetary'].sum():.0f} in past revenue")]
    return ChurnReport(
        scores=table.sort_values("risk", ascending=False),
        high_risk=list(high.sort_values("monetary", ascending=False).index),
        revenue_at_risk=float(high["monetary"].sum()),
        notes=notes,
    )
