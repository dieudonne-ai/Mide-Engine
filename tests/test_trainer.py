import numpy as np
import pandas as pd
import pytest

from mide.automl.task_detector import CLASSIFICATION, REGRESSION, TIMESERIES
from mide.automl.trainer import PROFILE_LIMITS, train_model


@pytest.fixture(scope="module")
def sales(demo_data):
    return pd.read_csv(demo_data["sales"])


@pytest.fixture(scope="module")
def daily(sales):
    return sales.groupby("date", as_index=False)["amount"].sum()


def test_regression_beats_baseline(sales):
    model = train_model(sales, "amount", profile="tiny")
    assert model.task.task == REGRESSION
    assert model.metric == "mae" and model.beats_baseline
    assert len(model.predict(sales.head(5))) == 5


def test_timeseries_beats_baseline(daily):
    model = train_model(daily, "amount", profile="tiny")
    assert model.task.task == TIMESERIES
    assert model.beats_baseline, (model.score, model.baseline_score)


def test_classification_beats_baseline(sales):
    df = sales.assign(big=np.where(sales["amount"] > sales["amount"].median(), "big", "small"))
    model = train_model(df, "big", profile="tiny")
    assert model.task.task == CLASSIFICATION
    assert model.metric == "accuracy" and model.beats_baseline
    assert set(model.predict(df.head(10))) <= {"big", "small"}


def test_reproducible_with_seed(sales):
    a = train_model(sales, "amount", profile="tiny", seed=7)
    b = train_model(sales, "amount", profile="tiny", seed=7)
    assert a.score == b.score
    np.testing.assert_array_equal(a.predict(sales.head(50)), b.predict(sales.head(50)))


def test_missing_values_and_unseen_categories(sales):
    df = sales.copy()
    df.loc[df.sample(frac=0.1, random_state=1).index, "quantity"] = np.nan
    model = train_model(df, "amount", profile="tiny")
    new = df.head(5).copy()
    new["city"] = "Atlantis"
    assert not np.isnan(model.predict(new)).any()


def test_ids_are_not_features(sales):
    model = train_model(sales, "amount", profile="tiny")
    assert "order_id" not in model.features and "customer_id" not in model.features
    assert "date_month" in model.features


def test_profile_limits_model_size(sales):
    tiny = train_model(sales, "amount", profile="tiny")
    n = tiny.pipeline.named_steps["model"].n_estimators
    assert n == PROFILE_LIMITS["tiny"]["n_estimators"] < PROFILE_LIMITS["large"]["n_estimators"]
    assert PROFILE_LIMITS["tiny"]["max_rows"] < PROFILE_LIMITS["large"]["max_rows"]


def test_errors(sales):
    with pytest.raises(ValueError):
        train_model(sales, "amount", profile="huge")
    with pytest.raises(ValueError):
        train_model(sales.head(5), "amount")
    with pytest.raises(ValueError):
        train_model(sales, "nope")
