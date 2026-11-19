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


def test_sales_trend_cites_yoy_basis(data):
    # Two years of demo data: direction is based on YoY growth, which must be cited.
    trend = run_modules(["sales"], data)[0].facts["trend"]
    direction, yoy, recent = trend.split(", ")
    assert direction in {"up", "down", "flat"}
    assert yoy.startswith("YoY ") and "%" in yoy
    assert recent.startswith("last 3 months ")


def test_sales_trend_cites_months_compared(data):
    # Demo sales cover 2023-01-01 -> 2024-12-31: growth figures must say which months they compare.
    trend = run_modules(["sales"], data)[0].facts["trend"]
    assert "YoY " in trend and "(2024-01 -> 2024-12 vs 2023-01 -> 2023-12)" in trend
    assert "(2024-10 -> 2024-12 vs 2024-07 -> 2024-09)" in trend


def test_sales_trend_skips_partial_last_month(data):
    # Data stops mid-December: the partial month is left out, so the windows end in November.
    cut = data.sales[pd.to_datetime(data.sales["date"]) <= "2024-12-15"]
    trend = run_modules(["sales"], BusinessData(sales=cut))[0].facts["trend"]
    assert "2024-12" not in trend
    assert "(2024-09 -> 2024-11 vs 2024-06 -> 2024-08)" in trend


def test_months_compared_needs_enough_months():
    from mide.agent.decision import _months_compared
    monthly = pd.Series([1.0] * 5, index=pd.date_range("2024-01-01", periods=5, freq="MS"))
    assert _months_compared(monthly, 3) == ""
    assert _months_compared(monthly, 2) == " (2024-04 -> 2024-05 vs 2024-02 -> 2024-03)"


def test_sales_trend_without_yoy_shows_recent_only(data):
    short = data.sales[pd.to_datetime(data.sales["date"]) >= "2024-01-01"]
    trend = run_modules(["sales"], BusinessData(sales=short))[0].facts["trend"]
    assert "YoY" not in trend and "last 3 months" in trend


def test_insights_orders_use_thousands_separator(data):
    facts = run_modules(["insights"], data)[0].facts
    assert facts["orders"] == f"{data.sales['order_id'].nunique():,}"
    assert "," in facts["orders"]


def test_reallocation_estimate_is_flagged_as_upper_bound(data):
    # The extra revenue is a linear, optimistic estimate: the figure must say so
    # and cite the ROAS it is based on (explainability).
    facts = run_modules(["marketing"], data)[0].facts
    moves = [v for k, v in facts.items() if k.startswith("move ")]
    assert moves
    best = facts["best channel"]
    roas = facts[f"channel {best}"].split("ROAS ")[1]
    for move in moves:
        assert "est. extra revenue up to " in move
        assert f"linear, at {best} ROAS {roas}" in move
        assert "returns diminish" in move


def _churn_sales(n_lost: int) -> pd.DataFrame:
    """Regular buyers until the end, plus `n_lost` customers silent for a long time."""
    rows = []
    days = pd.date_range("2024-01-01", "2024-12-31", freq="7D")
    for i in range(5):
        rows += [{"customer_id": f"A{i}", "date": d, "amount": 10.0, "order_id": f"A{i}-{k}"}
                 for k, d in enumerate(days)]
    for i in range(n_lost):
        rows += [{"customer_id": f"L{i}", "date": d, "amount": 100.0 * (i + 1),
                  "order_id": f"L{i}-{k}"} for k, d in enumerate(days[:5])]
    return pd.DataFrame(rows)


def test_churn_fact_names_most_valuable_at_risk_customers():
    from mide.agent.decision import _customers_finding

    fact = _customers_finding(_churn_sales(4)).facts["churn"]
    assert fact.startswith("4 customers at high risk (top: L3, L2, L1, ...)")


def test_churn_fact_without_overflow_has_no_ellipsis():
    from mide.agent.decision import _customers_finding

    fact = _customers_finding(_churn_sales(2)).facts["churn"]
    assert "(top: L1, L0)," in fact and "..." not in fact


def test_forecast_fact_cites_the_period_it_covers(data):
    facts = run_modules(["sales"], data)[0].facts
    start = (pd.to_datetime(data.sales["date"]).max() + pd.Timedelta(days=1)).date()
    for h in (30, 60, 90):
        end = start + pd.Timedelta(days=h - 1)
        assert f"for {start} -> {end} (" in facts[f"forecast {h}d"]
        assert facts[f"forecast {h}d"].endswith(f"vs previous {h}d)")


def test_insights_revenue_and_growth_cite_their_period(data):
    # Totals and growth refer to the data's own dates, not to today: say which.
    facts = run_modules(["insights"], data)[0].facts
    dates = pd.to_datetime(data.sales["date"])
    first, last = dates.min().date(), dates.max().date()
    assert facts["revenue"].endswith(f" for {first} -> {last}")
    assert facts["30d growth"].endswith(f" (30 days to {last} vs previous 30)")


def test_insights_growth_without_previous_period_is_na(data):
    sales = data.sales
    short = sales[pd.to_datetime(sales["date"]) >= pd.to_datetime(sales["date"]).max()
                  - pd.Timedelta(days=40)]
    facts = run_modules(["insights"], BusinessData(sales=short))[0].facts
    assert facts["30d growth"] == "n/a"
