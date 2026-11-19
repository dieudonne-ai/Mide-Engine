"""Weekly report: KPIs, forecasts, alerts and 3 priority actions (Markdown/HTML)."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

import pandas as pd

from mide.agent.decision import BusinessData, Finding, fact_label, run_modules

_ACTION_LIMIT = 3
STALE_AFTER_DAYS = 30  # older sales data gets a warning at the top of the alerts
RECENT_ANOMALY_DAYS = 90  # anomalies ending earlier than this before the last sale are summarized
_ANOMALY_END = re.compile(r" on (\d{4}-\d{2}-\d{2})(?: -> (\d{4}-\d{2}-\d{2}))?:")

_T = {
    "fr": {"title": "Rapport hebdomadaire MIDE", "kpis": "Indicateurs clés", "forecast": "Prévisions",
           "alerts": "Alertes", "actions": "Actions prioritaires", "none": "Aucune",
           "nodata": "Aucune donnée de ventes ou de marketing exploitable.",
           "generated": "Généré le"},
    "en": {"title": "MIDE weekly report", "kpis": "Key indicators", "forecast": "Forecasts",
           "alerts": "Alerts", "actions": "Priority actions", "none": "None",
           "nodata": "No usable sales or marketing data.",
           "generated": "Generated on"},
}

# Display labels of the business fact keys; the keys stay English for the agent facts.
@dataclass
class Action:
    """A prioritized recommendation with the figures that justify it."""

    text: str
    evidence: str


@dataclass
class Report:
    """Sections of the weekly report (all derived from the data, no LLM)."""

    language: str
    generated: date
    kpis: dict[str, str] = field(default_factory=dict)
    forecasts: dict[str, str] = field(default_factory=dict)
    alerts: list[str] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not (self.kpis or self.forecasts or self.alerts or self.actions)


def _by_module(findings: list[Finding]) -> dict[str, Finding]:
    return {f.module: f for f in findings}


def _actions(f: dict[str, Finding], fr: bool, last_day: date | None = None) -> list[Action]:
    """Rank candidate actions: churn, marketing budget, anomalies, sales trend.

    The anomaly action is only proposed for an anomaly in the recent window (see
    recent_anomaly_alerts), so it never asks to investigate an event the alerts left out.
    """
    out: list[Action] = []
    cust = f.get("customers")
    if cust and "churn" in cust.facts:
        out.append(Action(
            "Relancer les clients à risque de départ" if fr else "Re-engage customers at churn risk",
            f"churn: {cust.facts['churn']}"))
    mkt = f.get("marketing")
    if mkt:
        # The budget action rests on ROAS: carry the attribution caveat with it.
        check = mkt.facts.get("attribution check")
        caveat = f"; attribution check: {check}" if check else ""
        moves = [(k, v) for k, v in mkt.facts.items() if k.startswith("move ")]
        if moves:
            # Cite every suggested move: the alerts list all underperforming channels,
            # so the action must not silently drop all but the first one.
            sources = ", ".join(k[5:] for k, _ in moves)
            detail = moves[0][1] if len(moves) == 1 else "; ".join(f"{k[5:]}: {v}" for k, v in moves)
            out.append(Action(
                (f"Réallouer le budget depuis {sources}" if fr
                 else f"Reallocate budget from {sources}"),
                f"{detail}; best channel: {mkt.facts.get('best channel', '-')}{caveat}"))
        elif "best channel" in mkt.facts:
            out.append(Action(
                "Renforcer le canal le plus rentable" if fr else "Invest more in the best channel",
                f"best channel: {mkt.facts['best channel']}{caveat}"))
    ins = f.get("insights")
    anomalies = [v for k, v in ins.facts.items() if k.startswith("anomaly ")] if ins else []
    anomalies = [a for a in anomalies if _is_recent(a, last_day)]
    if anomalies:  # chronological order: the last one is the most recent
        out.append(Action(
            "Analyser la cause de l'anomalie de ventes la plus récente" if fr
            else "Investigate the cause of the latest sales anomaly",
            anomalies[-1]))
    sal = f.get("sales")
    if sal and "trend" in sal.facts:
        # Stock is bought for the coming weeks: cite the 30d forecast next to the past trend,
        # since a rising trend can come with a lower forecast (e.g. after a seasonal peak).
        forecast = sal.facts.get("forecast 30d")
        outlook = f"; forecast 30d: {forecast}" if forecast else ""
        out.append(Action(
            "Surveiller la tendance des ventes et ajuster les stocks" if fr
            else "Track the sales trend and adjust stock",
            f"trend: {sal.facts['trend']}{outlook}"))
    return out[:_ACTION_LIMIT]


def _last_sale_day(data: BusinessData) -> date | None:
    """Latest valid date in the sales table, or None if there is none."""
    if data.sales is None or "date" not in data.sales.columns:
        return None
    last = pd.to_datetime(data.sales["date"], errors="coerce").max()
    return None if pd.isna(last) else last.date()


def stale_data_alert(data: BusinessData, today: date, fr: bool) -> str | None:
    """Warn when the latest sale is more than STALE_AFTER_DAYS before the report date."""
    last = _last_sale_day(data)
    if last is None:
        return None
    age = (today - last).days
    if age <= STALE_AFTER_DAYS:
        return None
    if fr:
        return (f"données anciennes : dernière vente le {last.isoformat()}, {age} jours avant ce "
                "rapport ; les chiffres décrivent cette période, pas aujourd'hui")
    return (f"stale data: last sale on {last.isoformat()}, {age} days before this report; "
            "figures describe that period, not today")


def _anomaly_end(text: str) -> date | None:
    """Last day of an anomaly from its description ("drop on A -> B: ..."), or None."""
    m = _ANOMALY_END.search(text)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(2) or m.group(1))
    except ValueError:
        return None


def _recent_cutoff(last_day: date) -> date:
    return date.fromordinal(last_day.toordinal() - RECENT_ANOMALY_DAYS)


def _is_recent(anomaly: str, last_day: date | None) -> bool:
    """True if the anomaly ends within RECENT_ANOMALY_DAYS of last_day (or cannot be dated)."""
    if last_day is None:
        return True
    end = _anomaly_end(anomaly)
    return end is None or end >= _recent_cutoff(last_day)


def recent_anomaly_alerts(anomalies: list[str], last_day: date | None, fr: bool) -> list[str]:
    """Keep anomalies that end within RECENT_ANOMALY_DAYS of the last sale; count the others.

    The cutoff is relative to the last data day, not the report date: the stale-data alert
    already says when the data is old, and every anomaly would be "old" otherwise.
    """
    if last_day is None:
        return anomalies
    cutoff = _recent_cutoff(last_day)
    recent = [a for a in anomalies if _is_recent(a, last_day)]
    older = len(anomalies) - len(recent)
    if older:
        recent.append(
            f"{older} anomalie(s) plus ancienne(s) (avant le {cutoff.isoformat()}) non listée(s)"
            if fr else f"{older} older anomal{'y' if older == 1 else 'ies'} "
            f"(before {cutoff.isoformat()}) not listed")
    return recent


def build_report(data: BusinessData, language: str = "fr", today: date | None = None) -> Report:
    """Build the report from the business tables (missing tables are skipped)."""
    lang = language if language in _T else "fr"
    findings = _by_module(run_modules(["insights", "sales", "customers", "marketing"], data))
    report = Report(lang, today or datetime.now(UTC).date())
    if "insights" in findings:
        report.kpis = {k: v for k, v in findings["insights"].facts.items()
                       if not k.startswith("anomaly")}
        report.alerts = recent_anomaly_alerts(
            [v for k, v in findings["insights"].facts.items() if k.startswith("anomaly")],
            _last_sale_day(data), lang == "fr")
    if "sales" in findings:
        report.forecasts = {k: v for k, v in findings["sales"].facts.items()
                            if k.startswith("forecast")}
    if "customers" in findings and "churn" in findings["customers"].facts:
        report.alerts.append(
            f"{fact_label('churn', lang)}: {findings['customers'].facts['churn']}")
    if "marketing" in findings and findings["marketing"].facts.get("underperforming", "none") != "none":
        report.alerts.append(
            f"{fact_label('underperforming', lang)}: "
            f"{findings['marketing'].facts['underperforming']}")
    report.actions = _actions(findings, lang == "fr", _last_sale_day(data))
    stale = stale_data_alert(data, report.generated, lang == "fr")
    if stale and not report.empty:
        report.alerts.insert(0, stale)
    return report


def render_markdown(report: Report) -> str:
    t = _T[report.language]
    lines = [f"# {t['title']}", "", f"_{t['generated']} {report.generated.isoformat()}_", ""]
    if report.empty:
        return "\n".join(lines + [t["nodata"], ""])
    def items(facts: dict[str, str]) -> list[str]:
        return [f"- **{fact_label(k, report.language)}**: {v}" for k, v in facts.items()]

    lines += [f"## {t['kpis']}", ""] + items(report.kpis)
    lines += ["", f"## {t['forecast']}", ""] + items(report.forecasts)
    lines += ["", f"## {t['alerts']}", ""] + ([f"- {a}" for a in report.alerts] or [t["none"]])
    lines += ["", f"## {t['actions']}", ""]
    for i, a in enumerate(report.actions, start=1):
        lines.append(f"{i}. **{a.text}** — {a.evidence}")
    return "\n".join(lines) + "\n"


def render_html(report: Report) -> str:
    t = _T[report.language]
    e = html.escape

    def ul(items: list[str], tag: str = "ul") -> str:
        body = "".join(f"<li>{i}</li>" for i in items) or f"<li>{e(t['none'])}</li>"
        return f"<{tag}>{body}</{tag}>"

    body = [f"<h1>{e(t['title'])}</h1>", f"<p><em>{e(t['generated'])} {report.generated}</em></p>"]
    if report.empty:
        body.append(f"<p>{e(t['nodata'])}</p>")
    else:
        body += [
            f"<h2>{e(t['kpis'])}</h2>", ul([f"<b>{e(fact_label(k, report.language))}</b>: {e(v)}"
                                         for k, v in report.kpis.items()]),
            f"<h2>{e(t['forecast'])}</h2>",
            ul([f"<b>{e(fact_label(k, report.language))}</b>: {e(v)}"
                for k, v in report.forecasts.items()]),
            f"<h2>{e(t['alerts'])}</h2>", ul([e(a) for a in report.alerts]),
            f"<h2>{e(t['actions'])}</h2>",
            ul([f"<b>{e(a.text)}</b> — {e(a.evidence)}" for a in report.actions], "ol"),
        ]
    return (f"<!doctype html><html lang=\"{report.language}\"><head><meta charset=\"utf-8\">"
            f"<title>{e(t['title'])}</title></head><body>{''.join(body)}</body></html>\n")
