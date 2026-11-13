"""Generate a deterministic fictional SME dataset for demos and tests.

Usage: python scripts/make_demo_data.py [OUTPUT_DIR] [--seed N]

Produces (in OUTPUT_DIR, default ``demo_data``):
  sales.csv, products.csv, customers.csv, campaigns.csv, anomalies.json,
  documents/*.md (reports and meeting notes).

All data is fictional. The same seed always gives byte-identical files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

START = "2023-01-01"
END = "2024-12-31"
DEFAULT_SEED = 42

PRODUCTS = [
    ("P001", "Rice 25kg", "Food", 28.0, 21.0),
    ("P002", "Cooking oil 5L", "Food", 12.0, 9.0),
    ("P003", "Sugar 10kg", "Food", 14.0, 11.0),
    ("P004", "Soap pack", "Household", 6.0, 3.5),
    ("P005", "Detergent 2kg", "Household", 9.0, 6.0),
    ("P006", "LED lamp", "Electronics", 7.5, 4.0),
    ("P007", "Phone charger", "Electronics", 11.0, 6.0),
    ("P008", "School notebook x10", "Stationery", 5.0, 2.8),
    ("P009", "Solar lantern", "Electronics", 24.0, 15.0),
    ("P010", "Cotton fabric 5m", "Textile", 18.0, 11.0),
]
# Relative popularity; P009 is a deliberate "flop" and P001 a "top" product.
POPULARITY = [0.22, 0.16, 0.12, 0.12, 0.09, 0.08, 0.07, 0.07, 0.01, 0.06]
CHANNELS = ["Facebook", "Google Ads", "WhatsApp", "Email", "Radio", "SMS"]
CITIES = ["Kinshasa", "Lubumbashi", "Goma", "Kisangani", "Mbuji-Mayi"]

# Deliberate anomalies, recorded in anomalies.json for tests to find.
ANOMALIES = [
    {"start": "2023-06-14", "end": "2023-06-16", "kind": "drop", "factor": 0.1,
     "note": "system outage"},
    {"start": "2024-03-08", "end": "2024-03-08", "kind": "spike", "factor": 3.5,
     "note": "flash sale"},
    {"start": "2024-09-02", "end": "2024-09-04", "kind": "drop", "factor": 0.2,
     "note": "supplier strike"},
]


def _daily_multiplier(dates: pd.DatetimeIndex) -> np.ndarray:
    """Trend x yearly seasonality x weekly pattern x anomalies."""
    t = np.arange(len(dates)) / 365.0
    trend = 1.0 + 0.25 * t
    doy = dates.dayofyear.to_numpy()
    # Peak around December, dip around August.
    season = 1.0 + 0.35 * np.cos(2 * np.pi * (doy - 355) / 365.0)
    weekly = np.array([0.9, 0.85, 0.9, 1.0, 1.15, 1.35, 1.1])[dates.dayofweek.to_numpy()]
    mult = trend * season * weekly
    for a in ANOMALIES:
        mask = (dates >= a["start"]) & (dates <= a["end"])
        mult = np.where(mask, mult * a["factor"], mult)
    return mult


def _make_customers(rng: np.random.Generator, n: int = 400) -> pd.DataFrame:
    signup = pd.to_datetime(START) + pd.to_timedelta(rng.integers(0, 700, n), unit="D")
    return pd.DataFrame({
        "customer_id": [f"C{i:04d}" for i in range(1, n + 1)],
        "city": rng.choice(CITIES, n),
        "segment": rng.choice(["retail", "wholesale"], n, p=[0.8, 0.2]),
        "signup_date": signup.strftime("%Y-%m-%d"),
    })


def _make_sales(rng: np.random.Generator, customers: pd.DataFrame) -> pd.DataFrame:
    dates = pd.date_range(START, END, freq="D")
    counts = rng.poisson(18 * _daily_multiplier(dates))
    day_idx = np.repeat(np.arange(len(dates)), counts)
    n = len(day_idx)
    pids = rng.choice([p[0] for p in PRODUCTS], n, p=POPULARITY)
    price = {p[0]: p[3] for p in PRODUCTS}
    quantity = rng.integers(1, 6, n)
    unit_price = np.array([price[p] for p in pids])
    # Heavy buyers: a few customers account for many orders.
    weights = rng.pareto(1.5, len(customers)) + 1
    cust = rng.choice(customers["customer_id"], n, p=weights / weights.sum())
    return pd.DataFrame({
        "order_id": [f"O{i:06d}" for i in range(1, n + 1)],
        "date": dates[day_idx].strftime("%Y-%m-%d"),
        "customer_id": cust,
        "product_id": pids,
        "quantity": quantity,
        "unit_price": unit_price,
        "amount": np.round(quantity * unit_price, 2),
        "city": rng.choice(CITIES, n),
    })


def _make_products() -> pd.DataFrame:
    return pd.DataFrame(PRODUCTS, columns=["product_id", "name", "category", "price", "cost"])


def _make_campaigns(rng: np.random.Generator) -> pd.DataFrame:
    # (cost per click, click->conversion rate); SMS is deliberately poor.
    profile = {
        "Facebook": (0.30, 0.04), "Google Ads": (0.50, 0.06), "WhatsApp": (0.10, 0.09),
        "Email": (0.05, 0.05), "Radio": (0.80, 0.015), "SMS": (0.40, 0.004),
    }
    rows = []
    months = pd.date_range(START, END, freq="MS")
    for month in months:
        for ch in CHANNELS:
            cpc, conv_rate = profile[ch]
            spend = float(np.round(rng.uniform(300, 900), 2))
            clicks = int(spend / cpc * rng.uniform(0.9, 1.1))
            conversions = int(clicks * conv_rate * rng.uniform(0.85, 1.15))
            rows.append({
                "campaign_id": f"CMP-{month:%Y%m}-{ch[:3].upper()}",
                "channel": ch,
                "month": month.strftime("%Y-%m-%d"),
                "spend": spend,
                "impressions": clicks * int(rng.integers(20, 40)),
                "clicks": clicks,
                "conversions": conversions,
                "revenue": round(conversions * 45.0, 2),
            })
    return pd.DataFrame(rows)


def _write_documents(out: Path) -> None:
    docs = out / "documents"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "rapport_annuel_2023.md").write_text(
        "# Annual report 2023\n\nSales grew steadily through 2023 with a clear peak in "
        "November and December. Rice and cooking oil remain our best sellers. The solar "
        "lantern (P009) sells poorly and ties up stock. On 14-16 June an IT outage "
        "stopped almost all sales.\n\nMarketing: WhatsApp and Email give the best return; "
        "SMS campaigns convert very little.\n", encoding="utf-8")
    (docs / "reunion_2024_03.md").write_text(
        "# Meeting notes - March 2024\n\nA flash sale on 8 March tripled daily revenue. "
        "Decision: repeat a flash sale each quarter. Open question: reduce the SMS budget "
        "and move it to WhatsApp.\n", encoding="utf-8")
    (docs / "reunion_2024_09.md").write_text(
        "# Meeting notes - September 2024\n\nA supplier strike in early September caused "
        "stock-outs for 3 days. Action: find a second supplier for food products.\n",
        encoding="utf-8")


def generate_demo_data(out_dir: str | Path, seed: int = DEFAULT_SEED) -> dict[str, Path]:
    """Write the demo dataset into ``out_dir`` and return the created file paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    customers = _make_customers(rng)
    frames = {
        "customers": customers,
        "products": _make_products(),
        "sales": _make_sales(rng, customers),
        "campaigns": _make_campaigns(rng),
    }
    paths: dict[str, Path] = {}
    for name, df in frames.items():
        paths[name] = out / f"{name}.csv"
        df.to_csv(paths[name], index=False)
    paths["anomalies"] = out / "anomalies.json"
    paths["anomalies"].write_text(json.dumps(ANOMALIES, indent=2), encoding="utf-8")
    _write_documents(out)
    paths["documents"] = out / "documents"
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", nargs="?", default="demo_data")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    paths = generate_demo_data(args.output_dir, args.seed)
    print(f"Demo data written to {Path(args.output_dir).resolve()} ({len(paths)} items)")


if __name__ == "__main__":
    main()
