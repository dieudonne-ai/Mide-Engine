import json

import pandas as pd

from mide.ingestion.catalog import build_catalog
from mide.ingestion.profiling import profile_dataframe
from tests.conftest import _load_demo_module


def test_files_created(demo_data):
    for key in ("sales", "products", "customers", "campaigns", "anomalies"):
        assert demo_data[key].exists()
    assert len(list(demo_data["documents"].glob("*.md"))) >= 3


def test_deterministic(tmp_path):
    mod = _load_demo_module()
    a = mod.generate_demo_data(tmp_path / "a", seed=7)
    b = mod.generate_demo_data(tmp_path / "b", seed=7)
    c = mod.generate_demo_data(tmp_path / "c", seed=8)
    assert a["sales"].read_bytes() == b["sales"].read_bytes()
    assert a["sales"].read_bytes() != c["sales"].read_bytes()


def test_two_years_and_integrity(demo_data):
    sales = pd.read_csv(demo_data["sales"])
    products = pd.read_csv(demo_data["products"])
    customers = pd.read_csv(demo_data["customers"])
    assert sales["date"].min() == "2023-01-01" and sales["date"].max() == "2024-12-31"
    assert set(sales["product_id"]) <= set(products["product_id"])
    assert set(sales["customer_id"]) <= set(customers["customer_id"])
    assert (sales["amount"] > 0).all()


def test_seasonality_and_trend(demo_data):
    sales = pd.read_csv(demo_data["sales"], parse_dates=["date"])
    monthly = sales.groupby(sales["date"].dt.month)["amount"].sum()
    assert monthly[12] > monthly[8]
    yearly = sales.groupby(sales["date"].dt.year)["amount"].sum()
    assert yearly[2024] > yearly[2023]


def test_anomalies_visible(demo_data):
    sales = pd.read_csv(demo_data["sales"])
    daily = sales.groupby("date")["amount"].sum()
    median = daily.median()
    for a in json.loads(demo_data["anomalies"].read_text()):
        value = daily.get(a["start"], 0)
        if a["kind"] == "spike":
            assert value > 2 * median
        else:
            assert value < 0.5 * median


def test_channels_and_flop_product(demo_data):
    camp = pd.read_csv(demo_data["campaigns"])
    roi = camp.groupby("channel").apply(
        lambda g: g["revenue"].sum() / g["spend"].sum(), include_groups=False)
    assert roi.idxmin() == "SMS"
    assert roi.loc["WhatsApp"] > 1
    sales = pd.read_csv(demo_data["sales"])
    by_product = sales.groupby("product_id")["amount"].sum()
    assert by_product.idxmin() == "P009"


def test_profiling_on_demo(demo_data):
    profile = profile_dataframe(pd.read_csv(demo_data["sales"]))
    kinds = {c.name: c.kind for c in profile.columns}
    assert kinds["date"] == "date"
    assert "amount" in profile.target_candidates


def test_catalog_on_demo(demo_data):
    entries = build_catalog([str(demo_data["sales"].parent / "sales.csv"),
                             str(demo_data["documents"])])
    assert len(entries) >= 4
