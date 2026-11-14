import logging
import socket

import pytest
from typer.testing import CliRunner

from mide import cli
from mide.llm.runtime import FakeLLM
from mide.utils.privacy import _mask


@pytest.fixture
def env(tmp_path, monkeypatch, demo_data):
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    (cfg_dir / "sources.yaml").write_text(
        f"sources:\n  - {demo_data['campaigns']}\n  - {demo_data['sales']}\n")
    return cfg_dir


def test_ask_makes_no_network_access(env, monkeypatch):
    """Any socket use during `mide ask` fails the test."""
    def blocked(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    monkeypatch.setattr(cli, "_get_llm", lambda cfg: FakeLLM("ok"))
    res = CliRunner().invoke(cli.app, ["ask", "Quel canal marketing a le meilleur ROI ?",
                                       "--config-dir", str(env)])
    assert res.exit_code == 0, res.output


def test_privacy_command_lists_sources_and_storage(env, demo_data):
    res = CliRunner().invoke(cli.app, ["privacy", "--config-dir", str(env)])
    assert res.exit_code == 0, res.output
    assert str(demo_data["sales"]) in res.output
    assert "aucune télémétrie" in res.output.lower()
    assert "models_trained" in res.output


def test_privacy_masks_database_credentials():
    assert _mask("postgresql://user:secret@host/db") == "postgresql://***@host/db"
    assert "secret" not in _mask("mysql://u:secret@h/d")


def test_failing_dataset_logs_no_data(env, monkeypatch, caplog):
    """Log lines carry the exception type only, never its message (may hold row data)."""
    from mide.connectors.tabular import TabularConnector

    def boom(self, item, nrows=None):
        raise ValueError("CONFIDENTIAL-ROW-DATA")

    monkeypatch.setattr(TabularConnector, "read", boom)
    with caplog.at_level(logging.DEBUG):
        cli._load_all_datasets(cli.list_sources(env))
    assert "CONFIDENTIAL-ROW-DATA" not in caplog.text
    assert "ValueError" in caplog.text


def test_sources_respected(env, tmp_path, monkeypatch):
    """Only listed sources are read; an unlisted file next to them is never touched."""
    (tmp_path / "secret.csv").write_text("a\n1\n")
    frames = cli._load_all_datasets(cli.list_sources(env))
    assert not any("secret" in str(k) for k in frames)
