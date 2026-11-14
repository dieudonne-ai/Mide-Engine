"""Weekly report: KPIs, forecasts, alerts and 3 priority actions (Markdown/HTML)."""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from mide.agent.decision import BusinessData, Finding, run_modules

_ACTION_LIMIT = 3

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


def _actions(f: dict[str, Finding], fr: bool) -> list[Action]:
    """Rank candidate actions: churn, marketing budget, anomalies, sales trend."""
    out: list[Action] = []
    cust = f.get("customers")
    if cust and "churn" in cust.facts:
        out.append(Action(
            "Relancer les clients à risque de départ" if fr else "Re-engage customers at churn risk",
            f"churn: {cust.facts['churn']}"))
    mkt = f.get("marketing")
    if mkt:
        moves = [(k, v) for k, v in mkt.facts.items() if k.startswith("move ")]
        if moves:
            k, v = moves[0]
            out.append(Action(
                (f"Réallouer le budget depuis {k[5:]}" if fr else f"Reallocate budget from {k[5:]}"),
                f"{v}; best channel: {mkt.facts.get('best channel', '-')}"))
        elif "best channel" in mkt.facts:
            out.append(Action(
                "Renforcer le canal le plus rentable" if fr else "Invest more in the best channel",
                f"best channel: {mkt.facts['best channel']}"))
    ins = f.get("insights")
    if ins and "anomaly 1" in ins.facts:
        out.append(Action(
            "Analyser la cause de l'anomalie de ventes la plus récente" if fr
            else "Investigate the cause of the latest sales anomaly",
            ins.facts["anomaly 1"]))
    sal = f.get("sales")
    if sal and "trend" in sal.facts:
        out.append(Action(
            "Surveiller la tendance des ventes et ajuster les stocks" if fr
            else "Track the sales trend and adjust stock",
            f"trend: {sal.facts['trend']}"))
    return out[:_ACTION_LIMIT]


def build_report(data: BusinessData, language: str = "fr", today: date | None = None) -> Report:
    """Build the report from the business tables (missing tables are skipped)."""
    lang = language if language in _T else "fr"
    findings = _by_module(run_modules(["insights", "sales", "customers", "marketing"], data))
    report = Report(lang, today or datetime.now(UTC).date())
    if "insights" in findings:
        report.kpis = {k: v for k, v in findings["insights"].facts.items()
                       if not k.startswith("anomaly")}
        report.alerts = [v for k, v in findings["insights"].facts.items()
                         if k.startswith("anomaly")]
    if "sales" in findings:
        report.forecasts = {k: v for k, v in findings["sales"].facts.items()
                            if k.startswith("forecast")}
    if "customers" in findings and "churn" in findings["customers"].facts:
        report.alerts.append(f"churn: {findings['customers'].facts['churn']}")
    if "marketing" in findings and findings["marketing"].facts.get("underperforming", "none") != "none":
        report.alerts.append(
            f"marketing underperforming: {findings['marketing'].facts['underperforming']}")
    report.actions = _actions(findings, lang == "fr")
    return report


def render_markdown(report: Report) -> str:
    t = _T[report.language]
    lines = [f"# {t['title']}", "", f"_{t['generated']} {report.generated.isoformat()}_", ""]
    if report.empty:
        return "\n".join(lines + [t["nodata"], ""])
    lines += [f"## {t['kpis']}", ""] + [f"- **{k}**: {v}" for k, v in report.kpis.items()]
    lines += ["", f"## {t['forecast']}", ""] + [f"- **{k}**: {v}" for k, v in report.forecasts.items()]
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
            f"<h2>{e(t['kpis'])}</h2>", ul([f"<b>{e(k)}</b>: {e(v)}" for k, v in report.kpis.items()]),
            f"<h2>{e(t['forecast'])}</h2>",
            ul([f"<b>{e(k)}</b>: {e(v)}" for k, v in report.forecasts.items()]),
            f"<h2>{e(t['alerts'])}</h2>", ul([e(a) for a in report.alerts]),
            f"<h2>{e(t['actions'])}</h2>",
            ul([f"<b>{e(a.text)}</b> — {e(a.evidence)}" for a in report.actions], "ol"),
        ]
    return (f"<!doctype html><html lang=\"{report.language}\"><head><meta charset=\"utf-8\">"
            f"<title>{e(t['title'])}</title></head><body>{''.join(body)}</body></html>\n")
