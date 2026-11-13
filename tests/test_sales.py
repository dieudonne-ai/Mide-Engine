import pandas as pd
import pytest

from mide.business.sales import (
    daily_series,
    detect_seasonality,
    forecast_sales,
    product_ranking,
    sales_trend,
)


@pytest.fixture
def sales(demo_data):
    return pd.read_csv(demo_data["sales"])


def test_daily_series_is_continuous(sales):
    s = daily_series(sales)
    assert s.index.is_monotonic_increasing
    assert len(s) == (s.index[-1] - s.index[0]).days + 1
    assert s.sum() == pytest.approx(sales["amount"].sum())


def test_forecast_horizons_and_sanity(sales):
    fc = forecast_sales(sales)
    assert set(fc.totals) == {30, 60, 90}
    assert len(fc.daily) == 90
    assert (fc.daily >= 0).all()
    assert fc.totals[30] < fc.totals[60] < fc.totals[90]
    assert fc.daily.index[0] == pd.to_datetime(sales["date"]).max() + pd.Timedelta(days=1)
    # Demo data grows ~25%/yr and peaks in Dec: Jan 2025 should not collapse.
    last30 = fc.previous_totals[30]
    assert 0.5 * last30 < fc.totals[30] < 2.5 * last30
    assert any("anomalous" in n for n in fc.notes)


def test_forecast_needs_history(sales):
    with pytest.raises(ValueError):
        forecast_sales(sales.head(20))


def test_product_ranking_finds_top_and_flop(sales):
    rank = product_ranking(sales, n=2)
    assert rank["top"].index[0] == "P001"
    assert rank["flop"].index[0] == "P009"
    assert rank["top"]["share_pct"].iloc[0] > rank["flop"]["share_pct"].iloc[0]


def test_trend_is_growing(sales):
    trend = sales_trend(sales)
    assert trend.direction == "up"
    assert trend.yoy_growth_pct is not None and trend.yoy_growth_pct > 5


def test_detects_generated_seasonality(sales):
    seas = detect_seasonality(sales)
    assert seas.has_yearly_seasonality
    assert seas.peak_month in {"Nov", "Dec", "Jan"}
    assert seas.trough_month in {"Jun", "Jul", "Aug", "Sep"}
    assert seas.peak_weekday == "Sat"
    assert seas.monthly_index["Dec"] > seas.monthly_index["Aug"]


def test_no_seasonality_on_flat_data():
    dates = pd.date_range("2023-01-01", "2024-12-31", freq="D")
    flat = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "amount": 100.0})
    assert not detect_seasonality(flat).has_yearly_seasonality
