"""Turns business-module results into actionable, sourced recommendations."""

from __future__ import annotations

from collections.abc import Sequence
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
    """Tables the business modules work on (either may be missing)."""

    sales: pd.DataFrame | None = None
    campaigns: pd.DataFrame | None = None


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


def detect_tables(frames: dict[str, pd.DataFrame]) -> BusinessData:
    """Pick the sales and campaigns tables among datasets by their columns."""
    data = BusinessData()
    for df in frames.values():
        cols = set(df.columns)
        if data.sales is None and _SALES_COLS <= cols and "customer_id" in cols:
            data.sales = df
        elif data.campaigns is None and _CAMPAIGN_COLS <= cols:
            data.campaigns = df
    return data


def _money(x: float) -> str:
    return f"{x:,.0f}"


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:+.1f}%"


def _sales_finding(df: pd.DataFrame) -> Finding:
    forecast = sales.forecast_sales(df)
    trend = sales.sales_trend(df)
    ranking = sales.product_ranking(df, n=2) if "product_id" in df.columns else None
    facts = {f"forecast {h}d": f"{_money(t)} ({_pct(forecast.growth_pct[h])} vs previous {h}d)"
             for h, t in forecast.totals.items()}
    facts["trend"] = f"{trend.direction}, last 3 months {_pct(trend.last_3m_growth_pct)}"
    if ranking is not None:
        facts["top products"] = ", ".join(
            f"{p} ({r.share_pct:.1f}%)" for p, r in ranking["top"].iterrows())
        facts["flop products"] = ", ".join(
            f"{p} ({r.share_pct:.1f}%)" for p, r in ranking["flop"].iterrows())
    return Finding("sales", facts)


def _customers_finding(df: pd.DataFrame) -> Finding:
    summary = customers.segment_summary(customers.rfm_segments(df))
    churn = customers.churn_risk(df)
    facts = {f"segment {seg}": f"{int(r.customers)} customers, {r.revenue_share_pct}% of revenue"
             for seg, r in summary.head(3).iterrows()}
    facts["churn"] = (f"{len(churn.high_risk)} customers at high risk, "
                      f"{_money(churn.revenue_at_risk)} past revenue at risk")
    return Finding("customers", facts)


def _marketing_finding(df: pd.DataFrame) -> Finding:
    channels = marketing.channel_performance(df)
    plan = marketing.suggest_reallocation(channels)
    facts = {f"channel {c}": f"ROI {r.roi:.2f}, ROAS {r.roas:.2f}" for c, r in channels.iterrows()}
    facts["underperforming"] = ", ".join(plan.underperforming) or "none"
    facts["best channel"] = plan.best_channel
    for m in plan.moves:
        facts[f"move {m.from_channel}"] = (f"{_money(m.amount)} to {m.to_channel}, est. extra "
                                           f"revenue {_money(m.estimated_extra_revenue)}")
    return Finding("marketing", facts)


def _insights_finding(df: pd.DataFrame) -> Finding:
    report = insights.analyze(df)
    k = report.kpis
    facts = {
        "revenue": _money(k.total_revenue), "orders": str(k.orders),
        "average order value": _money(k.avg_order_value),
        "30d growth": "n/a" if k.growth_30d is None else f"{k.growth_30d:+.1%}",
    }
    for i, a in enumerate(report.anomalies[:5], start=1):
        facts[f"anomaly {i}"] = a.describe()
    return Finding("insights", facts)


_BUILDERS = {
    "sales": ("sales", _sales_finding), "customers": ("sales", _customers_finding),
    "insights": ("sales", _insights_finding), "marketing": ("campaigns", _marketing_finding),
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
            findings.append(builder(table))
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
