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


def test_anomaly_action_cites_most_recent_alert(tables):
    r = build_report(tables, "en")
    anomalies = [a for a in r.alerts if a.startswith(("drop on", "spike on"))]
    assert len(anomalies) >= 2
    action = next(a for a in r.actions if "latest sales anomaly" in a.text)
    assert action.evidence == anomalies[-1]


def test_report_french_and_html(tables):
    r = build_report(tables, "fr")
    assert "Actions prioritaires" in render_markdown(r)
    page = render_html(r)
    assert page.startswith("<!doctype html>") and "<ol>" in page


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

