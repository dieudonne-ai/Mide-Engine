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
    assert "Saved sales-amount v1" in res.output
    res = runner.invoke(app, ["models", "trained", *opt])
    assert "sales-amount v1" in res.output
    bad = runner.invoke(app, ["train", "--dataset", "nope", "--target", "amount", *opt])
    assert bad.exit_code == 1
