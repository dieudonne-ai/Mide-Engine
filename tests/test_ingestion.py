import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from typer.testing import CliRunner

from mide.cli import app
from mide.connectors.sources import add_source
from mide.ingestion.catalog import build_catalog
from mide.ingestion.profiling import profile_dataframe

runner = CliRunner()


def _sales_df() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = 60
    return pd.DataFrame(
        {
            "order_id": range(1, n + 1),
            "date": pd.date_range("2024-01-01", periods=n).strftime("%Y-%m-%d"),
            "product": rng.choice(["A", "B", "C"], n),
            "montant": rng.uniform(10, 500, n).round(2),
            "quantity": rng.integers(1, 10, n),
            "note": [None if i % 4 == 0 else "ok" for i in range(n)],
        }
    )


def test_profile_detects_dates_and_targets() -> None:
    profile = profile_dataframe(_sales_df())
    assert profile.rows == 60
    assert profile.date_columns == ["date"]
    assert set(profile.target_candidates) == {"montant", "quantity"}
    by_name = {c.name: c for c in profile.columns}
    assert by_name["order_id"].is_target_candidate is False
    assert by_name["product"].kind == "categorical"
    assert by_name["note"].missing_pct == 25.0


def test_numeric_strings_are_not_dates() -> None:
    df = pd.DataFrame({"code": ["1500", "2300", "1800"] * 5})
    assert profile_dataframe(df).date_columns == []


def test_native_datetime_column() -> None:
    df = pd.DataFrame({"d": pd.date_range("2024-01-01", periods=5)})
    assert profile_dataframe(df).date_columns == ["d"]


def test_catalog_all_source_types(tmp_path: Path) -> None:
    folder = tmp_path / "data"
    folder.mkdir()
    _sales_df().to_csv(folder / "ventes.csv", index=False)
    (folder / "notes.txt").write_text("Meeting notes", encoding="utf-8")
    db = tmp_path / "shop.db"
    with sqlite3.connect(db) as conn:
        _sales_df().to_sql("orders", conn, index=False)
    url = f"sqlite:///{db}"
    entries = build_catalog([str(folder), url])
    kinds = {e.kind for e in entries}
    assert kinds == {"csv", "document", "sql"}
    csv_entry = next(e for e in entries if e.kind == "csv")
    assert csv_entry.rows == 60 and csv_entry.profile is not None
    assert csv_entry.profile.date_columns == ["date"]
    sql_entry = next(e for e in entries if e.kind == "sql")
    assert sql_entry.item == "orders" and sql_entry.rows == 60


def test_catalog_ignores_unlisted_folders(tmp_path: Path) -> None:
    other = tmp_path / "other"
    other.mkdir()
    _sales_df().to_csv(other / "secret.csv", index=False)
    assert build_catalog([]) == []


def test_catalog_reports_unreadable_file(tmp_path: Path) -> None:
    (tmp_path / "bad.xlsx").write_bytes(b"not an excel file")
    entries = build_catalog([str(tmp_path)])
    assert any(e.error for e in entries)


def test_scan_cli(tmp_path: Path) -> None:
    cfg = tmp_path / "config"
    cfg.mkdir()
    data = tmp_path / "data"
    data.mkdir()
    _sales_df().to_csv(data / "ventes.csv", index=False)
    add_source(str(data), cfg)
    result = runner.invoke(app, ["scan", "--config-dir", str(cfg)])
    assert result.exit_code == 0
    assert "ventes.csv" in result.output
    assert "date columns: date" in result.output
    assert "montant" in result.output
