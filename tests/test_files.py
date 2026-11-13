"""Tests for the document connector."""

import logging

import pytest
from docx import Document
from pypdf import PdfWriter

from mide.connectors.base import SourceNotAuthorizedError
from mide.connectors.files import DocumentConnector, DocumentReadError


@pytest.fixture()
def docs(tmp_path):
    root = tmp_path / "docs"
    (root / "sub").mkdir(parents=True)
    (root / "note.txt").write_text("Réunion du lundi", encoding="utf-8")
    (root / "sub" / "plan.md").write_text("# Plan\nVentes", encoding="utf-8")
    (root / "latin.txt").write_bytes("café".encode("latin-1"))
    (root / "ignored.csv").write_text("a,b\n1,2\n")
    d = Document()
    d.add_paragraph("Rapport annuel")
    d.save(root / "report.docx")
    w = PdfWriter()
    w.add_blank_page(width=100, height=100)
    with (root / "blank.pdf").open("wb") as fh:
        w.write(fh)
    (root / "broken.docx").write_bytes(b"not a zip")
    (root / "broken.pdf").write_bytes(b"not a pdf")
    return root


def test_discover_recursive_and_filtered(docs):
    conn = DocumentConnector(str(docs), [str(docs)])
    names = {p.rsplit("/", 1)[-1] for p in conn.discover()}
    assert "plan.md" in names and "report.docx" in names
    assert "ignored.csv" not in names


def test_extension_filter(docs):
    conn = DocumentConnector(str(docs), [str(docs)], extensions={".md"})
    assert [p.rsplit("/", 1)[-1] for p in conn.discover()] == ["plan.md"]


def test_read_formats(docs):
    conn = DocumentConnector(str(docs), [str(docs)])
    assert "Réunion" in conn.read(str(docs / "note.txt"))
    assert conn.read(str(docs / "latin.txt")) == "café"
    assert "Rapport annuel" in conn.read(str(docs / "report.docx"))
    assert conn.read(str(docs / "blank.pdf")).strip() == ""


def test_max_size_skips_large_files(docs):
    (docs / "big.txt").write_bytes(b"x" * 2048)
    conn = DocumentConnector(str(docs), [str(docs)], max_file_size_mb=1 / 1024)
    assert not any(p.endswith("big.txt") for p in conn.discover())


def test_corrupted_files_are_skipped_with_log(docs, caplog):
    conn = DocumentConnector(str(docs), [str(docs)])
    with pytest.raises(DocumentReadError):
        conn.read(str(docs / "broken.docx"))
    with caplog.at_level(logging.WARNING, logger="mide.connectors.files"):
        result = conn.read_all()
    assert not any(k.endswith("broken.pdf") for k in result)
    assert any("corrupted" in r.message.lower() for r in caplog.records)
    assert any(k.endswith("report.docx") for k in result)


def test_unauthorized_file_refused(docs, tmp_path):
    other = tmp_path / "secret.txt"
    other.write_text("secret")
    conn = DocumentConnector(str(docs), [str(docs)])
    with pytest.raises(SourceNotAuthorizedError):
        conn.read(str(other))
    with pytest.raises(SourceNotAuthorizedError):
        DocumentConnector(str(tmp_path), [str(docs)])


def test_metadata(docs):
    meta = DocumentConnector(str(docs), [str(docs)]).metadata(str(docs / "note.txt"))
    assert meta["type"] == "txt" and meta["size_bytes"] > 0
