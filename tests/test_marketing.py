import pandas as pd
import pytest

from mide.business.marketing import (
    campaign_performance,
    channel_performance,
    suggest_reallocation,
    underperforming_channels,
)


@pytest.fixture
def campaigns(demo_data):
    return pd.read_csv(demo_data["campaigns"])


@pytest.fixture
def toy():
    return pd.DataFrame({
        "campaign_id": ["a", "b", "c"],
        "channel": ["Good", "Bad", "Good"],
        "spend": [100.0, 100.0, 100.0],
        "impressions": [1000, 1000, 1000],
        "clicks": [100, 100, 100],
        "conversions": [10, 1, 10],
        "revenue": [400.0, 50.0, 400.0],
    })


def test_channel_values(toy):
    t = channel_performance(toy)
    assert t.loc["Good", "spend"] == 200
    assert t.loc["Good", "roi"] == pytest.approx(3.0)
    assert t.loc["Bad", "roi"] == pytest.approx(-0.5)
    assert t.loc["Good", "cost_per_conversion"] == pytest.approx(10.0)
    assert t.loc["Bad", "conversion_rate"] == pytest.approx(0.01)
    assert list(t.index) == ["Good", "Bad"]


def test_zero_spend_gives_nan():
    df = pd.DataFrame({"channel": ["X"], "spend": [0.0], "revenue": [10.0]})
    assert pd.isna(channel_performance(df).loc["X", "roi"])


def test_missing_column_raises():
    with pytest.raises(ValueError):
        channel_performance(pd.DataFrame({"channel": ["a"]}))


def test_campaign_performance(toy):
    t = campaign_performance(toy)
    assert len(t) == 3
    assert t.index[-1] == "b"


def test_demo_underperformers(campaigns):
    ch = channel_performance(campaigns)
    weak = underperforming_channels(ch)
    assert "SMS" in weak and "Radio" in weak
    assert set(ch.index[:2]) == {"Email", "WhatsApp"}
    assert "Facebook" not in weak


def test_reallocation_demo(campaigns):
    plan = suggest_reallocation(channel_performance(campaigns))
    assert plan.best_channel == "Email"
    assert "SMS" in plan.underperforming
    assert plan.total_moved > 0 and plan.estimated_extra_revenue > 0
    assert all(m.to_channel == "Email" for m in plan.moves)
    assert all(m.reason for m in plan.moves)


def test_reallocation_toy(toy):
    plan = suggest_reallocation(channel_performance(toy))
    assert plan.underperforming == ["Bad"]
    assert plan.moves[0].amount == pytest.approx(50.0)
    assert plan.moves[0].estimated_extra_revenue == pytest.approx(50 * 4.0 - 50 * 0.5)
