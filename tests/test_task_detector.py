import pandas as pd
import pytest

from mide.automl.task_detector import CLASSIFICATION, REGRESSION, TIMESERIES, detect_task


@pytest.fixture
def sales(demo_data):
    return pd.read_csv(demo_data["sales"])


def test_regression_on_transactions(sales):
    info = detect_task(sales, "amount")
    assert info.task == REGRESSION and info.date_column is None


def test_timeseries_on_daily_aggregate(sales):
    daily = sales.groupby("date", as_index=False)["amount"].sum()
    info = detect_task(daily, "amount")
    assert info.task == TIMESERIES and info.date_column == "date"


def test_explicit_date_column_forces_timeseries(sales):
    assert detect_task(sales, "amount", date_column="date").task == TIMESERIES


def test_classification_categorical(sales):
    assert detect_task(sales, "city").task == CLASSIFICATION


def test_classification_binary_numeric(sales):
    df = sales.assign(big=(sales["amount"] > sales["amount"].median()).astype(int))
    assert detect_task(df, "big").task == CLASSIFICATION


def test_campaign_conversions_is_regression(demo_data):
    camp = pd.read_csv(demo_data["campaigns"])
    assert detect_task(camp, "conversions").task == REGRESSION


def test_invalid_inputs(sales):
    with pytest.raises(ValueError):
        detect_task(sales, "nope")
    with pytest.raises(ValueError):
        detect_task(sales, "amount", date_column="nope")
    with pytest.raises(ValueError):
        detect_task(pd.DataFrame({"y": [None, None]}), "y")
