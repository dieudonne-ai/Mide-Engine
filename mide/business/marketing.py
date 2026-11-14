"""Marketing analytics: channel/campaign performance and budget reallocation.

Works on a campaigns DataFrame (one row per campaign). Every figure returned
(spend, revenue, ROI...) comes straight from the data so recommendations are
explainable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# A channel underperforms when its ROI is below this fraction of the median channel ROI.
UNDERPERFORM_RATIO = 0.5
# Share of an underperforming channel's budget that is suggested to move.
MAX_CUT = 0.5

_SUM_COLS = ["spend", "impressions", "clicks", "conversions", "revenue"]


def _prepare(df: pd.DataFrame, columns: dict[str, str]) -> pd.DataFrame:
    """Rename to canonical columns, coerce numerics, drop unusable rows."""
    missing = [v for k, v in columns.items() if k in ("channel", "spend", "revenue")
               and v not in df.columns]
    if missing:
        raise ValueError(f"Missing marketing columns: {missing}")
    data = pd.DataFrame({k: df[v] for k, v in columns.items() if v in df.columns})
    for col in _SUM_COLS:
        data[col] = pd.to_numeric(data[col], errors="coerce") if col in data else 0.0
    data = data.dropna(subset=["channel", "spend", "revenue"])
    data[["impressions", "clicks", "conversions"]] = data[
        ["impressions", "clicks", "conversions"]].fillna(0)
    if data.empty:
        raise ValueError("No valid marketing rows to analyse")
    return data


def _ratios(table: pd.DataFrame) -> pd.DataFrame:
    spend = table["spend"].replace(0, np.nan)
    table["roi"] = (table["revenue"] - table["spend"]) / spend
    table["roas"] = table["revenue"] / spend
    table["cost_per_conversion"] = spend / table["conversions"].replace(0, np.nan)
    table["conversion_rate"] = table["conversions"] / table["clicks"].replace(0, np.nan)
    table["ctr"] = table["clicks"] / table["impressions"].replace(0, np.nan)
    return table


def _columns(**names: str) -> dict[str, str]:
    return {"channel": names["channel_col"], "campaign": names["campaign_col"],
            "spend": names["spend_col"], "impressions": "impressions",
            "clicks": "clicks", "conversions": names["conversions_col"],
            "revenue": names["revenue_col"]}


def channel_performance(df: pd.DataFrame, channel_col: str = "channel",
                        spend_col: str = "spend", revenue_col: str = "revenue",
                        conversions_col: str = "conversions",
                        campaign_col: str = "campaign_id") -> pd.DataFrame:
    """One row per channel: totals, ROI, ROAS, cost per conversion, sorted by ROI."""
    data = _prepare(df, _columns(channel_col=channel_col, campaign_col=campaign_col,
                                 spend_col=spend_col, conversions_col=conversions_col,
                                 revenue_col=revenue_col))
    table = data.groupby("channel")[_SUM_COLS].sum()
    table.insert(0, "campaigns", data.groupby("channel").size())
    return _ratios(table).sort_values("roi", ascending=False)


def campaign_performance(df: pd.DataFrame, channel_col: str = "channel",
                         spend_col: str = "spend", revenue_col: str = "revenue",
                         conversions_col: str = "conversions",
                         campaign_col: str = "campaign_id") -> pd.DataFrame:
    """One row per campaign with the same ratios, sorted by ROI."""
    data = _prepare(df, _columns(channel_col=channel_col, campaign_col=campaign_col,
                                 spend_col=spend_col, conversions_col=conversions_col,
                                 revenue_col=revenue_col))
    if "campaign" not in data.columns:
        raise ValueError(f"Missing marketing column: {campaign_col}")
    table = data.groupby(["campaign", "channel"])[_SUM_COLS].sum().reset_index()
    return _ratios(table.set_index("campaign")).sort_values("roi", ascending=False)


def underperforming_channels(channels: pd.DataFrame,
                             ratio: float = UNDERPERFORM_RATIO) -> list[str]:
    """Channels whose ROI is below `ratio` x the median channel ROI (or negative).

    The median (not the spend-weighted total) is the baseline so that one or two
    exceptional channels do not make every other channel look weak.
    """
    median = channels["roi"].median()
    threshold = max(float(median) * ratio, 0.0) if pd.notna(median) else 0.0
    return [str(c) for c, roi in channels["roi"].items()
            if pd.notna(roi) and roi < threshold]


@dataclass
class BudgetMove:
    """Suggested shift of budget from one channel to another."""

    from_channel: str
    to_channel: str
    amount: float
    reason: str
    estimated_extra_revenue: float


@dataclass
class ReallocationPlan:
    """Budget reallocation suggestion with the figures that justify it."""

    underperforming: list[str]
    best_channel: str
    moves: list[BudgetMove] = field(default_factory=list)
    total_moved: float = 0.0
    estimated_extra_revenue: float = 0.0
    overall_roi: float = 0.0


def suggest_reallocation(channels: pd.DataFrame, max_cut: float = MAX_CUT,
                         ratio: float = UNDERPERFORM_RATIO) -> ReallocationPlan:
    """Move part of the budget from weak channels to the best-ROAS channel.

    The extra revenue is a linear estimate (marginal ROAS = average ROAS of the
    receiving channel) and is optimistic: returns diminish as spend grows.
    """
    ranked = channels.dropna(subset=["roas"])
    if ranked.empty:
        raise ValueError("No channel with spend to compare")
    best = str(ranked["roas"].idxmax())
    weak = [c for c in underperforming_channels(channels, ratio) if c != best]
    total_spend = channels["spend"].sum()
    overall = (channels["revenue"].sum() - total_spend) / total_spend if total_spend else 0.0
    median = float(channels["roi"].median())
    plan = ReallocationPlan(underperforming=weak, best_channel=best, overall_roi=float(overall))
    best_roas = float(channels.loc[best, "roas"])
    for ch in weak:
        row = channels.loc[ch]
        amount = round(float(row["spend"]) * max_cut, 2)
        lost = amount * (float(row["roas"]) if pd.notna(row["roas"]) else 0.0)
        extra = amount * best_roas - lost
        plan.moves.append(BudgetMove(
            from_channel=ch, to_channel=best, amount=amount, estimated_extra_revenue=round(extra, 2),
            reason=(f"{ch} ROI {row['roi']:.2f} vs median {median:.2f}; "
                    f"{best} returns {best_roas:.2f} revenue per unit spent")))
    plan.total_moved = round(sum(m.amount for m in plan.moves), 2)
    plan.estimated_extra_revenue = round(sum(m.estimated_extra_revenue for m in plan.moves), 2)
    return plan
