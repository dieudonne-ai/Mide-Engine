"""Tests for the CSV / Excel connector."""

from pathlib import Path

import pandas as pd
import pytest

from mide.connectors.base import SourceNotAuthorizedError
from mide.connectors.tabular import TabularConnector

DATA = pd.DataFrame({"produit": ["café", "thé", "été"], "montant": [1.5, 2.25, 3.0]})


def make(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


def conn(folder: Path) -> TabularConnector:
    return TabularConnector(str(folder), [str(folder)])


@pytest.mark.parametrize("sep", [",", ";"])
@pytest.mark.parametrize("encoding", ["utf-8", "latin-1"])
def test_csv_separator_and_encoding(tmp_path: Path, sep: str, encoding: str) -> None:
    folder = make(tmp_path)
    f = folder / "ventes.csv"
    text = DATA.to_csv(index=False, sep=sep, decimal="," if sep == ";" else ".")
    f.write_bytes(text.encode(encoding))
    c = conn(folder)
    df = c.read(str(f))
    assert list(df.columns) == ["produit", "montant"]
    assert df["produit"].tolist() == ["café", "thé", "été"]
    assert len(df) == 3
    assert c.metadata(str(f))["separator"] == sep


def test_utf8_bom(tmp_path: Path) -> None:
    folder = make(tmp_path)
    f = folder / "bom.csv"
    f.write_bytes(b"\xef\xbb\xbf" + DATA.to_csv(index=False).encode("utf-8"))
    assert list(conn(folder).read(str(f)).columns) == ["produit", "montant"]


def test_excel_all_sheets(tmp_path: Path) -> None:
    folder = make(tmp_path)
    f = folder / "book.xlsx"
    with pd.ExcelWriter(f) as w:
        DATA.to_excel(w, sheet_name="Ventes", index=False)
        DATA.head(1).to_excel(w, sheet_name="Clients", index=False)
    c = conn(folder)
    items = c.discover()
    assert len(items) == 2
    by_sheet = {i.split("::")[1]: c.read(i) for i in items}
    assert set(by_sheet) == {"Ventes", "Clients"}
    assert len(by_sheet["Ventes"]) == 3 and len(by_sheet["Clients"]) == 1
    meta = c.metadata(items[0])
    assert meta["type"] == "excel" and meta["rows"] in (1, 3) and "sheet" in meta


def test_discover_ignores_unsupported(tmp_path: Path) -> None:
    folder = make(tmp_path)
    (folder / "a.csv").write_text("x,y\n1,2\n")
    (folder / "b.pdf").write_bytes(b"%PDF")
    assert [Path(i).name for i in conn(folder).discover()] == ["a.csv"]


def test_unauthorized_file_refused(tmp_path: Path) -> None:
    folder = make(tmp_path)
    outside = tmp_path / "secret.csv"
    outside.write_text("a,b\n1,2\n")
    with pytest.raises(SourceNotAuthorizedError):
        TabularConnector(str(outside), [str(folder)])
    with pytest.raises(SourceNotAuthorizedError):
        conn(folder).read(str(outside))


def test_read_only(tmp_path: Path) -> None:
    folder = make(tmp_path)
    f = folder / "a.csv"
    f.write_text("x;y\n1;2\n")
    before = f.read_bytes()
    conn(folder).read(str(f))
    assert f.read_bytes() == before
