import numpy as np
import pandas as pd
import pytest

from mide.automl.task_detector import TaskType, detect_task
from mide.automl.trainer import LIMITS, FeaturePrep, TrainingError, train


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
    with pytest.raises(ValueError, match="Not enough rows") as rows_err:
        train(pd.DataFrame({"a": [0.5, 1.5, 2.5], "y": [1.5, 2.5, 3.5]}), "y")
    assert isinstance(rows_err.value, TrainingError)
    assert (rows_err.value.code, rows_err.value.n_rows) == ("not_enough_rows", 3)
    with pytest.raises(TrainingError, match="No usable feature") as feat_err:
        train(pd.DataFrame({"y": [float(i) for i in range(30)]}), "y")
    assert feat_err.value.code == "no_features"


def test_unique_class_target_is_refused():
    # A text target where no value repeats (an id column) cannot be cross-validated.
    from mide.automl.task_detector import TargetError

    df = pd.DataFrame({"a": [float(i) for i in range(30)], "y": [f"C{i:03d}" for i in range(30)]})
    with pytest.raises(TargetError, match="is unique") as err:
        train(df, "y")
    assert (err.value.code, err.value.column) == ("unique_values", "y")
    df["y"] = ["a", "b"] * 15
    assert train(df, "y").task.task is TaskType.CLASSIFICATION


def test_feature_prep_dates():
    df = pd.DataFrame({"d": ["2024-01-05", "2024-02-06"], "y": [1.5, 2.5]})
    prep = FeaturePrep("y").fit(df)
    out = prep.transform(df)
    assert "d_month" in out.columns and out["d_month"].tolist() == [1.0, 2.0]


def test_target_leakage_is_flagged_on_demo_sales(frames):
    # amount = quantity x unit_price: predicting quantity is "perfect" because of a leak.
    result = train(frames["sales"], "quantity", profile="tiny")
    assert result.task.task is TaskType.CLASSIFICATION
    assert result.metrics["accuracy"] >= 0.99
    assert result.leakage_suspects[:2] == ["amount", "unit_price"]
    assert "quantity" not in result.leakage_suspects


def test_target_leakage_regression_and_plausible_models():
    rng = np.random.default_rng(1)
    x = rng.uniform(0, 100, size=300)
    leaky = pd.DataFrame({"price": x, "noise": rng.normal(size=300), "total": 3.0 * x})
    assert train(leaky, "total", profile="tiny").leakage_suspects == ["price"]
    # A useful but imperfect model raises no suspicion.
    noisy = leaky.assign(total=3.0 * x + rng.normal(scale=40, size=300))
    assert train(noisy, "total", profile="tiny").leakage_suspects == []
    label = pd.DataFrame({"x": x, "label": np.where(x + rng.normal(scale=20, size=300) > 50,
                                                    "high", "low")})
    assert train(label, "label", profile="tiny").leakage_suspects == []


def test_leakage_suspects_rules():
    from mide.automl.trainer import leakage_suspects

    prep = FeaturePrep("y", dates=["date"])
    importance = {"date_ordinal": 0.5, "date_day": 0.2, "a": 0.2, "b": 0.1}
    reg = TaskType.REGRESSION
    # Date parts map back to their date column; stops once 60 % of the importance is covered.
    assert leakage_suspects(reg, {"mae": 0.0}, {"mae": 5.0}, importance, prep) == ["date"]
    late = {"a": 0.4, "date_day": 0.1, "b": 0.3}
    assert leakage_suspects(reg, {"mae": 0.0}, {"mae": 5.0}, late, prep) == ["a", "date", "b"]
    assert leakage_suspects(reg, {"mae": 1.0}, {"mae": 5.0}, importance, prep) == []
    assert leakage_suspects(reg, {"mae": 0.0}, {"mae": 0.0}, importance, prep) == []
    spread = {f"c{i}": 0.1 for i in range(10)}
    assert leakage_suspects(reg, {"mae": 0.0}, {"mae": 5.0}, spread, prep) == ["c0", "c1", "c2"]
    ts = TaskType.TIME_SERIES
    assert leakage_suspects(ts, {"mae": 0.0}, {"mae": 5.0}, importance, prep) == []
    clf = TaskType.CLASSIFICATION
    assert leakage_suspects(clf, {"accuracy": 0.995}, {"accuracy": 0.5}, {"a": 1.0}, prep) == ["a"]
    assert leakage_suspects(clf, {"accuracy": 0.95}, {"accuracy": 0.5}, {"a": 1.0}, prep) == []
    # Correlated columns are always suspects, listed first and not repeated.
    assert leakage_suspects(reg, {"mae": 1.0}, {"mae": 5.0}, importance, prep, ["b"]) == ["b"]
    assert leakage_suspects(reg, {"mae": 0.0}, {"mae": 5.0}, importance, prep, ["a"]) == [
        "a", "date"]


def test_correlated_feature_is_a_suspect_even_with_an_imperfect_fit():
    # 40 rows: the trees cannot reach a near-perfect error, but total = 3 x price exactly.
    x = np.arange(40, dtype=float)
    df = pd.DataFrame({"price": x, "other": (x * 7) % 5, "total": 3.0 * x})
    result = train(df, "total", profile="tiny")
    assert result.metrics["mae"] > 0.05 * result.baseline_metrics["mae"]
    assert result.leakage_suspects == ["price"]


def test_date_parts_without_signal_are_dropped():
    monthly = pd.DataFrame(
        {"m": pd.date_range("2023-01-01", periods=24, freq="MS"), "y": np.arange(24.0)}
    )
    cols = FeaturePrep("y", "m").fit(monthly).columns
    assert "m_day" not in cols and "m_day_of_week" not in cols  # 1st of month: calendar noise
    assert {"m_year", "m_month", "m_day_of_year", "m_ordinal"} <= set(cols)

    daily = pd.DataFrame(
        {"d": pd.date_range("2024-01-01", periods=60, freq="D"), "y": np.arange(60.0)}
    )
    cols = FeaturePrep("y", "d").fit(daily).columns
    assert "d_day_of_week" in cols and "d_day" in cols
    assert "d_year" not in cols  # constant within 2024
    out = FeaturePrep("y", "d").fit(daily).transform(daily)
    assert list(out.columns) == cols


def test_monthly_campaign_series_ignores_weekday(frames):
    result = train(frames["campaigns"], "conversions", profile="small")
    assert result.task.task is TaskType.TIME_SERIES
    features = result.prep.columns
    assert "month_day_of_week" not in features and "month_day" not in features
