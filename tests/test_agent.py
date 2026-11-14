import pandas as pd
import pytest

from mide.agent.decision import (
    BusinessData,
    build_decision_prompt,
    detect_tables,
    recommend,
    run_modules,
)
from mide.agent.router import route_question
from mide.llm.runtime import FakeLLM


@pytest.fixture
def data(demo_data):
    frames = {k: pd.read_csv(demo_data[k]) for k in ("sales", "campaigns", "products")}
    return detect_tables(frames)


@pytest.mark.parametrize("question, kind, module", [
    ("Quelles sont les prévisions de ventes ?", "business", "sales"),
    ("Which customers are at risk of churn?", "business", "customers"),
    ("Quel canal marketing a le meilleur ROI ?", "business", "marketing"),
    ("Y a-t-il des anomalies dans les ventes ?", "business", "insights"),
    ("Que dit la note de réunion sur le recrutement ?", "rag", None),
    ("What is our return policy?", "rag", None),
    ("Selon le rapport, pourquoi les ventes ont-elles chuté ?", "both", "sales"),
])
def test_routing(question, kind, module):
    route = route_question(question)
    assert route.kind == kind
    if module:
        assert module in route.modules


def test_detect_tables(data):
    assert "customer_id" in data.sales.columns and "spend" in data.campaigns.columns


def test_run_modules_has_figures(data):
    findings = run_modules(["sales", "customers", "marketing", "insights"], data)
    assert [f.module for f in findings] == ["sales", "customers", "marketing", "insights"]
    assert all(f.facts for f in findings)
    assert "forecast 30d" in findings[0].facts


def test_missing_table_skipped():
    assert run_modules(["marketing", "sales"], BusinessData()) == []


def test_recommendation_contains_source_figures(data):
    findings = run_modules(["marketing"], data)
    llm = FakeLLM("Reallocate budget.")
    rec = recommend("Où réallouer le budget ?", findings, llm)
    assert rec.text == "Reallocate budget."
    used = rec.data_used("fr")
    assert used.startswith("Données utilisées")
    assert "ROI" in used and "[marketing]" in used
    assert "ROI" in build_decision_prompt("q", findings, language="en")


def test_ask_uses_agent_for_business_question(tmp_path, monkeypatch, demo_data):
    from typer.testing import CliRunner

    from mide import cli

    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    llm = FakeLLM("Shift budget to Email.")
    monkeypatch.setattr(cli, "_get_llm", lambda cfg: llm)
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    (cfg_dir / "sources.yaml").write_text(
        f"sources:\n  - {demo_data['campaigns']}\n  - {demo_data['sales']}\n")
    res = CliRunner().invoke(cli.app, ["ask", "Quel canal marketing a le meilleur ROI ?",
                                       "--config-dir", str(cfg_dir)])
    assert res.exit_code == 0, res.output
    assert "Shift budget to Email." in res.output
    assert "Données utilisées" in res.output and "ROI" in res.output
    assert "ROAS" in llm.prompts[0]
