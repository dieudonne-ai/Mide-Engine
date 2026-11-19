import pandas as pd
import pytest

from mide.automl.task_detector import TargetError, TaskType, detect_task


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


def test_unknown_column_errors_list_available_columns():
    df = pd.DataFrame({"amount": [1.5, 2.5], "date": ["2026-01-01", "2026-02-01"]})
    with pytest.raises(ValueError, match="Available columns: amount, date"):
        detect_task(df, "amout")
    with pytest.raises(ValueError, match="Available columns: amount, date"):
        detect_task(df, "amount", date_column="day")


def test_unknown_date_column_raises():
    df = pd.DataFrame({"a": [1.5, 2.5, 3.5, 9.9, 8.8, 7.7, 6.6, 5.5, 4.4, 3.3, 2.2, 1.1]})
    with pytest.raises(ValueError, match="Date column"):
        detect_task(df, "a", date_column="nope")


def test_explicit_date_column_must_hold_dates(demo_frames):
    # Ids, numbers (read as nanosecond timestamps) and the target itself are refused.
    sales = demo_frames["sales"]
    for column, target in [("product_id", "amount"), ("unit_price", "amount"),
                           ("amount", "amount"), ("product_id", "quantity")]:
        with pytest.raises(TargetError, match="does not contain dates") as err:
            detect_task(sales, target, date_column=column)
        assert (err.value.code, err.value.column) == ("not_a_date", column)
    assert detect_task(sales, "amount", date_column="date").task is TaskType.TIME_SERIES


def test_constant_target_raises():
    with pytest.raises(ValueError, match="fewer than 2"):
        detect_task(pd.DataFrame({"a": ["x", "x", "x"]}), "a")


def test_target_errors_have_codes():
    # Unusable targets raise a coded TargetError so interfaces can translate the message.
    cases = [
        (pd.DataFrame({"a": [None, None, None]}), "no_values", "has no values"),
        (pd.DataFrame({"a": ["x", "x", "x"]}), "single_value", "fewer than 2"),
        (pd.DataFrame({"a": [3, 3, 3]}), "single_value", "fewer than 2"),
    ]
    for df, code, text in cases:
        with pytest.raises(TargetError, match=text) as err:
            detect_task(df, "a")
        assert (err.value.code, err.value.column) == (code, "a")


def test_reason_code_names_the_detection_rule(demo_frames):
    # Each rule sets a stable code so interfaces can translate the reason.
    sales = demo_frames["sales"]
    assert detect_task(sales, "amount").reason_code == "dated"
    assert detect_task(sales.drop(columns=["date"]), "amount").reason_code == "continuous"
    assert detect_task(pd.DataFrame({"y": ["a", "b", "a"]}), "y").reason_code == "non_numeric"
    assert detect_task(pd.DataFrame({"y": [0, 1, 1, 0]}), "y").reason_code == "few_integers"
