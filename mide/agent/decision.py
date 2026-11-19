"""Turns business-module results into actionable, sourced recommendations."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import pandas as pd

from mide.business import customers, insights, marketing, sales
from mide.llm.prompts import format_passages
from mide.llm.runtime import LLM
from mide.rag.retriever import Passage


@dataclass
class Finding:
    """Figures produced by one business module (the evidence behind advice)."""

    module: str
    facts: dict[str, str] = field(default_factory=dict)


@dataclass
class BusinessData:
    """Tables the business modules work on (any may be missing)."""

    sales: pd.DataFrame | None = None
    campaigns: pd.DataFrame | None = None
    products: pd.DataFrame | None = None  # optional catalog: product_id -> name


@dataclass
class Recommendation:
    """LLM text plus the deterministic figures used to produce it."""

    text: str
    findings: list[Finding]
    passages: list[Passage] = field(default_factory=list)

    def data_used(self, language: str = "fr") -> str:
        title = "Données utilisées" if language == "fr" else "Data used"
        lines = [f"- [{f.module}] {k}: {v}" for f in self.findings for k, v in f.facts.items()]
        return f"{title}:\n" + "\n".join(lines) if lines else ""


_SALES_COLS = {"date", "amount"}
_CAMPAIGN_COLS = {"channel", "spend", "revenue"}
_PRODUCT_COLS = {"product_id", "name"}


def detect_tables(frames: dict[str, pd.DataFrame]) -> BusinessData:
    """Pick the sales, campaigns and product-catalog tables among datasets by their columns."""
    data = BusinessData()
    for df in frames.values():
        cols = set(df.columns)
        if data.sales is None and _SALES_COLS <= cols and "customer_id" in cols:
            data.sales = df
        elif data.campaigns is None and _CAMPAIGN_COLS <= cols:
            data.campaigns = df
        elif data.products is None and _PRODUCT_COLS <= cols and "date" not in cols:
            data.products = df
    return data


def _money(x: float) -> str:
    return f"{x:,.0f}"


def _ratio(x: float) -> str:
    return "n/a" if pd.isna(x) else f"{x:.2f}"


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:+.1f}%"


def _product_list(table: pd.DataFrame, names: dict[str, str]) -> str:
    """'P001 Rice 25kg (43.2%), ...' (id only when the name is unknown)."""
    labels = (f"{p} {names[str(p)]}" if names.get(str(p)) else str(p) for p in table.index)
    return ", ".join(f"{label} ({share:.1f}%)" for label, share in zip(labels, table["share_pct"]))


def _months_compared(monthly: pd.Series, size: int) -> str:
    """'(2024-10 -> 2024-12 vs 2024-07 -> 2024-09)': the last ``size`` months vs the ones before."""
    idx = monthly.index
    if len(idx) < 2 * size:
        return ""
    recent = f"{idx[-size]:%Y-%m} -> {idx[-1]:%Y-%m}"
    before = f"{idx[-2 * size]:%Y-%m} -> {idx[-size - 1]:%Y-%m}"
    return f" ({recent} vs {before})"


def _trend_text(trend: sales.Trend) -> str:
    """Direction, the figure it is based on (YoY when available), recent momentum, and
    the months each growth figure compares (complete months only)."""
    parts = [trend.direction]
    if trend.yoy_growth_pct is not None:
        parts.append(f"YoY {_pct(trend.yoy_growth_pct)}{_months_compared(trend.monthly, 12)}")
    recent = _pct(trend.last_3m_growth_pct)
    if trend.last_3m_growth_pct is not None:
        recent += _months_compared(trend.monthly, 3)
    parts.append(f"last 3 months {recent}")
    return ", ".join(parts)


def _forecast_text(forecast: sales.Forecast, horizon: int) -> str:
    """Total for one horizon, the dates it covers (it starts after the last data day) and growth."""
    days = forecast.daily.index[:horizon]
    period = f"{days[0]:%Y-%m-%d} -> {days[-1]:%Y-%m-%d}"
    growth = _pct(forecast.growth_pct[horizon])
    return f"{_money(forecast.totals[horizon])} for {period} ({growth} vs previous {horizon}d)"


def _sales_finding(df: pd.DataFrame, products: pd.DataFrame | None = None) -> Finding:
    forecast = sales.forecast_sales(df)
    trend = sales.sales_trend(df)
    ranking = sales.product_ranking(df, n=2) if "product_id" in df.columns else None
    facts = {f"forecast {h}d": _forecast_text(forecast, h) for h in forecast.totals}
    facts["trend"] = _trend_text(trend)
    if ranking is not None:
        names = sales.product_names(products) if products is not None else {}
        facts["top products"] = _product_list(ranking["top"], names)
        facts["flop products"] = _product_list(ranking["flop"], names)
    return Finding("sales", facts)


_MAX_CHURN_NAMED = 3


def _customers_finding(df: pd.DataFrame) -> Finding:
    summary = customers.segment_summary(customers.rfm_segments(df))
    churn = customers.churn_risk(df)
    facts = {f"segment {seg}": f"{int(r.customers)} customers, {r.revenue_share_pct}% of revenue"
             for seg, r in summary.head(3).iterrows()}
    # Name the most valuable at-risk customers so the action says whom to contact.
    top = churn.high_risk[:_MAX_CHURN_NAMED]
    named = ""
    if top:
        more = ", ..." if len(churn.high_risk) > len(top) else ""
        named = f" (top: {', '.join(map(str, top))}{more})"
    facts["churn"] = (f"{len(churn.high_risk)} customers at high risk{named}, "
                      f"{_money(churn.revenue_at_risk)} past revenue at risk")
    return Finding("customers", facts)


def _marketing_finding(df: pd.DataFrame) -> Finding:
    channels = marketing.channel_performance(df)
    plan = marketing.suggest_reallocation(channels)
    # Cite the totals behind each ratio, so "ROI 41.54" cannot be read as 41.54%.
    facts = {f"channel {c}": (f"spend {_money(r.spend)}, revenue {_money(r.revenue)}: "
                              f"ROI {_ratio(r.roi)}, ROAS {_ratio(r.roas)}")
             for c, r in channels.iterrows()}
    facts["underperforming"] = ", ".join(plan.underperforming) or "none"
    facts["best channel"] = plan.best_channel
    best_roas = float(channels.loc[plan.best_channel, "roas"])
    for m in plan.moves:
        # Linear estimate at the receiving channel's average ROAS: an upper bound,
        # since returns diminish as spend grows. Say so next to the figure.
        facts[f"move {m.from_channel}"] = (
            f"{_money(m.amount)} to {m.to_channel}, est. extra revenue up to "
            f"{_money(m.estimated_extra_revenue)} (linear, at {m.to_channel} ROAS "
            f"{best_roas:.2f}; returns diminish)")
    return Finding("marketing", facts)


_MAX_ANOMALIES = 5


def _insights_finding(df: pd.DataFrame) -> Finding:
    report = insights.analyze(df)
    k = report.kpis
    period = f"{k.start.date()} -> {k.end.date()}"
    growth = ("n/a" if k.growth_30d is None
              else f"{k.growth_30d:+.1%} (30 days to {k.end.date()} vs previous 30)")
    facts = {
        "revenue": f"{_money(k.total_revenue)} for {period}", "orders": f"{k.orders:,}",
        "average order value": _money(k.avg_order_value),
        "30d growth": growth,
    }
    # Keep the most recent anomalies (detection order is chronological).
    for i, a in enumerate(report.anomalies[-_MAX_ANOMALIES:], start=1):
        facts[f"anomaly {i}"] = a.describe()
    return Finding("insights", facts)


_BUILDERS: dict[str, tuple[str, Callable[[pd.DataFrame, BusinessData], Finding]]] = {
    "sales": ("sales", lambda df, data: _sales_finding(df, data.products)),
    "customers": ("sales", lambda df, _: _customers_finding(df)),
    "insights": ("sales", lambda df, _: _insights_finding(df)),
    "marketing": ("campaigns", lambda df, _: _marketing_finding(df)),
}


def run_modules(modules: Sequence[str], data: BusinessData) -> list[Finding]:
    """Run the requested modules; a module without its table or enough data is skipped."""
    findings: list[Finding] = []
    for name in modules:
        table_name, builder = _BUILDERS[name]
        table = getattr(data, table_name)
        if table is None:
            continue
        try:
            findings.append(builder(table, data))
        except ValueError:
            continue
    return findings


_SYSTEM = {
    "fr": ("Tu es MIDE, un conseiller business. À partir des chiffres fournis, donne des "
           "recommandations actionnables. Pour chacune : quoi faire, pourquoi, impact estimé, "
           "données utilisées. N'invente aucun chiffre."),
    "en": ("You are MIDE, a business advisor. Using the figures provided, give actionable "
           "recommendations. For each: what to do, why, estimated impact, data used. "
           "Never invent figures."),
}
_LABELS = {
    "fr": ("Chiffres", "Extraits", "Question", "Recommandations"),
    "en": ("Figures", "Excerpts", "Question", "Recommendations"),
}


def build_decision_prompt(question: str, findings: Sequence[Finding],
                          passages: Sequence[Passage] = (), language: str = "fr") -> str:
    """Prompt asking the LLM for recommendations grounded in the figures."""
    lang = language if language in _SYSTEM else "fr"
    figures, excerpts, q, answer = _LABELS[lang]
    facts = "\n".join(f"[{f.module}] {k}: {v}" for f in findings for k, v in f.facts.items())
    parts = [_SYSTEM[lang], f"{figures}:\n{facts or '-'}"]
    if passages:
        parts.append(f"{excerpts}:\n{format_passages(passages)}")
    parts.append(f"{q}: {question}\n{answer}:")
    return "\n\n".join(parts)


def recommend(question: str, findings: Sequence[Finding], llm: LLM,
              passages: Sequence[Passage] = (), language: str = "fr") -> Recommendation:
    """Ask the LLM for recommendations; the source figures are always attached."""
    prompt = build_decision_prompt(question, findings, passages, language)
    text = llm.generate(prompt, max_tokens=700, temperature=0.2).strip()
    return Recommendation(text, list(findings), list(passages))
