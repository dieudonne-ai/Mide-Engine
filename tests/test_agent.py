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


@pytest.mark.parametrize("question", [
    "What are my 3 priority actions this week?",
    "Quelles actions prioritaires cette semaine ?",
    "Que dois-je faire ce mois-ci ?",
    "What do you recommend?",
])
def test_action_questions_use_all_business_modules(question):
    route = route_question(question)
    assert route.kind == "business"
    assert set(route.modules) == {"sales", "customers", "marketing", "insights"}


def test_transactions_is_not_an_action_question():
    assert route_question("How many transactions did we log?").kind == "rag"


def test_insights_keeps_most_recent_anomalies(monkeypatch, data):
    from mide.agent import decision
    from mide.business import insights

    real = insights.analyze

    def many_anomalies(df):
        report = real(df)
        base = report.anomalies[0]
        report.anomalies = [
            insights.Anomaly(base.start + pd.Timedelta(days=30 * i),
                             base.start + pd.Timedelta(days=30 * i), "drop", 1, 10, 0.1, 9)
            for i in range(7)]
        return report

    monkeypatch.setattr(decision.insights, "analyze", many_anomalies)
    facts = run_modules(["insights"], data)[0].facts
    anomalies = [v for k, v in facts.items() if k.startswith("anomaly")]
    assert len(anomalies) == 5
    last = (pd.Timestamp(real(data.sales).anomalies[0].start) + pd.Timedelta(days=180)).date()
    assert str(last) in anomalies[-1]


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


def _business_cfg(tmp_path, monkeypatch, demo_data, language="fr"):
    from mide import cli
    from mide.llm.downloader import DownloadError

    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))

    def no_llm(cfg):
        raise DownloadError("Model not installed: run `mide models pull` (x.gguf).")

    monkeypatch.setattr(cli, "_get_llm", no_llm)
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    (cfg_dir / "sources.yaml").write_text(
        f"sources:\n  - {demo_data['campaigns']}\n  - {demo_data['sales']}\n")
    if language != "fr":
        (cfg_dir / "default.yaml").write_text(f"language: {language}\n")
    return cli, cfg_dir


def test_ask_business_question_without_llm_shows_figures(tmp_path, monkeypatch, demo_data):
    from typer.testing import CliRunner

    cli, cfg_dir = _business_cfg(tmp_path, monkeypatch, demo_data)
    res = CliRunner().invoke(cli.app, ["ask", "Quel canal marketing a le meilleur ROI ?",
                                       "--config-dir", str(cfg_dir)])
    assert res.exit_code == 0, res.output
    assert "LLM local indisponible" in res.output and "mide models pull" in res.output
    assert "Données utilisées" in res.output and "ROI" in res.output


def test_ask_answer_without_llm_english(tmp_path, monkeypatch, demo_data):
    cli, cfg_dir = _business_cfg(tmp_path, monkeypatch, demo_data, language="en")
    answer, used, _ = cli.ask_answer("Which customers are at risk of churn?", cfg_dir)
    assert answer.startswith("Local LLM unavailable")
    assert used.startswith("Data used") and "churn" in used


def test_ask_document_question_without_llm_still_fails(tmp_path, monkeypatch, demo_data):
    from mide.llm.downloader import DownloadError

    cli, cfg_dir = _business_cfg(tmp_path, monkeypatch, demo_data)
    monkeypatch.setattr(cli, "VectorStore", lambda path: type("S", (), {"count": lambda s: 1})())
    monkeypatch.setattr(cli, "_get_embedder", lambda cfg: None)
    monkeypatch.setattr(cli, "Retriever", lambda *a: type("R", (), {
        "retrieve": lambda s, q, source=None: []})())
    with pytest.raises(DownloadError):
        cli.ask_answer("What is our return policy?", cfg_dir)


def test_products_catalog_detected(data):
    assert data.products is not None and "name" in data.products.columns


def test_sales_finding_cites_product_names(data):
    facts = run_modules(["sales"], data)[0].facts
    assert facts["top products"].startswith("P001 Rice 25kg (")
    assert facts["flop products"].startswith("P009 ")


def test_sales_finding_without_catalog_uses_ids(data):
    plain = BusinessData(sales=data.sales)
    assert run_modules(["sales"], plain)[0].facts["top products"].startswith("P001 (")
