import pandas as pd
import pytest

from mide.business.customers import (
    churn_risk,
    customer_table,
    rfm_segments,
    segment_summary,
)


@pytest.fixture
def sales(demo_data):
    return pd.read_csv(demo_data["sales"])


@pytest.fixture
def toy():
    rows = []
    # A: frequent, recent, big spender. B: one old small order. C: used to buy weekly, gone.
    for d in pd.date_range("2024-01-01", "2024-12-30", freq="7D"):
        rows.append(("A", d, 100.0))
    rows.append(("B", pd.Timestamp("2024-01-05"), 5.0))
    for d in pd.date_range("2024-01-01", "2024-03-01", freq="7D"):
        rows.append(("C", d, 20.0))
    rows.append(("D", pd.Timestamp("2024-12-31"), 10.0))
    df = pd.DataFrame(rows, columns=["customer_id", "date", "amount"])
    df["order_id"] = range(len(df))
    return df


def test_customer_table_values(toy):
    t = customer_table(toy)
    assert t.loc["A", "frequency"] == 53
    assert t.loc["A", "recency_days"] == 1
    assert t.loc["B", "recency_days"] == (pd.Timestamp("2024-12-31") - pd.Timestamp("2024-01-05")).days
    assert t.loc["C", "typical_gap_days"] == pytest.approx(7.0)
    assert pd.isna(t.loc["B", "typical_gap_days"])
    assert t["monetary"].sum() == pytest.approx(toy["amount"].sum())


def test_rfm_segments_are_coherent(toy):
    rfm = rfm_segments(toy)
    assert rfm.loc["A", "segment"] == "Champions"
    assert rfm.loc["B", "segment"] in {"Hibernating", "Needs attention"}
    assert rfm.loc["D", "r_score"] == 5
    assert rfm[["r_score", "f_score", "m_score"]].min().min() >= 1
    assert rfm[["r_score", "f_score", "m_score"]].max().max() <= 5


def test_churn_orders_customers(toy):
    report = churn_risk(toy)
    s = report.scores["risk"]
    assert s["C"] > 0.9 > s["A"]
    assert s["A"] < 0.1
    assert "C" in report.high_risk
    assert report.revenue_at_risk >= toy[toy.customer_id == "C"]["amount"].sum()
    assert ((s >= 0) & (s <= 1)).all()


def test_demo_segments(sales):
    rfm = rfm_segments(sales)
    assert len(rfm) == sales["customer_id"].nunique()
    summary = segment_summary(rfm)
    assert summary["revenue_share_pct"].sum() == pytest.approx(100, abs=0.5)
    # Top-scoring group should out-earn the bottom group per customer.
    top = rfm[rfm.segment == "Champions"]["monetary"].mean()
    low = rfm[rfm.segment.isin(["Hibernating", "At risk"])]["monetary"].mean()
    assert top > low


def test_demo_churn_report(sales):
    report = churn_risk(sales)
    assert len(report.scores) == sales["customer_id"].nunique()
    assert report.notes and report.revenue_at_risk >= 0


def test_empty_input_raises():
    with pytest.raises(ValueError):
        customer_table(pd.DataFrame({"customer_id": [], "date": [], "amount": []}))
