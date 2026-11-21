import json

import numpy as np
import pandas as pd
import pytest

from mide.business.insights import analyze, compute_kpis, detect_anomalies
from mide.business.sales import daily_series


@pytest.fixture
def sales(demo_data):
    return pd.read_csv(demo_data["sales"])


@pytest.fixture
def planted(demo_data):
    return json.loads(demo_data["anomalies"].read_text(encoding="utf-8"))


def test_kpis_values():
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-01", "2024-01-02"],
        "order_id": ["a", "b", "c"], "customer_id": ["x", "x", "y"],
        "amount": [10.0, 20.0, 40.0],
    })
    k = compute_kpis(df)
    assert k.total_revenue == 70 and k.orders == 3 and k.customers == 2
    assert k.avg_order_value == pytest.approx(70 / 3)
    assert str(k.best_day.date()) == "2024-01-02" and k.best_day_revenue == 40
    assert k.growth_30d is None  # not enough history


def test_kpis_growth(sales):
    k = compute_kpis(sales)
    assert k.growth_30d == pytest.approx(
        (k.last_30d_revenue - k.previous_30d_revenue) / k.previous_30d_revenue)
    assert k.total_revenue == pytest.approx(sales["amount"].sum())


def test_finds_planted_anomalies(sales, planted):
    found = detect_anomalies(daily_series(sales))
    for p in planted:
        start, end = pd.Timestamp(p["start"]), pd.Timestamp(p["end"])
        hits = [a for a in found if a.start <= end and a.end >= start]
        assert hits, f"missed {p['note']}"
        assert hits[0].kind == p["kind"]


def test_few_false_positives(sales, planted):
    found = detect_anomalies(daily_series(sales))
    assert len(found) <= len(planted) + 2


def test_flat_series_has_no_anomaly():
    rng = np.random.default_rng(0)
    idx = pd.date_range("2024-01-01", periods=120, freq="D")
    s = pd.Series(100 + rng.normal(0, 3, 120), index=idx)
    assert detect_anomalies(s) == []


def test_synthetic_spike_and_drop():
    idx = pd.date_range("2024-01-01", periods=120, freq="D")
    s = pd.Series(100.0, index=idx)
    s.iloc[50] = 400.0
    s.iloc[80:83] = 5.0
    kinds = [(a.kind, a.days) for a in detect_anomalies(s)]
    assert kinds == [("spike", 1), ("drop", 3)]


def test_too_short_series():
    s = pd.Series(1.0, index=pd.date_range("2024-01-01", periods=10))
    with pytest.raises(ValueError):
        detect_anomalies(s)


def test_analyze_and_describe(sales):
    report = analyze(sales)
    assert report.kpis.orders == sales["order_id"].nunique()
    assert report.anomalies and "expected" in report.anomalies[0].describe()


def test_describe_shows_signed_deviation_from_expected():
    """A spike at 3x expected is +200%, a drop to 4% of expected is -96% (not '300%'/'4%')."""
    from mide.business.insights import Anomaly

    day = pd.Timestamp("2024-03-08")
    spike = Anomaly(day, day, "spike", actual=3000.0, expected=1000.0, ratio=3.0, score=9.0)
    drop = Anomaly(day, day + pd.Timedelta(days=2), "drop", actual=40.0, expected=1000.0,
                   ratio=0.04, score=-9.0, days=3)
    assert spike.describe() == "spike on 2024-03-08: 3,000 vs 1,000 expected (+200%)"
    assert drop.describe() == "drop from 2024-03-08 to 2024-03-10: 40 vs 1,000 expected (-96%)"
