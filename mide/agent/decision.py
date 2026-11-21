"""Turns business-module results into actionable, sourced recommendations."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import pandas as pd

from mide.business import customers, insights, marketing, sales
from mide.llm.prompts import format_passages
from mide.llm.runtime import LLM
from mide.rag.retriever import Passage
from mide.utils.french import french_dates, french_year_months


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


# Display labels of the fact keys. The keys stay English (stable for the LLM prompt,
# the dashboard and the report); only what the user reads is translated.
_FACT_LABELS = {
    "fr": {"revenue": "chiffre d'affaires", "orders": "commandes",
           "average order value": "panier moyen", "30d growth": "croissance sur 30 jours",
           "forecast": "prévision à {x} jours", "churn": "risque de départ",
           "underperforming": "canaux marketing sous-performants", "trend": "tendance",
           "top products": "meilleurs produits", "flop products": "produits les plus faibles",
           "best channel": "meilleur canal", "attribution check": "contrôle d'attribution",
           "segment": "segment {x}", "channel": "canal {x}", "move": "transfert depuis {x}",
           "anomaly": "anomalie {x}"},
    "en": {"revenue": "revenue", "orders": "orders", "average order value": "average order value",
           "30d growth": "30d growth", "forecast": "forecast {x}d", "churn": "churn",
           "underperforming": "marketing underperforming", "trend": "trend",
           "top products": "top products", "flop products": "flop products",
           "best channel": "best channel", "attribution check": "attribution check",
           "segment": "segment {x}", "channel": "channel {x}", "move": "move {x}",
           "anomaly": "anomaly {x}"},
}
_PARAM_KEY = re.compile(r"(forecast) (\d+)d|(segment|channel|move|anomaly) (.+)")


def fact_label(key: str, language: str) -> str:
    """Label of a fact key in the given language (unknown keys unchanged, French by default)."""
    labels = _FACT_LABELS.get(language, _FACT_LABELS["fr"])
    match = _PARAM_KEY.fullmatch(key)
    if match:
        prefix = match.group(1) or match.group(3)
        value = match.group(2) or match.group(4)
        if prefix == "segment":
            value = customers.segment_label(value, language)
        return labels[prefix].format(x=value)
    return labels.get(key, key)


_D = r"\d{4}-\d{2}-\d{2}"
# French wording of the English phrases the fact builders write into fact values.
# Facts stay English (LLM prompt, report parsing); only the displayed text is translated.
# Order matters: longer phrases first, so a short one never breaks a longer match.
_FR_VALUE_PHRASES: list[tuple[re.Pattern[str], str]] = [(re.compile(p), r) for p, r in [
    ((r"the same sale is likely counted by several channels, so compare ROI/ROAS between "
      r"channels rather than as absolute returns"),
     ("la même vente est probablement comptée par plusieurs canaux : comparez le ROI/ROAS "
      "entre canaux plutôt qu'en valeur absolue")),
    (r"channels report (\S+) revenue, (\S+)x total sales \((\S+?)\);",
     r"les canaux déclarent \1 de revenus, soit \2 fois le total des ventes (\3) ;"),
    (r"est\. extra revenue up to", "revenu supplémentaire estimé jusqu'à"),
    (r"\(linear, at (.+?) ROAS ", r"(linéaire, au ROAS \1 de "),
    (r"returns diminish", "rendements décroissants"),
    (rf"\b(drop|spike) on ({_D}) -> ({_D}):", r"\1 du \2 au \3 :"),
    (rf"\b(drop|spike) on ({_D}):", r"\1 le \2 :"),
    (r"\bdrop\b", "baisse"), (r"\bspike\b", "pic"),
    (r"(\S+) vs (\S+) expected \(", r"\1 au lieu de \2 attendus ("),
    (r"(\S+) expected \(", r"\1 attendus ("),
    (rf"\((\d+) days to ({_D}) vs previous (\d+)\)",
     r"(\1 jours jusqu'au \2, contre les \3 précédents)"),
    (rf"\bfrom ({_D}) to ({_D})", r"du \1 au \2"),
    (r"vs previous (\d+)d\b", r"par rapport aux \1 jours précédents"),
    (r"(\d{4}-\d{2}) vs (\d{4}-\d{2})", r"\1 contre \2"),
    (r"(\d) to (?=\S)", r"\1 vers "),
    (r"customers at high risk", "clients à risque élevé"),
    (r"\(top: ", "(principaux : "),
    (r", \+(\d+) more\)", r", +\1 autres)"),
    (r"past revenue at risk", "de chiffre d'affaires passé à risque"),
    (r"(\d+) of (\d+) customers", r"\1 clients sur \2"),
    (r"% of revenue", "% du chiffre d'affaires"),
    (r"\bcustomers\b", "clients"),
    (r"(\d) orders\)", r"\1 commandes)"),
    (r"\bspend (?=-?\d)", "dépenses "), (r"\brevenue (?=-?\d)", "revenus "),
    (r"^up\b", "hausse"), (r"^down\b", "baisse"), (r"^flat\b", "stable"),
    (r"\bYoY ", "sur un an "), (r"\blast 3 months ", "3 derniers mois "),
    (r"^none$", "aucun"), (r"\bn/a\b", "n.d."),
]]


_NBSP = "\u00a0"
_FR_THOUSANDS = re.compile(r"(?<![\d.])(?<!\d,)\d{1,3}(?:,\d{3})+(?!\d|,\d)")
_FR_DECIMAL = re.compile(r"(?<=\d)\.(?=\d)")
_FR_PERCENT = re.compile(r"(?<=\d)%")


def french_numbers(value: str) -> str:
    """French number format: '1,735' -> '1 735', '42.54' -> '42,54', '20.7%' -> '20,7 %'.

    Spaces are non-breaking so a number is never split across lines. Dates
    (2024-12-31) and identifiers (C0012) are left as they are."""
    value = _FR_THOUSANDS.sub(lambda m: m.group(0).replace(",", _NBSP), value)
    value = _FR_DECIMAL.sub(",", value)
    return _FR_PERCENT.sub(_NBSP + "%", value)


_FR_PUNCT = re.compile(r"[ \u00a0]?([;:])(?= |$)")


def french_punctuation(value: str) -> str:
    """French spacing: a non-breaking space before ':' and ';' ('a; b' -> 'a ; b').

    Only a sign followed by a space or the end is touched, so ratios, times and
    URLs ('a:b', '10:30', 'http://') stay as they are."""
    return _FR_PUNCT.sub(_NBSP + r"\1", value)


def fact_sep(language: str) -> str:
    """Separator between a label and its value: ': ' in English, ' : ' in French."""
    return ": " if language == "en" else _NBSP + ": "


def list_sep(language: str) -> str:
    """Separator between items of a fact: '; ' in English, ' ; ' in French."""
    return "; " if language == "en" else _NBSP + "; "


def fact_value(value: str, language: str) -> str:
    """Fact value as shown to the user: French phrasing, numbers and spacing unless English."""
    if language == "en":
        return value
    for pattern, replacement in _FR_VALUE_PHRASES:
        value = pattern.sub(replacement, value)
    return french_punctuation(french_numbers(french_year_months(french_dates(value))))


@dataclass
class Recommendation:
    """LLM text plus the deterministic figures used to produce it."""

    text: str
    findings: list[Finding]
    passages: list[Passage] = field(default_factory=list)

    def data_used(self, language: str = "fr") -> str:
        title = "Données utilisées" if language == "fr" else "Data used"
        lines = [f"- [{f.module}] {fact_label(k, language)}{fact_sep(language)}{fact_value(v, language)}"
                 for f in self.findings for k, v in f.facts.items()]
        return f"{title}{fact_sep(language).rstrip()}\n" + "\n".join(lines) if lines else ""


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
    """'P001 Rice 25kg (317,912 = 43.2% of revenue), ...' (id only when the name is unknown).

    Each product cites the revenue its share comes from (explainability)."""
    labels = (f"{p} {names[str(p)]}" if names.get(str(p)) else str(p) for p in table.index)
    return ", ".join(f"{label} ({_money(revenue)} = {share:.1f}% of revenue)"
                     for label, revenue, share in zip(labels, table["revenue"], table["share_pct"]))


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
    period = f"from {days[0]:%Y-%m-%d} to {days[-1]:%Y-%m-%d}"
    growth = _pct(forecast.growth_pct[horizon])
    return f"{_money(forecast.totals[horizon])} {period} ({growth} vs previous {horizon}d)"


def _sales_finding(df: pd.DataFrame, products: pd.DataFrame | None = None) -> Finding:
    forecast = sales.forecast_sales(df)
    trend = sales.sales_trend(df)
    ranking = sales.product_ranking(df, n=2) if "product_id" in df.columns else None
    facts = {f"forecast {h}d": _forecast_text(forecast, h) for h in forecast.totals}
    facts["trend"] = _trend_text(trend)
    if ranking is not None:
        names = sales.product_names(products) if products is not None else {}
        facts["top products"] = _product_list(ranking["top"], names)
        if not ranking["flop"].empty:
            facts["flop products"] = _product_list(ranking["flop"], names)
    return Finding("sales", facts)


_MAX_CHURN_NAMED = 3


def _churn_scale(churn: customers.ChurnReport) -> str:
    """' (0.3% of revenue; 4 of 350 customers)': how big the risk is against the whole base."""
    total = float(churn.scores["monetary"].sum())
    if churn.scores.empty or total <= 0:
        return ""
    share = 100 * churn.revenue_at_risk / total
    return f" ({share:.1f}% of revenue; {len(churn.high_risk)} of {len(churn.scores)} customers)"


def _customers_finding(df: pd.DataFrame) -> Finding:
    summary = customers.segment_summary(customers.rfm_segments(df))
    churn = customers.churn_risk(df)
    # RFM has at most six segments: list them all, so "At risk" is never hidden.
    facts = {f"segment {seg}": f"{int(r.customers)} customers, {r.revenue_share_pct}% of revenue"
             for seg, r in summary.iterrows()}
    # Name the most valuable at-risk customers so the action says whom to contact.
    # Hiding a single name saves nothing, so it is shown; beyond that, say how many are left out.
    limit = _MAX_CHURN_NAMED + 1 if len(churn.high_risk) <= _MAX_CHURN_NAMED + 1 \
        else _MAX_CHURN_NAMED
    top = churn.high_risk[:limit]
    named = ""
    if top:
        hidden = len(churn.high_risk) - len(top)
        more = f", +{hidden} more" if hidden else ""
        named = f" (top: {', '.join(map(str, top))}{more})"
    facts["churn"] = (f"{len(churn.high_risk)} customers at high risk{named}, "
                      f"{_money(churn.revenue_at_risk)} past revenue at risk"
                      f"{_churn_scale(churn)}")
    return Finding("customers", facts)


def _attribution_check(channels: pd.DataFrame, sales_df: pd.DataFrame | None) -> str | None:
    """Warn when channels claim more revenue than total sales (double-counted attribution)."""
    if sales_df is None or "amount" not in sales_df.columns:
        return None
    total_sales = float(pd.to_numeric(sales_df["amount"], errors="coerce").sum())
    attributed = float(channels["revenue"].sum())
    if total_sales <= 0 or attributed <= total_sales:
        return None
    return (f"channels report {_money(attributed)} revenue, {attributed / total_sales:.2f}x "
            f"total sales ({_money(total_sales)}); the same sale is likely counted by several "
            "channels, so compare ROI/ROAS between channels rather than as absolute returns")


def _marketing_finding(df: pd.DataFrame, sales_df: pd.DataFrame | None = None) -> Finding:
    channels = marketing.channel_performance(df)
    plan = marketing.suggest_reallocation(channels)
    # Cite the totals behind each ratio, so "ROI 41.54" cannot be read as 41.54%.
    # Ratios first, totals in parentheses: one colon per line ("channel X: ROI ..."), not two.
    facts = {f"channel {c}": (f"ROI {_ratio(r.roi)}, ROAS {_ratio(r.roas)} "
                              f"(spend {_money(r.spend)}, revenue {_money(r.revenue)})")
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
    check = _attribution_check(channels, sales_df)
    if check:
        facts["attribution check"] = check
    return Finding("marketing", facts)


_MAX_ANOMALIES = 5


def _insights_finding(df: pd.DataFrame) -> Finding:
    report = insights.analyze(df)
    k = report.kpis
    period = f"from {k.start.date()} to {k.end.date()}"
    growth = ("n/a" if k.growth_30d is None
              else f"{k.growth_30d:+.1%} (30 days to {k.end.date()} vs previous 30)")
    facts = {
        "revenue": f"{_money(k.total_revenue)} {period}", "orders": f"{k.orders:,}",
        "average order value": (f"{_money(k.avg_order_value)} "
                                f"({_money(k.total_revenue)} / {k.orders:,} orders)"),
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
    "marketing": ("campaigns", lambda df, data: _marketing_finding(df, data.sales)),
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


def _prompt_key(key: str, language: str) -> str:
    """Fact key as sent to the LLM: RFM segment names in the answer language.

    Other keys stay as they are; translating the segment name keeps a French answer
    from quoting "At risk" or "Hibernating" in English.
    """
    if key.startswith("segment "):
        return "segment " + customers.segment_label(key[len("segment "):], language)
    return key


def build_decision_prompt(question: str, findings: Sequence[Finding],
                          passages: Sequence[Passage] = (), language: str = "fr") -> str:
    """Prompt asking the LLM for recommendations grounded in the figures."""
    lang = language if language in _SYSTEM else "fr"
    figures, excerpts, q, answer = _LABELS[lang]
    facts = "\n".join(f"[{f.module}] {_prompt_key(k, lang)}: {v}"
                      for f in findings for k, v in f.facts.items())
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
