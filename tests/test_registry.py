import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from mide.automl.evaluator import evaluate, feature_importance, mape
from mide.automl.registry import RegistryError, list_models, load_model, save_model
from mide.automl.trainer import train
from mide.cli import app


@pytest.fixture(scope="module")
def sales(demo_data):
    return pd.read_csv(demo_data["sales"])


@pytest.fixture(scope="module")
def trained_ts(sales):
    return train(sales, "amount", profile="tiny")


def test_evaluate_time_series(trained_ts, sales):
    m = evaluate(trained_ts, sales)
    assert {"mae", "mape", "rmse", "r2"} <= m.keys()
    assert m["mae"] >= 0 and m["r2"] > 0


def test_evaluate_classification():
    rng = np.random.default_rng(0)
    x = rng.normal(size=300)
    df = pd.DataFrame({"x": x, "y": np.where(x + rng.normal(scale=0.3, size=300) > 0, "a", "b")})
    model = train(df, "y", profile="tiny")
    m = evaluate(model, df)
    assert m["accuracy"] > 0.8 and 0.5 < m["auc"] <= 1.0
    assert "f1_macro" in m


@pytest.mark.parametrize("labels", [(0, 1), (1, 2, 3, 4)])
def test_evaluate_integer_classes(labels):
    # Integer class labels (e.g. a quantity target) used to crash sklearn ("unknown").
    rng = np.random.default_rng(1)
    y = rng.choice(labels, size=300)
    df = pd.DataFrame({"x": y + rng.normal(scale=0.1, size=300), "y": y})
    model = train(df, "y", profile="tiny")
    assert model.task.task.value == "classification"
    m = evaluate(model, df)
    assert m["accuracy"] > 0.9 and 0.5 < m["auc"] <= 1.0


def test_mape_ignores_zero():
    assert mape(np.array([0.0, 100.0]), np.array([5.0, 90.0])) == pytest.approx(10.0)
    assert np.isnan(mape(np.array([0.0]), np.array([1.0])))


def test_feature_importance_sorted(trained_ts):
    top = feature_importance(trained_ts, top=3)
    assert len(top) <= 3
    assert list(top.values()) == sorted(top.values(), reverse=True)


def test_save_load_roundtrip_and_versions(trained_ts, sales, tmp_path):
    r1 = save_model(trained_ts, tmp_path, "Sales amount")
    r2 = save_model(trained_ts, tmp_path, "Sales amount")
    assert (r1.version, r2.version) == (1, 2)
    assert r1.metadata["beats_baseline"] is True
    loaded, record = load_model(tmp_path, "Sales amount")
    assert record.version == 2
    sample = sales.head(5)
    assert np.allclose(loaded.predict(sample), trained_ts.predict(sample))
    _, old = load_model(tmp_path, "Sales amount", version=1)
    assert old.version == 1
    assert [(r.name, r.version) for r in list_models(tmp_path)] == [
        ("Sales_amount", 1), ("Sales_amount", 2)
    ]


def test_registry_errors(tmp_path):
    assert list_models(tmp_path / "missing") == []
    with pytest.raises(RegistryError):
        load_model(tmp_path, "nope")


def test_cli_train_and_list(demo_data, tmp_path, monkeypatch):
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    runner = CliRunner()
    opt = ["--config-dir", str(cfg)]
    runner.invoke(app, ["sources", "add", str(demo_data["sales"]), *opt])
    res = runner.invoke(app, ["train", "--dataset", "sales", "--target", "amount", *opt])
    assert res.exit_code == 0, res.output
    assert "Modèle enregistré : sales-amount v1" in res.output
    res = runner.invoke(app, ["models", "trained", *opt])
    assert "sales-amount v1" in res.output
    bad = runner.invoke(app, ["train", "--dataset", "nope", "--target", "amount", *opt])
    assert bad.exit_code == 1
    assert "Jeux de données disponibles : sales" in bad.output
    bad = runner.invoke(app, ["train", "--dataset", "sales", "--target", "amout", *opt])
    assert bad.exit_code == 1
    assert "Colonnes disponibles :" in bad.output and "amount" in bad.output


def test_cli_train_integer_class_target(demo_data, tmp_path, monkeypatch):
    # `quantity` (few integer values) is a classification target; training must not crash.
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    runner = CliRunner()
    opt = ["--config-dir", str(cfg)]
    runner.invoke(app, ["sources", "add", str(demo_data["sales"]), *opt])
    res = runner.invoke(app, ["train", "--dataset", "sales", "--target", "quantity", *opt])
    assert res.exit_code == 0, res.output
    assert "Modèle enregistré : sales-quantity v1" in res.output
    assert "VC accuracy" in res.output


def test_cli_train_unknown_column_follows_language(demo_data, tmp_path, monkeypatch):
    # Wrong --target / --date-column errors are fully in the configured language.
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    runner = CliRunner()
    opt = ["--config-dir", str(cfg)]
    runner.invoke(app, ["sources", "add", str(demo_data["sales"]), *opt])
    cases = {
        "fr": [("Erreur : Colonne cible 'amout' introuvable dans le jeu de données. "
                "Colonnes disponibles : "),
               ("Erreur : Colonne de date 'jour' introuvable dans le jeu de données. "
                "Colonnes disponibles : ")],
        "en": ["Error: Target column 'amout' not found in dataset. Available columns: ",
               "Error: Date column 'jour' not found in dataset. Available columns: "],
    }
    for language, (target_line, date_line) in cases.items():
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        res = runner.invoke(app, ["train", "--dataset", "sales", "--target", "amout", *opt])
        assert res.exit_code == 1
        assert target_line in res.output and "amount" in res.output, (language, res.output)
        res = runner.invoke(app, ["train", "--dataset", "sales", "--target", "amount",
                                  "--date-column", "jour", *opt])
        assert res.exit_code == 1
        assert date_line in res.output and "amount" in res.output, (language, res.output)


def test_cli_train_training_errors_follow_language(tmp_path, monkeypatch):
    # Trainer errors (too few rows, no usable feature) are in the configured language.
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    data = tmp_path / "data"
    data.mkdir()
    pd.DataFrame({"a": [0.5, 1.5, 2.5], "y": [1.5, 2.5, 3.5]}).to_csv(data / "tiny.csv",
                                                                       index=False)
    pd.DataFrame({"y": [float(i) for i in range(30)]}).to_csv(data / "only.csv", index=False)
    cfg = tmp_path / "cfg"
    runner = CliRunner()
    opt = ["--config-dir", str(cfg)]
    runner.invoke(app, ["sources", "add", str(data), *opt])
    expected = {
        "fr": ["Erreur : Pas assez de lignes pour entraîner (3) ; il en faut au moins 20",
               "Erreur : Aucune colonne utilisable comme variable explicative"],
        "en": ["Error: Not enough rows to train (3); at least 20 are needed",
               "Error: No usable feature columns found"],
    }
    for language, (rows_line, features_line) in expected.items():
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        res = runner.invoke(app, ["train", "--dataset", "tiny", "--target", "y", *opt])
        assert res.exit_code == 1
        assert rows_line in res.output, (language, res.output)
        res = runner.invoke(app, ["train", "--dataset", "only", "--target", "y", *opt])
        assert res.exit_code == 1
        assert features_line in res.output, (language, res.output)


def test_cli_train_target_errors_follow_language(tmp_path, monkeypatch):
    # Unusable targets (empty column, a single value) are reported in the configured language.
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    data = tmp_path / "data"
    data.mkdir()
    pd.DataFrame({"a": [0.5, 1.5, 2.5], "y": ["", "", ""]}).to_csv(data / "empty.csv",
                                                                    index=False)
    pd.DataFrame({"a": [0.5, 1.5, 2.5], "y": ["x", "x", "x"]}).to_csv(data / "same.csv",
                                                                       index=False)
    cfg = tmp_path / "cfg"
    runner = CliRunner()
    opt = ["--config-dir", str(cfg)]
    runner.invoke(app, ["sources", "add", str(data), *opt])
    expected = {
        "fr": ["Erreur : La colonne cible 'y' ne contient aucune valeur",
               "Erreur : La colonne cible 'y' a moins de 2 valeurs distinctes"],
        "en": ["Error: Target column 'y' has no values",
               "Error: Target column 'y' has fewer than 2 distinct values"],
    }
    for language, (empty_line, same_line) in expected.items():
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        res = runner.invoke(app, ["train", "--dataset", "empty", "--target", "y", *opt])
        assert res.exit_code == 1
        assert empty_line in res.output, (language, res.output)
        res = runner.invoke(app, ["train", "--dataset", "same", "--target", "y", *opt])
        assert res.exit_code == 1
        assert same_line in res.output, (language, res.output)


def test_cli_train_unknown_dataset_follows_language(demo_data, tmp_path, monkeypatch):
    # The "dataset not found" error is fully in the configured language.
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    runner = CliRunner()
    opt = ["--config-dir", str(cfg)]
    runner.invoke(app, ["sources", "add", str(demo_data["sales"]), *opt])
    expected = {
        "fr": "Erreur : Jeu de données introuvable dans les sources autorisées : nope. "
              "Jeux de données disponibles : sales",
        "en": "Error: Dataset not found in authorized sources: nope. Available datasets: sales",
    }
    for language, line in expected.items():
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        res = runner.invoke(app, ["train", "--dataset", "nope", "--target", "amount", *opt])
        assert res.exit_code == 1
        assert line in res.output, (language, res.output)


def test_cli_train_output_follows_language(demo_data, tmp_path, monkeypatch):
    # `mide train` result lines use the configured language (default fr).
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    runner = CliRunner()
    opt = ["--config-dir", str(cfg)]
    runner.invoke(app, ["sources", "add", str(demo_data["sales"]), *opt])
    expected = {
        "fr": ["Tâche : série temporelle - cible numérique avec la colonne de date ", "Modèle enregistré : sales-amount v1", "  VC ", "(référence ",
               "Le modèle bat la référence.", "Variables principales : "],
        "en": ["Task: ", "Saved sales-amount v2", "  CV ", "(baseline ",
               "The model beats the baseline.", "Top features: "],
    }
    for language, lines in expected.items():
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        res = runner.invoke(app, ["train", "--dataset", "sales", "--target", "amount", *opt])
        assert res.exit_code == 0, res.output
        for line in lines:
            assert line in res.output, (language, line)


def test_cli_models_trained_follows_language(demo_data, tmp_path, monkeypatch):
    # `mide models trained` lines are localized; English keeps the historical format.
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    runner = CliRunner()
    opt = ["--config-dir", str(cfg)]
    runner.invoke(app, ["sources", "add", str(demo_data["sales"]), *opt])
    res = runner.invoke(app, ["train", "--dataset", "sales", "--target", "amount", *opt])
    assert res.exit_code == 0, res.output
    res = runner.invoke(app, ["models", "trained", *opt])
    assert res.exit_code == 0, res.output
    assert "sales-amount v1 [série temporelle] cible=amount " in res.output
    assert "bat_reference=oui" in res.output
    (cfg / "default.yaml").write_text("language: en\n", encoding="utf-8")
    res = runner.invoke(app, ["models", "trained", *opt])
    assert res.exit_code == 0, res.output
    assert "sales-amount v1 [time_series] target=amount " in res.output
    assert "beats_baseline=True" in res.output


def test_cli_models_trained_invalid_config(tmp_path):
    # A broken config gives a clear error instead of a traceback.
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "default.yaml").write_text("language: de\n", encoding="utf-8")
    res = CliRunner().invoke(app, ["models", "trained", "--config-dir", str(cfg)])
    assert res.exit_code == 1
    assert "Erreur :" in res.output and "language" in res.output
    assert res.exception is None or isinstance(res.exception, SystemExit)


def test_trained_line_handles_missing_score():
    from mide.cli import _trained_line

    meta = {"task": "regression", "target": "y", "primary_metric": "mae",
            "metrics": {}, "beats_baseline": False}
    assert _trained_line("m", 2, meta, "fr") == "m v2 [régression] cible=y mae=? bat_reference=non"
