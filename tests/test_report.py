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
    assert r.empty and "No usable" in render_markdown(r)


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
