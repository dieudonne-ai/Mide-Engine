import numpy as np
import pandas as pd
import pytest

from mide.automl.task_detector import TaskType, detect_task
from mide.automl.trainer import LIMITS, FeaturePrep, train


@pytest.fixture
def frames(demo_data):
    return {k: pd.read_csv(demo_data[k]) for k in ("sales", "customers", "campaigns")}


def test_time_series_beats_baseline(frames):
    result = train(frames["sales"], "amount", profile="small")
    assert result.task.task is TaskType.TIME_SERIES
    assert result.beats_baseline
    assert result.metrics["mae"] < result.baseline_metrics["mae"]


def test_regression_beats_baseline(frames):
    sales = frames["sales"]
    info = detect_task(sales.drop(columns="date"), "amount")
    assert info.task is TaskType.REGRESSION
    result = train(sales.drop(columns="date"), "amount", task=info, profile="tiny")
    assert result.beats_baseline
    assert "order_id" not in result.prep.columns  # identifier dropped
    preds = result.predict(sales.head(5))
    assert len(preds) == 5 and np.isfinite(preds).all()


def test_classification_beats_baseline():
    rng = np.random.default_rng(0)
    x = rng.normal(size=400)
    df = pd.DataFrame({"x": x, "noise": rng.normal(size=400),
                       "label": np.where(x > 0, "high", "low")})
    result = train(df, "label")
    assert result.task.task is TaskType.CLASSIFICATION
    assert result.beats_baseline
    assert set(result.predict(df.head(10))) <= {"high", "low"}
    assert result.feature_importance["x"] > result.feature_importance["noise"]


def test_reproducible_with_seed(frames):
    a = train(frames["campaigns"].drop(columns=["campaign_id"]), "revenue", seed=7)
    b = train(frames["campaigns"].drop(columns=["campaign_id"]), "revenue", seed=7)
    assert a.metrics == b.metrics
    assert a.feature_importance == b.feature_importance


def test_profile_limits_scale():
    assert LIMITS["tiny"].n_estimators < LIMITS["large"].n_estimators
    assert LIMITS["tiny"].max_rows < LIMITS["large"].max_rows


def test_row_cap_applies_for_tiny(monkeypatch):
    from mide.automl import trainer

    monkeypatch.setitem(trainer.LIMITS, "tiny", trainer.TrainingLimits(20, 4, 100, 3, 1))
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"a": rng.normal(size=500)})
    df["y"] = df["a"] * 3 + rng.normal(size=500) * 0.1
    assert train(df, "y", profile="tiny").n_rows == 100


def test_missing_values_and_unseen_category():
    rng = np.random.default_rng(2)
    df = pd.DataFrame({"a": rng.normal(size=100), "c": rng.choice(["u", "v"], 100)})
    df.loc[::5, "a"] = np.nan
    df["y"] = df["c"].map({"u": 1.0, "v": 5.0}) + rng.normal(size=100) * 0.1
    result = train(df, "y")
    new = pd.DataFrame({"a": [np.nan], "c": ["never-seen"]})
    assert len(result.predict(new)) == 1


def test_errors():
    with pytest.raises(ValueError, match="Unknown profile"):
        train(pd.DataFrame({"a": [1.5] * 30, "y": range(30)}), "y", profile="huge")
    with pytest.raises(ValueError, match="Not enough rows"):
        train(pd.DataFrame({"a": [0.5, 1.5, 2.5], "y": [1.5, 2.5, 3.5]}), "y")


def test_feature_prep_dates():
    df = pd.DataFrame({"d": ["2024-01-05", "2024-02-06"], "y": [1.5, 2.5]})
    prep = FeaturePrep("y").fit(df)
    out = prep.transform(df)
    assert "d_month" in out.columns and out["d_month"].tolist() == [1.0, 2.0]
