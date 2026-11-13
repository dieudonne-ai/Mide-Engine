import pandas as pd
import pytest

from mide.automl.task_detector import TaskType, detect_task


@pytest.fixture
def demo_frames(demo_data):
    return {k: pd.read_csv(demo_data[k]) for k in ("sales", "customers", "products", "campaigns")}


def test_time_series_on_sales(demo_frames):
    info = detect_task(demo_frames["sales"], "amount")
    assert info.task is TaskType.TIME_SERIES
    assert info.date_column == "date"
    assert info.frequency == "D"


def test_classification_on_text_target(demo_frames):
    info = detect_task(demo_frames["customers"], "segment")
    assert info.task is TaskType.CLASSIFICATION
    assert info.n_classes >= 2


def test_regression_without_date(demo_frames):
    info = detect_task(demo_frames["products"], "price")
    assert info.task is TaskType.REGRESSION
    assert info.date_column is None


def test_monthly_frequency(demo_frames):
    df = demo_frames["campaigns"]
    df["month"] = pd.to_datetime(df["month"].astype(str) + "-01", errors="coerce")
    info = detect_task(df, "spend", date_column="month")
    assert info.task is TaskType.TIME_SERIES
    assert info.frequency == "MS"


def test_binary_integer_target_is_classification():
    df = pd.DataFrame({"churn": [0, 1, 0, 1, 1, 0], "x": [1.5, 2.2, 3.1, 4.7, 5.3, 6.9]})
    info = detect_task(df, "churn")
    assert info.task is TaskType.CLASSIFICATION
    assert info.n_classes == 2


def test_boolean_target_is_classification():
    df = pd.DataFrame({"won": [True, False, True, False]})
    assert detect_task(df, "won").task is TaskType.CLASSIFICATION


def test_unknown_target_raises():
    with pytest.raises(ValueError, match="not found"):
        detect_task(pd.DataFrame({"a": [1.5, 2.5]}), "b")


def test_unknown_date_column_raises():
    df = pd.DataFrame({"a": [1.5, 2.5, 3.5, 9.9, 8.8, 7.7, 6.6, 5.5, 4.4, 3.3, 2.2, 1.1]})
    with pytest.raises(ValueError, match="Date column"):
        detect_task(df, "a", date_column="nope")


def test_constant_target_raises():
    with pytest.raises(ValueError, match="fewer than 2"):
        detect_task(pd.DataFrame({"a": ["x", "x", "x"]}), "a")
