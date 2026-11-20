from pathlib import Path

import pytest

from mide import dashboard_data as dd
from mide.config import ConfigError
from mide.llm.runtime import FakeLLM

APP = Path(__file__).resolve().parent.parent / "app" / "dashboard.py"


@pytest.fixture
def cfg_dir(tmp_path, monkeypatch, demo_data):
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "sources.yaml").write_text(
        f"sources:\n  - {demo_data['campaigns']}\n  - {demo_data['sales']}\n"
        f"  - {demo_data['products']}\n")
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
    named = dd.sales_view(data.tables.sales, data.tables.products)["products"]["top"]
    assert named.loc["P001", "name"] == "Rice 25kg"
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


@pytest.mark.parametrize(("language", "expected"), [
    ("fr", "Erreur\u00a0: Streamlit n'est pas installé\u00a0: pip install 'mide-engine[ui]'"),
    ("en", "Error: Streamlit is not installed: pip install 'mide-engine[ui]'"),
])
def test_ui_without_streamlit_follows_language(empty_cfg, monkeypatch, language, expected):
    import importlib.util

    from typer.testing import CliRunner

    from mide import cli

    (empty_cfg / "default.yaml").write_text(f"language: {language}\n")
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    res = CliRunner().invoke(cli.app, ["ui", "--config-dir", str(empty_cfg)])
    assert res.exit_code == 1
    assert expected in res.output


@pytest.mark.parametrize(("language", "expected"), [
    ("fr", "Erreur\u00a0: tableau de bord introuvable\u00a0: "),
    ("en", "Error: dashboard not found: "),
])
def test_ui_without_dashboard_follows_language(empty_cfg, monkeypatch, tmp_path, language,
                                               expected):
    import importlib.util

    from typer.testing import CliRunner

    from mide import cli

    (empty_cfg / "default.yaml").write_text(f"language: {language}\n")
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    missing = tmp_path / "missing.py"
    monkeypatch.setattr(cli, "_dashboard_script", lambda: missing)
    res = CliRunner().invoke(cli.app, ["ui", "--config-dir", str(empty_cfg)])
    assert res.exit_code == 1
    assert expected + str(missing) in res.output


def test_dashboard_pages_run_without_error(cfg_dir, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv(dd.CONFIG_ENV, str(cfg_dir))
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    assert not at.exception, at.exception
    for page in ("sales", "customers", "marketing", "sources", "hardware", "home"):
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, (page, at.exception)


def test_dashboard_without_data(empty_cfg, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv(dd.CONFIG_ENV, str(empty_cfg))
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception and at.info


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("fr", "Erreur de configuration : YAML invalide dans"),
        ("en", "Configuration error: Invalid YAML in"),
    ],
)
def test_config_error_message_follows_language(empty_cfg, language, expected):
    # A broken sources.yaml must not force English in the dashboard: the message
    # follows the language of default.yaml, like the CLI errors.
    (empty_cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
    (empty_cfg / "sources.yaml").write_text("sources: [\n", encoding="utf-8")
    with pytest.raises(ConfigError) as info:
        dd.load_dashboard_data(empty_cfg)
    assert dd.config_error_message(info.value, empty_cfg).startswith(expected)


def test_config_error_message_without_default_yaml(empty_cfg):
    # No readable default.yaml: French default, plain error text kept.
    exc = ConfigError("boom")
    assert dd.config_error_message(exc, empty_cfg) == "Erreur de configuration : boom"


def test_ui_text_has_both_languages_with_same_placeholders():
    import string

    def fields(text):
        return {name for _, name, _, _ in string.Formatter().parse(text) if name}

    for key, texts in dd.UI_TEXT.items():
        assert set(texts) == {"fr", "en"}, key
        assert fields(texts["fr"]) == fields(texts["en"]), key


def test_ui_text_falls_back_to_french():
    assert dd.ui_text("high_risk", "en", n=3) == "3 high-risk customers"
    assert dd.ui_text("high_risk", "fr", n=3) == "3 clients à risque élevé"
    assert dd.ui_text("high_risk", "sw", n=3) == "3 clients à risque élevé"


@pytest.mark.parametrize(("language", "home", "sources"), [
    ("fr", "Accueil", "Sources de données"),
    ("en", "Home", "Data sources"),
])
def test_page_labels_follow_language(language, home, sources):
    labels = dd.page_labels(language)
    assert list(labels) == dd.PAGE_KEYS
    assert labels["home"] == home and labels["sources"] == sources


@pytest.mark.parametrize("language", ["fr", "en"])
def test_dashboard_language_reads_config(empty_cfg, language):
    (empty_cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
    assert dd.dashboard_language(empty_cfg) == language


def test_dashboard_language_with_broken_config(empty_cfg):
    (empty_cfg / "default.yaml").write_text("language: en\n", encoding="utf-8")
    (empty_cfg / "sources.yaml").write_text("sources: [\n", encoding="utf-8")
    assert dd.dashboard_language(empty_cfg) == "en"


@pytest.mark.parametrize(("language", "header", "info"), [
    ("fr", "Accueil", "Aucune donnée de ventes trouvée"),
    ("en", "Home", "No sales data found"),
])
def test_dashboard_follows_language(empty_cfg, monkeypatch, language, header, info):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    (empty_cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
    monkeypatch.setenv(dd.CONFIG_ENV, str(empty_cfg))
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception, at.exception
    assert at.header[0].value == header
    assert at.info[0].value.startswith(info)
    assert at.sidebar.radio[0].options[0] == header


def _anomaly(start: str, end: str, kind: str = "drop"):
    import pandas as pd

    from mide.business.insights import Anomaly

    return Anomaly(start=pd.Timestamp(start), end=pd.Timestamp(end), kind=kind,
                   actual=1200.0, expected=4000.0, ratio=0.3, score=5.0)


@pytest.mark.parametrize(("start", "end", "kind"), [
    ("2024-03-10", "2024-03-10", "drop"),
    ("2024-03-10", "2024-03-12", "spike"),
])
def test_anomaly_text_english_matches_describe(start, end, kind):
    a = _anomaly(start, end, kind)
    assert dd.anomaly_text(a, "en") == a.describe()


def test_anomaly_text_french():
    assert dd.anomaly_text(_anomaly("2024-03-10", "2024-03-10"), "fr") == (
        "chute le 2024-03-10\u00a0: 1\u00a0200 au lieu de 4\u00a0000 attendus (-70\u00a0%)")
    assert dd.anomaly_text(_anomaly("2024-03-10", "2024-03-12", "spike"), "fr") == (
        "pic du 2024-03-10 au 2024-03-12\u00a0: 1\u00a0200 au lieu de 4\u00a0000 attendus (-70\u00a0%)")


def test_anomaly_text_unknown_kind_kept():
    assert dd.anomaly_text(_anomaly("2024-03-10", "2024-03-10", "other"), "fr").startswith(
        "other le 2024-03-10")


@pytest.mark.parametrize(("language", "word"), [("fr", "attendus"), ("en", "expected")])
def test_dashboard_anomalies_follow_language(cfg_dir, monkeypatch, language, word):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    (cfg_dir / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
    monkeypatch.setenv(dd.CONFIG_ENV, str(cfg_dir))
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    assert not at.exception, at.exception
    assert at.warning, "the demo data has deliberate anomalies"
    assert all(word in w.value for w in at.warning)


def _move(**figures):
    from mide.business.marketing import BudgetMove

    return BudgetMove(from_channel="radio", to_channel="whatsapp", amount=300.0,
                      reason="radio ROI -0.20 vs median 1.50; whatsapp returns 4.00 revenue "
                             "per unit spent", estimated_extra_revenue=1000.0, **figures)


def test_move_reason_english_matches_marketing_reason(demo_data):
    import pandas as pd

    from mide.business import marketing

    campaigns = pd.read_csv(demo_data["campaigns"])
    plan = marketing.suggest_reallocation(marketing.channel_performance(campaigns))
    assert plan.moves, "the demo data has an underperforming channel"
    assert all(dd.move_reason(m, "en") == m.reason for m in plan.moves)


def test_move_reason_french():
    move = _move(from_roi=-0.2, median_roi=1.5, to_roas=4.0)
    assert dd.move_reason(move, "fr") == (
        "ROI de radio -0,20 contre une médiane de 1,50\u00a0; whatsapp rapporte 4,00 "
        "de chiffre d'affaires par unité dépensée")


def test_move_reason_without_figures_keeps_reason():
    move = _move()
    assert dd.move_reason(move, "fr") == move.reason


@pytest.mark.parametrize(("language", "word"), [("fr", "médiane"), ("en", "median")])
def test_dashboard_marketing_reasons_follow_language(cfg_dir, monkeypatch, language, word):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    (cfg_dir / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
    monkeypatch.setenv(dd.CONFIG_ENV, str(cfg_dir))
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    page = dd.page_labels(language)["marketing"]
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, at.exception
    moves = [m.value for m in at.markdown if "→" in m.value]
    assert moves, "the demo data has a budget move"
    assert all(word in m for m in moves)


def test_column_labels_have_fr_and_en():
    assert all(set(texts) == {"fr", "en"} for texts in dd.COLUMN_LABELS.values())


def test_display_table_translates_columns_and_index():
    import pandas as pd

    df = pd.DataFrame({"name": ["Rice"], "revenue": [10.0], "custom": [1]},
                      index=pd.Index(["P001"], name="product_id"))
    fr = dd.display_table(df, "fr")
    assert list(fr.columns) == ["Nom", "Chiffre d'affaires", "custom"]
    assert fr.index.name == "Produit"
    assert fr.loc["P001", "Nom"] == "Rice"
    en = dd.display_table(df, "en")
    assert list(en.columns) == ["Name", "Revenue", "custom"]
    assert list(df.columns) == ["name", "revenue", "custom"], "input is not modified"


def test_display_table_covers_dashboard_tables(cfg_dir):
    data = dd.load_dashboard_data(cfg_dir)
    sv = dd.sales_view(data.tables.sales, data.tables.products)
    cv = dd.customers_view(data.tables.sales)
    tables = [sv["products"]["top"], cv["segments"], cv["churn"].scores,
              dd.marketing_view(data.tables.campaigns)["channels"]]
    for table in tables:
        names = [table.index.name, *table.columns]
        assert all(n in dd.COLUMN_LABELS for n in names), names


@pytest.mark.parametrize(("language", "column"), [("fr", "Dépenses"), ("en", "Spend")])
def test_dashboard_marketing_columns_follow_language(cfg_dir, monkeypatch, language, column):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    (cfg_dir / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
    monkeypatch.setenv(dd.CONFIG_ENV, str(cfg_dir))
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    at.sidebar.radio[0].set_value(dd.page_labels(language)["marketing"]).run()
    assert not at.exception, at.exception
    assert column in list(at.dataframe[0].value.columns)


@pytest.mark.parametrize(("language", "column"), [("fr", "Niveau de risque"),
                                                  ("en", "Risk level")])
def test_dashboard_customer_columns_follow_language(cfg_dir, monkeypatch, language, column):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    (cfg_dir / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
    monkeypatch.setenv(dd.CONFIG_ENV, str(cfg_dir))
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    at.sidebar.radio[0].set_value(dd.page_labels(language)["customers"]).run()
    assert not at.exception, at.exception
    churn = at.dataframe[1].value
    assert column in list(churn.columns)
    risk = dd.column_label("risk", language)
    assert list(churn[risk]) == sorted(churn[risk], reverse=True), "riskiest first"


def test_value_labels_cover_every_segment_and_risk_level():
    from mide.business import customers

    segments = {customers._segment(r, f, m) for r in range(1, 6)
                for f in range(1, 6) for m in range(1, 6)}
    assert segments == set(dd.VALUE_LABELS["segment"])
    assert set(dd.VALUE_LABELS["risk_level"]) == {"low", "medium", "high"}
    for labels in dd.VALUE_LABELS.values():
        assert all(set(texts) == {"fr", "en"} for texts in labels.values())


def test_value_label_translates_known_values_only():
    assert dd.value_label("risk_level", "high", "fr") == "élevé"
    assert dd.value_label("risk_level", "high", "en") == "high"
    assert dd.value_label("segment", "At risk", "fr") == "À risque"
    assert dd.value_label("segment", "Other", "fr") == "Other"
    assert dd.value_label("name", "high", "fr") == "high", "only listed columns"
    assert dd.value_label("risk", 0.5, "fr") == 0.5


def test_display_table_translates_segments_and_risk_levels():
    import pandas as pd

    segments = pd.DataFrame({"customers": [3, 2]},
                            index=pd.Index(["Loyal", "Hibernating"], name="segment"))
    fr = dd.display_table(segments, "fr")
    assert list(fr.index) == ["Fidèles", "En sommeil"]
    assert list(fr["Clients"]) == [3, 2]
    assert list(dd.display_table(segments, "en").index) == ["Loyal", "Hibernating"]
    churn = pd.DataFrame({"risk": [0.9, 0.1], "risk_level": ["high", "low"]})
    out = dd.display_table(churn, "fr")
    assert list(out["Niveau de risque"]) == ["élevé", "faible"]
    assert list(out["Risque"]) == [0.9, 0.1]
    assert list(churn["risk_level"]) == ["high", "low"], "input is not modified"


@pytest.mark.parametrize(("language", "level"), [("fr", "élevé"), ("en", "high")])
def test_dashboard_customer_values_follow_language(cfg_dir, monkeypatch, language, level):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    (cfg_dir / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
    monkeypatch.setenv(dd.CONFIG_ENV, str(cfg_dir))
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    at.sidebar.radio[0].set_value(dd.page_labels(language)["customers"]).run()
    assert not at.exception, at.exception
    allowed = {dd.value_label("segment", s, language) for s in dd.VALUE_LABELS["segment"]}
    assert set(at.dataframe[0].value.index) <= allowed
    levels = set(at.dataframe[1].value[dd.column_label("risk_level", language)])
    allowed_levels = {dd.value_label("risk_level", v, language) for v in ("low", "medium", "high")}
    assert level in levels and levels <= allowed_levels


def test_chart_series_translates_name_and_index_name():
    import pandas as pd

    roi = pd.Series([1.5, -0.2], index=pd.Index(["whatsapp", "radio"], name="channel"),
                    name="roi")
    out = dd.chart_series(roi, "fr")
    assert out.name == "ROI" and out.index.name == "Canal"
    assert list(out) == [1.5, -0.2] and list(out.index) == ["whatsapp", "radio"]
    assert roi.name == "roi" and roi.index.name == "channel", "input is not modified"
    monthly = pd.Series([10.0], index=pd.DatetimeIndex(["2024-01-01"], name="date"),
                        name="amount")
    assert dd.chart_series(monthly, "fr").name == "Chiffre d'affaires"
    assert dd.chart_series(monthly, "en").name == "Revenue"
    assert dd.chart_series(monthly, "en").index.name == "Date"
    unknown = pd.Series([1.0], name="other")
    assert dd.chart_series(unknown, "fr").name == "other"


def test_chart_series_labels_cover_dashboard_charts(cfg_dir):
    data = dd.load_dashboard_data(cfg_dir)
    sales_view = dd.sales_view(data.tables.sales, data.tables.products)
    channels = dd.marketing_view(data.tables.campaigns)["channels"]
    for series in (sales_view["history"], sales_view["trend"].monthly, channels["roi"]):
        assert series.name in dd.COLUMN_LABELS
        assert series.index.name in dd.COLUMN_LABELS


def _spec_fields(spec: object) -> set[str]:
    """Every ``field`` name used anywhere in a Vega-Lite spec (layers included)."""
    if isinstance(spec, dict):
        found = {spec["field"]} if isinstance(spec.get("field"), str) else set()
        return found.union(*(_spec_fields(v) for v in spec.values()))
    if isinstance(spec, list):
        return set().union(*(_spec_fields(v) for v in spec))
    return set()


def _chart_fields(at) -> set[str]:
    import json

    fields: set[str] = set()
    for node in at.main.children.values():
        if getattr(node, "type", None) == "vega_lite_chart":
            fields |= _spec_fields(json.loads(node.proto.spec))
    return fields


@pytest.mark.parametrize(("language", "page", "expected"), [
    ("fr", "sales", {"Date", "Chiffre d'affaires"}),
    ("en", "sales", {"Date", "Revenue"}),
    ("fr", "marketing", {"Canal", "ROI"}),
    ("en", "marketing", {"Channel", "ROI"}),
])
def test_dashboard_chart_labels_follow_language(cfg_dir, monkeypatch, language, page, expected):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    (cfg_dir / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
    monkeypatch.setenv(dd.CONFIG_ENV, str(cfg_dir))
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    at.sidebar.radio[0].set_value(dd.page_labels(language)[page]).run()
    assert not at.exception, at.exception
    fields = _chart_fields(at)
    assert expected <= fields
    assert not fields & {"amount", "date", "roi", "channel"}


def test_leak_warning_for_flagged_models_only():
    assert dd.leak_warning({"target": "y", "leakage_suspects": []}, "fr") is None
    assert dd.leak_warning({"target": "y"}, "en") is None
    meta = {"target": "quantity", "leakage_suspects": ["amount", "unit_price"]}
    fr = dd.leak_warning(meta, "fr")
    assert fr.startswith("Attention\u00a0: score presque parfait")
    assert "amount, unit_price" in fr and "'quantity'" in fr
    assert dd.leak_warning(meta, "en").startswith("Warning: near-perfect score")


NBSP = "\u00a0"


def _placeholders(text: str) -> set[str]:
    import string

    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_ui_text_french_spacing_before_signs():
    for key, texts in dd.UI_TEXT.items():
        fr = dd.ui_text(key, "fr", **{k: "x" for k in _placeholders(texts["fr"])})
        for sign in ":;?!":
            assert " " + sign + " " not in fr + " ", (key, fr)
    assert dd.ui_text("trend", "fr", value="hausse") == "Tendance" + NBSP + ": hausse"
    assert dd.ui_text("trend", "en", value="up") == "Trend: up"
    assert dd.ui_text("trend", "sw", value="hausse") == "Tendance" + NBSP + ": hausse"


def test_ui_text_french_spacing_leaves_values_untouched():
    text = dd.ui_text("move", "fr", src="a", dst="b", amount="1", reason="x : y", extra="2")
    assert "x : y" in text


@pytest.mark.parametrize(("value", "spec", "fr", "en"), [
    (17037, ",", "17" + NBSP + "037", "17,037"),
    (1234567.4, ",.0f", "1" + NBSP + "234" + NBSP + "567", "1,234,567"),
    (15.73, ".1f", "15,7", "15.7"),
    (0.123, "+.1%", "+12,3" + NBSP + "%", "+12.3%"),
    (-0.2, ".2f", "-0,20", "-0.20"),
])
def test_num_french_and_english(value, spec, fr, en):
    assert dd.num(value, "fr", spec) == fr
    assert dd.num(value, "en", spec) == en
    assert dd.num(value, "sw", spec) == fr


@pytest.mark.parametrize("language", ["fr", "en"])
def test_dashboard_metrics_follow_language(cfg_dir, monkeypatch, language):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    default = cfg_dir / "default.yaml"
    text = default.read_text(encoding="utf-8") if default.exists() else ""
    lines = [line for line in text.splitlines() if not line.startswith("language:")]
    default.write_text("\n".join([*lines, f"language: {language}"]) + "\n", encoding="utf-8")
    monkeypatch.setenv(dd.CONFIG_ENV, str(cfg_dir))
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    assert not at.exception, at.exception
    values = [m.value for m in at.metric]
    at.sidebar.radio[0].set_value("sales").run()
    values += [m.value for m in at.metric]
    assert values
    big = [v for v in values if any(c.isdigit() for c in v) and len(v) > 4]
    assert big
    if language == "fr":
        assert all("," not in v for v in values), values
        assert any(NBSP in v for v in big), values
    else:
        assert all(NBSP not in v for v in values), values
        assert any("," in v for v in big), values
