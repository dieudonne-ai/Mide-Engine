from pathlib import Path

import pytest

from mide import dashboard_data as dd
from mide.llm.runtime import FakeLLM

APP = Path(__file__).resolve().parent.parent / "app" / "dashboard.py"


@pytest.fixture
def cfg_dir(tmp_path, monkeypatch, demo_data):
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "sources.yaml").write_text(
        f"sources:\n  - {demo_data['campaigns']}\n  - {demo_data['sales']}\n")
    return cfg


@pytest.fixture
def empty_cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    return cfg


def test_load_and_views(cfg_dir):
    data = dd.load_dashboard_data(cfg_dir)
    assert data.has_sales and data.has_campaigns
    report = dd.home_kpis(data)
    assert report.kpis.total_revenue > 0 and report.anomalies
    sv = dd.sales_view(data.tables.sales)
    assert set(sv["forecast"].totals) == {30, 60, 90}
    assert not dd.customers_view(data.tables.sales)["segments"].empty
    mv = dd.marketing_view(data.tables.campaigns)
    assert not mv["channels"].empty and mv["plan"].best_channel
    hv = dd.hardware_view(data.config)
    assert hv["hardware"].profile in ("tiny", "small", "medium", "large")


def test_no_sources(empty_cfg):
    data = dd.load_dashboard_data(empty_cfg)
    assert not data.has_sales and dd.home_kpis(data) is None


def test_config_dir_from_env(monkeypatch, tmp_path):
    monkeypatch.delenv(dd.CONFIG_ENV, raising=False)
    assert dd.config_dir_from_env() is None
    monkeypatch.setenv(dd.CONFIG_ENV, str(tmp_path))
    assert dd.config_dir_from_env() == tmp_path


def test_ask_answer_refactor(cfg_dir, monkeypatch):
    from mide import cli

    monkeypatch.setattr(cli, "_get_llm", lambda cfg: FakeLLM("Use Email."))
    answer, used, _ = cli.ask_answer("Quel canal marketing a le meilleur ROI ?", cfg_dir)
    assert answer == "Use Email." and "ROI" in used


def test_ui_command_without_streamlit(monkeypatch):
    import importlib.util

    from typer.testing import CliRunner

    from mide import cli

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    res = CliRunner().invoke(cli.app, ["ui"])
    assert res.exit_code == 1


def test_dashboard_pages_run_without_error(cfg_dir, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv(dd.CONFIG_ENV, str(cfg_dir))
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    assert not at.exception, at.exception
    for page in ("Sales", "Customers", "Marketing", "Data sources", "Hardware & models", "Home"):
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, (page, at.exception)


def test_dashboard_without_data(empty_cfg, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv(dd.CONFIG_ENV, str(empty_cfg))
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception and at.info
