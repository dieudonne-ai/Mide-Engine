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
from mide.business import marketing, sales
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


def test_insights_average_order_value_cites_its_basis(data):
    # "average order value: 43" alone does not say what it divides; cite revenue / orders.
    facts = run_modules(["insights"], data)[0].facts
    assert facts["average order value"] == "43 (735,907 / 17,037 orders)"


def test_insights_average_order_value_basis_on_small_table():
    days = pd.date_range("2024-01-01", periods=60, freq="D")
    sales = pd.DataFrame({"date": days, "amount": [10.0] * 60,
                          "order_id": [i // 2 for i in range(60)]})
    facts = run_modules(["insights"], BusinessData(sales=sales))[0].facts
    assert facts["average order value"] == "20 (600 / 30 orders)"


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

    fact = _customers_finding(_churn_sales(6)).facts["churn"]
    assert fact.startswith("6 customers at high risk (top: L5, L4, L3, +3 more)")


def test_churn_fact_names_the_last_customer_instead_of_hiding_one():
    from mide.agent.decision import _customers_finding

    fact = _customers_finding(_churn_sales(4)).facts["churn"]
    assert fact.startswith("4 customers at high risk (top: L3, L2, L1, L0),")
    assert "more" not in fact and "..." not in fact


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


def test_channel_figures_cite_spend_and_revenue(data):
    # Each channel ratio must cite the totals it comes from (explainability).
    facts = run_modules(["marketing"], data)[0].facts
    channels = marketing.channel_performance(data.campaigns)
    assert len(channels) > 1
    for name, row in channels.iterrows():
        assert facts[f"channel {name}"] == (
            f"spend {row.spend:,.0f}, revenue {row.revenue:,.0f}: "
            f"ROI {row.roi:.2f}, ROAS {row.roas:.2f}")


def test_channel_figure_with_zero_spend_stays_readable():
    df = pd.DataFrame({"channel": ["Email", "Radio"], "spend": [100.0, 0.0],
                       "revenue": [500.0, 50.0], "conversions": [5, 1]})
    facts = run_modules(["marketing"], detect_tables({"campaigns": df}))[0].facts
    assert facts["channel Email"] == "spend 100, revenue 500: ROI 4.00, ROAS 5.00"
    assert facts["channel Radio"] == "spend 0, revenue 50: ROI n/a, ROAS n/a"


def test_product_figures_cite_revenue_and_share_basis(data):
    # Each product share must cite the revenue it comes from and say it is a share of revenue.
    facts = run_modules(["sales"], data)[0].facts
    ranking = sales.product_ranking(data.sales, n=2)
    names = sales.product_names(data.products)
    for key, table in (("top products", ranking["top"]), ("flop products", ranking["flop"])):
        expected = ", ".join(
            f"{pid} {names[str(pid)]} ({row.revenue:,.0f} = {row.share_pct:.1f}% of revenue)"
            for pid, row in table.iterrows())
        assert facts[key] == expected


def test_product_figure_without_catalog_cites_revenue():
    days = pd.date_range("2024-01-01", periods=60, freq="D")
    df = pd.DataFrame({"date": days, "product_id": ["A", "A", "A", "B"] * 15, "amount": 100.0})
    facts = run_modules(["sales"], BusinessData(sales=df))[0].facts
    assert facts["top products"] == "A (4,500 = 75.0% of revenue), B (1,500 = 25.0% of revenue)"


def test_no_flop_figure_when_every_product_is_already_top():
    # Two products: both are top, so neither may be called a flop (A has 75% of revenue).
    days = pd.date_range("2024-01-01", periods=60, freq="D")
    df = pd.DataFrame({"date": days, "product_id": ["A", "A", "A", "B"] * 15, "amount": 100.0})
    facts = run_modules(["sales"], BusinessData(sales=df))[0].facts
    assert "flop products" not in facts


def test_marketing_flags_attribution_above_total_sales(data):
    # Demo channels claim about twice total sales: the figures must say so.
    facts = run_modules(["marketing"], data)[0].facts
    attributed = marketing.channel_performance(data.campaigns)["revenue"].sum()
    total = data.sales["amount"].sum()
    assert attributed > total
    assert facts["attribution check"] == (
        f"channels report {attributed:,.0f} revenue, {attributed / total:.2f}x "
        f"total sales {total:,.0f}; the same sale is likely counted by several channels, "
        "so compare ROI/ROAS between channels rather than as absolute returns")


def test_marketing_no_attribution_check_when_consistent_or_no_sales():
    campaigns = pd.DataFrame({"channel": ["Email", "Radio"], "spend": [100.0, 100.0],
                              "revenue": [300.0, 200.0]})
    sales_df = pd.DataFrame({"date": ["2024-01-01"], "customer_id": ["C1"],
                             "amount": [1000.0]})
    consistent = run_modules(["marketing"], BusinessData(sales=sales_df, campaigns=campaigns))
    alone = run_modules(["marketing"], BusinessData(campaigns=campaigns))
    assert "attribution check" not in consistent[0].facts
    assert "attribution check" not in alone[0].facts


def test_churn_fact_cites_share_of_revenue_and_customer_base():
    from mide.agent.decision import _customers_finding

    # 5 regular buyers (53 x 10 = 530 each) + 2 lost (5 x 100, 5 x 200): 1,500 of 4,150.
    fact = _customers_finding(_churn_sales(2)).facts["churn"]
    assert fact.endswith("1,500 past revenue at risk (36.1% of revenue; 2 of 7 customers)")


def test_churn_fact_on_demo_data_cites_its_scale(data):
    fact = run_modules(["customers"], data)[0].facts["churn"]
    assert fact.endswith(
        "2,344 past revenue at risk (0.3% of revenue; 4 of 400 customers)")


def test_customer_segments_on_demo_data_include_at_risk(data):
    facts = run_modules(["customers"], data)[0].facts
    segments = {k: v for k, v in facts.items() if k.startswith("segment ")}
    assert segments["segment At risk"] == "44 customers, 9.1% of revenue"
    assert len(segments) == 6
    assert sum(int(v.split()[0]) for v in segments.values()) == 400


def test_data_used_labels_follow_language():
    from mide.agent.decision import Finding, Recommendation, fact_label

    findings = [Finding("sales", {"forecast 30d": "45,871", "top products": "P001"}),
                Finding("marketing", {"channel SMS": "ROI -0.58", "move Radio": "6,840"}),
                Finding("insights", {"anomaly 2": "spike", "custom key": "x"})]
    rec = Recommendation("t", findings)
    fr = rec.data_used("fr")
    assert "- [sales] prévision à 30 jours: 45,871" in fr
    assert "- [sales] meilleurs produits: P001" in fr
    assert "- [marketing] canal SMS: ROI -0.58" in fr
    assert "- [marketing] transfert depuis Radio: 6,840" in fr
    assert "- [insights] anomalie 2: spike" in fr
    assert "- [insights] custom key: x" in fr
    en = rec.data_used("en")
    assert "- [sales] forecast 30d: 45,871" in en and "- [marketing] channel SMS" in en
    assert "- [marketing] move Radio: 6,840" in en and "top products: P001" in en
    assert fact_label("30d growth", "fr") == "croissance sur 30 jours"
    assert fact_label("trend", "xx") == "tendance"
