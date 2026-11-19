import pytest
from typer.testing import CliRunner

from mide import cli
from mide.agent.decision import BusinessData, detect_tables
from mide.report import build_report, render_html, render_markdown


@pytest.fixture
def tables(demo_data):
    import pandas as pd

    return detect_tables({"s": pd.read_csv(demo_data["sales"]),
                          "c": pd.read_csv(demo_data["campaigns"])})


def test_report_sections(tables):
    r = build_report(tables, "en")
    assert r.kpis and r.forecasts and r.alerts
    assert 1 <= len(r.actions) <= 3 and all(a.evidence for a in r.actions)
    md = render_markdown(r)
    for h in ("Key indicators", "Forecasts", "Alerts", "Priority actions"):
        assert h in md


def test_anomaly_action_cites_most_recent_anomaly(demo_data):
    import pandas as pd

    from mide.agent.decision import run_modules

    # Sales cut at 2024-10-01: the 2024-09-03 -> 09-04 drop is within the 90-day window.
    sales = pd.read_csv(demo_data["sales"])
    data = detect_tables({"s": sales[sales["date"] <= "2024-10-01"]})
    facts = run_modules(["insights"], data)[0].facts
    anomalies = [v for k, v in facts.items() if k.startswith("anomaly ")]
    assert len(anomalies) >= 2 and anomalies[-1].startswith("drop on 2024-09-03")
    action = next(a for a in build_report(data, "en").actions
                  if "latest sales anomaly" in a.text)
    assert action.evidence == anomalies[-1]


def test_no_anomaly_action_when_all_anomalies_are_old(tables):
    # Demo sales end 2024-12-31 and every anomaly ends before 2024-10-02.
    actions = build_report(tables, "en").actions
    assert not any("anomaly" in a.text for a in actions)
    assert any(a.text == "Track the sales trend and adjust stock" for a in actions)
    fr = build_report(tables, "fr").actions
    assert not any("anomalie" in a.text for a in fr)


def test_actions_anomaly_window():
    from datetime import date

    from mide.agent.decision import Finding
    from mide.report import _actions

    ins = {"insights": Finding("insights", {
        "anomaly 1": "drop on 2024-06-01: 1 vs 9 expected (-89%)",
        "anomaly 2": "spike on 2024-09-28 -> 2024-10-03: 9 vs 1 expected (+800%)"})}
    [act] = _actions(ins, fr=False, last_day=date(2024, 12, 31))
    assert act.evidence.startswith("spike on 2024-09-28")  # a run counts by its last day
    assert _actions(ins, fr=False, last_day=date(2025, 3, 1)) == []
    assert _actions(ins, fr=False)[0].evidence.startswith("spike")  # no sales date: no filter


def test_recent_anomaly_alerts_keeps_recent_and_counts_older():
    from datetime import date

    from mide.report import recent_anomaly_alerts

    items = ["drop on 2024-06-01: 1 vs 9 expected (-89%)",
             "spike on 2024-09-28 -> 2024-10-03: 9 vs 1 expected (+800%)",
             "drop on 2024-12-20: 1 vs 9 expected (-89%)"]
    last = date(2024, 12, 31)  # cutoff = 2024-10-02; a run counts by its last day
    assert recent_anomaly_alerts(items, last, fr=False) == [
        items[1], items[2], "1 older anomaly (before 2024-10-02) not listed"]
    assert recent_anomaly_alerts(items[:1] * 2, last, fr=True) == [
        "2 anomalie(s) plus ancienne(s) (avant le 2024-10-02) non listée(s)"]
    assert recent_anomaly_alerts(items, None, fr=False) == items
    assert recent_anomaly_alerts(["odd text"], last, fr=False) == ["odd text"]


def test_report_alerts_skip_old_demo_anomalies(tables):
    # Demo sales end 2024-12-31; the 4 anomalies all end before 2024-10-02.
    alerts = build_report(tables, "en").alerts
    assert not any(a.startswith(("drop on", "spike on")) for a in alerts)
    assert "4 older anomalies (before 2024-10-02) not listed" in alerts


def test_report_french_and_html(tables):
    r = build_report(tables, "fr")
    assert "Actions prioritaires" in render_markdown(r)
    page = render_html(r)
    assert page.startswith("<!doctype html>") and "<ol>" in page


def test_report_labels_follow_language(tables):
    from mide.report import fact_label

    fr = render_markdown(build_report(tables, "fr"))
    for label in ("**chiffre d'affaires**:", "**commandes**:", "**panier moyen**:",
                  "**croissance sur 30 jours**:", "**prévision à 30 jours**:",
                  "- risque de départ: ", "- canaux marketing sous-performants: Radio, SMS"):
        assert label in fr, label
    assert "**revenue**" not in fr and "- churn:" not in fr and "marketing underperforming" not in fr
    en = render_markdown(build_report(tables, "en"))
    for label in ("**revenue**:", "**average order value**:", "**forecast 90d**:", "- churn: ",
                  "- marketing underperforming: Radio, SMS"):
        assert label in en, label
    assert "<b>prévision à 60 jours</b>" in render_html(build_report(tables, "fr"))
    assert fact_label("unknown key", "fr") == "unknown key"
    assert fact_label("forecast 7d", "xx") == "prévision à 7 jours"


def test_html_escapes():
    from mide.report import Action, Report

    r = Report("en", __import__("datetime").date(2026, 1, 1), kpis={"<b>": "<script>"},
               actions=[Action("x", "y")])
    assert "<script>" not in render_html(r)


def test_empty_data():
    r = build_report(BusinessData(), "en")
    assert r.empty and not r.alerts and "No usable" in render_markdown(r)


def test_cli_report(tmp_path, monkeypatch, demo_data):
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "sources.yaml").write_text(
        f"sources:\n  - {demo_data['campaigns']}\n  - {demo_data['sales']}\n")
    out = tmp_path / "r.html"
    res = CliRunner().invoke(cli.app, ["report", "--format", "html", "-o", str(out),
                                       "--config-dir", str(cfg)])
    assert res.exit_code == 0 and "<h1>" in out.read_text()
    res = CliRunner().invoke(cli.app, ["report", "--config-dir", str(cfg)])
    assert res.exit_code == 0 and "#" in res.output
    assert CliRunner().invoke(cli.app, ["report", "--format", "pdf"]).exit_code == 2


def _sales(last: str):
    import pandas as pd

    return BusinessData(sales=pd.DataFrame(
        {"date": ["2024-01-01", last, "not a date"], "amount": [1.0, 2.0, 3.0]}))


def test_stale_data_alert():
    from datetime import date

    from mide.report import stale_data_alert

    data = _sales("2024-12-31")
    en = stale_data_alert(data, date(2025, 3, 1), fr=False)
    assert en == ("stale data: last sale on 2024-12-31, 60 days before this report; "
                  "figures describe that period, not today")
    assert "dernière vente le 2024-12-31, 60 jours" in stale_data_alert(data, date(2025, 3, 1), True)
    assert stale_data_alert(data, date(2025, 1, 30), fr=False) is None  # 30 days: still fresh
    assert stale_data_alert(BusinessData(), date(2025, 3, 1), fr=False) is None


def test_report_flags_stale_data_first(tables):
    from datetime import date

    r = build_report(tables, "en", today=date(2026, 11, 19))
    assert r.alerts[0].startswith("stale data: last sale on 2024-12-31,")
    fresh = build_report(tables, "en", today=date(2025, 1, 2))
    assert not any(a.startswith("stale data") for a in fresh.alerts)



def test_budget_action_carries_attribution_check(tables):
    # Demo channels claim ~1.96x total sales: the ROAS-based action must say so.
    action = next(a for a in build_report(tables, "en").actions
                  if a.text.startswith("Reallocate budget from"))
    assert action.text == "Reallocate budget from Radio, SMS"
    assert action.evidence == (
        "Radio: 6,840 to Email, est. extra revenue up to 285,353 (linear, at Email ROAS 42.54; "
        "returns diminish); SMS: 6,396 to Email, est. extra revenue up to 269,460 (linear, at "
        "Email ROAS 42.54; returns diminish); best channel: Email; attribution check: channels report "
        "1,443,825 revenue, 1.96x total sales 735,907; the same sale is likely counted by "
        "several channels, so compare ROI/ROAS between channels rather than as absolute returns")


def test_budget_action_without_attribution_issue():
    from mide.agent.decision import Finding
    from mide.report import _actions

    mkt = {"marketing": Finding("marketing", {"best channel": "Email"})}
    assert _actions(mkt, fr=False)[0].evidence == "best channel: Email"
    mkt["marketing"].facts["attribution check"] = "channels report 2x total sales"
    assert _actions(mkt, fr=False)[0].evidence == (
        "best channel: Email; attribution check: channels report 2x total sales")


def test_trend_action_cites_30d_forecast(tables):
    # Demo trend is "up" while the 30d forecast is lower: stock advice must show both.
    action = next(a for a in build_report(tables, "en").actions
                  if a.text == "Track the sales trend and adjust stock")
    assert action.evidence == (
        "trend: up, YoY +20.7% (2024-01 -> 2024-12 vs 2023-01 -> 2023-12), last 3 months "
        "+70.7% (2024-10 -> 2024-12 vs 2024-07 -> 2024-09); forecast 30d: 45,871 for "
        "2025-01-01 -> 2025-01-30 (-9.3% vs previous 30d)")


def test_trend_action_without_forecast():
    from mide.agent.decision import Finding
    from mide.report import _actions

    sal = {"sales": Finding("sales", {"trend": "up"})}
    assert _actions(sal, fr=False)[0].evidence == "trend: up"
    sal["sales"].facts["forecast 30d"] = "100 (-5% vs previous 30d)"
    assert _actions(sal, fr=False)[0].evidence == (
        "trend: up; forecast 30d: 100 (-5% vs previous 30d)")


def test_budget_action_single_move_keeps_short_text():
    from mide.agent.decision import Finding
    from mide.report import _actions

    mkt = {"marketing": Finding("marketing", {"move Radio": "500 to Email", "best channel": "Email"})}
    action = _actions(mkt, fr=True)[0]
    assert action.text == "Réallouer le budget depuis Radio"
    assert action.evidence == "500 to Email; meilleur canal: Email"


def test_action_evidence_labels_follow_language():
    from mide.agent.decision import Finding
    from mide.report import _actions

    f = {"customers": Finding("customers", {"churn": "4 customers"}),
         "marketing": Finding("marketing", {"move Radio": "500 to Email", "best channel": "Email",
                                            "attribution check": "2x"}),
         "sales": Finding("sales", {"trend": "up", "forecast 30d": "100"})}
    fr = [a.evidence for a in _actions(f, fr=True)]
    assert fr == ["risque de départ: 4 customers",
                  "500 to Email; meilleur canal: Email; contrôle d'attribution: 2x",
                  "tendance: up; prévision à 30 jours: 100"]
    en = [a.evidence for a in _actions(f, fr=False)]
    assert en == ["churn: 4 customers",
                  "500 to Email; best channel: Email; attribution check: 2x",
                  "trend: up; forecast 30d: 100"]
    only_best = {"marketing": Finding("marketing", {"best channel": "Email"})}
    assert _actions(only_best, fr=True)[0].evidence == "meilleur canal: Email"


@pytest.mark.parametrize("language", ["fr", "en"])
def test_cli_report_never_overwrites_source_file(tmp_path, monkeypatch, demo_data, language):
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "default.yaml").write_text(f"language: {language}\n")
    folder = tmp_path / "data"
    folder.mkdir()
    sales = folder / "sales.csv"
    sales.write_bytes(demo_data["sales"].read_bytes())
    (cfg / "sources.yaml").write_text(f"sources:\n  - {folder}\n  - {demo_data['campaigns']}\n")
    before_sales = sales.read_bytes()
    before_campaigns = demo_data["campaigns"].read_bytes()
    for target in (sales, demo_data["campaigns"]):
        res = CliRunner().invoke(cli.app, ["report", "-o", str(target), "--config-dir", str(cfg)])
        assert res.exit_code == 1
        word = "source autorisée" if language == "fr" else "authorized source"
        assert word in res.output
    assert sales.read_bytes() == before_sales
    assert demo_data["campaigns"].read_bytes() == before_campaigns
    # A new file, even inside a source folder, is still allowed.
    new = folder / "report.md"
    res = CliRunner().invoke(cli.app, ["report", "-o", str(new), "--config-dir", str(cfg)])
    assert res.exit_code == 0 and new.read_text(encoding="utf-8").startswith("#")


def test_source_owning(tmp_path):
    from mide.connectors.sources import source_owning

    folder = tmp_path / "data"
    folder.mkdir()
    f = folder / "a.csv"
    f.write_text("x\n1\n")
    other = tmp_path / "other.csv"
    other.write_text("x\n")
    sources = ["sqlite:///db.sqlite", str(folder)]
    assert source_owning(f, sources) == str(folder)
    assert source_owning(folder, sources) == str(folder)
    assert source_owning(other, sources) is None
    assert source_owning(folder / "missing.md", sources) is None
    assert source_owning(other, [str(other)]) == str(other)
