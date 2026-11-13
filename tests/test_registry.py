import numpy as np
import pandas as pd
import pytest

from mide.automl.evaluator import (
    classification_metrics,
    evaluate_model,
    feature_importance,
    mape,
    regression_metrics,
)
from mide.automl.registry import ModelRegistry, model_name, slugify
from mide.automl.trainer import train_model


@pytest.fixture(scope="module")
def sales(demo_data):
    return pd.read_csv(demo_data["sales"])


@pytest.fixture(scope="module")
def model(sales):
    return train_model(sales, "amount", profile="tiny")


def test_regression_metrics():
    m = regression_metrics([100, 200, 0], [110, 180, 5])
    assert m["mae"] == pytest.approx(35 / 3)
    assert m["mape"] == pytest.approx((0.1 + 0.1) / 2)  # zero target ignored
    assert np.isnan(mape([0, 0], [1, 1]))


def test_classification_metrics_binary_and_multiclass():
    proba = np.array([[0.9, 0.1], [0.2, 0.8], [0.4, 0.6], [0.7, 0.3]])
    m = classification_metrics([0, 1, 1, 0], [0, 1, 1, 0], proba, [0, 1])
    assert m["accuracy"] == 1.0 and m["f1"] == 1.0 and m["auc"] == 1.0
    p3 = np.eye(3)[[0, 1, 2, 0]]
    m3 = classification_metrics([0, 1, 2, 0], [0, 1, 2, 0], p3, [0, 1, 2])
    assert m3["auc"] == 1.0


def test_evaluate_and_importance(model, sales):
    metrics = evaluate_model(model, sales)
    assert set(metrics) == {"mae", "mape"}
    imp = feature_importance(model)
    assert sum(imp.values()) == pytest.approx(1.0, abs=1e-3)
    assert list(imp.values()) == sorted(imp.values(), reverse=True)


def test_evaluate_classification(sales):
    df = sales.assign(big=np.where(sales["amount"] > sales["amount"].median(), "big", "small"))
    clf = train_model(df, "big", profile="tiny")
    metrics = evaluate_model(clf, df)
    assert {"accuracy", "f1", "auc"} <= set(metrics)


def test_save_load_roundtrip_and_versions(tmp_path, model, sales):
    reg = ModelRegistry(tmp_path / "models_trained")
    assert reg.list() == []
    r1 = reg.save(model, "sales amount", "x.csv", {"mae": 1.0}, {"qty": 1.0})
    r2 = reg.save(model, "sales amount")
    assert (r1.version, r2.version) == (1, 2)
    assert r1.name == "sales_amount"
    assert [r.version for r in reg.list()] == [1, 2]
    assert reg.record("sales amount").version == 2
    assert reg.record("sales amount", 1).metrics == {"mae": 1.0}
    loaded = reg.load("sales amount", 1)
    np.testing.assert_array_equal(loaded.predict(sales.head(20)), model.predict(sales.head(20)))
    assert loaded.score == model.score


def test_missing_model_and_safe_names(tmp_path):
    reg = ModelRegistry(tmp_path)
    with pytest.raises(KeyError):
        reg.load("nope")
    with pytest.raises(KeyError):
        reg.record("nope", 3)
    assert ".." not in slugify("../../etc")
    assert model_name("/d/sales.csv", "amount") == "sales_amount"
    assert model_name("/d/book.xlsx::Q1", "amount") == "book_Q1_amount"


def test_train_and_list_cli(tmp_path, monkeypatch, demo_data):
    from typer.testing import CliRunner

    from mide.cli import app

    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "sources.yaml").write_text(f"sources:\n  - {demo_data['sales']}\n")
    runner = CliRunner()
    args = ["--dataset", str(demo_data["sales"]), "--target", "amount", "--config-dir", str(cfg)]
    out = runner.invoke(app, ["train", *args])
    assert out.exit_code == 0, out.output
    assert "Saved: sales_amount v1" in out.output
    listing = runner.invoke(app, ["models", "trained", "--config-dir", str(cfg)])
    assert "sales_amount v1" in listing.output and "beats baseline" in listing.output


def test_train_refuses_unauthorized_dataset(tmp_path, monkeypatch, demo_data):
    from typer.testing import CliRunner

    from mide.cli import app

    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "sources.yaml").write_text("sources: []\n")
    out = CliRunner().invoke(
        app,
        ["train", "--dataset", str(demo_data["sales"]), "--target", "amount",
         "--config-dir", str(cfg)],
    )  # fmt: skip
    assert out.exit_code == 1
