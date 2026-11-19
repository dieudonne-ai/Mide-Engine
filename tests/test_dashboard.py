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
    ("fr", "Erreur : Streamlit n'est pas installé : pip install 'mide-engine[ui]'"),
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
    ("fr", "Erreur : tableau de bord introuvable : "),
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
        "chute le 2024-03-10 : 1,200 au lieu de 4,000 attendus (-70%)")
    assert dd.anomaly_text(_anomaly("2024-03-10", "2024-03-12", "spike"), "fr") == (
        "pic du 2024-03-10 au 2024-03-12 : 1,200 au lieu de 4,000 attendus (-70%)")


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
        "ROI de radio -0.20 contre une médiane de 1.50 ; whatsapp rapporte 4.00 "
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
