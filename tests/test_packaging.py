"""Packaging tests: packaged defaults, config seeding, install scripts, Dockerfile."""

from __future__ import annotations

from pathlib import Path

import pytest

from mide import config as cfg

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("name", cfg.CONFIG_FILES)
def test_packaged_defaults_match_repo_config(name: str) -> None:
    assert (cfg.PACKAGED_DEFAULTS_DIR / name).read_bytes() == (ROOT / "config" / name).read_bytes()


def test_seed_default_config_when_installed(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "config"
    monkeypatch.setattr(cfg, "DEFAULT_CONFIG_DIR", target)
    monkeypatch.setattr(cfg, "_REPO_CONFIG_DIR", tmp_path / "missing")
    cfg.seed_default_config(target)
    assert {p.name for p in target.iterdir()} == set(cfg.CONFIG_FILES)
    assert cfg.load_config(create_app_dir=False).sources.sources == []


def test_seed_does_not_overwrite(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "config"
    target.mkdir()
    (target / "sources.yaml").write_text("sources: [/x]\n", encoding="utf-8")
    monkeypatch.setattr(cfg, "DEFAULT_CONFIG_DIR", target)
    monkeypatch.setattr(cfg, "_REPO_CONFIG_DIR", tmp_path / "missing")
    cfg.seed_default_config(target)
    assert (target / "sources.yaml").read_text(encoding="utf-8") == "sources: [/x]\n"


def test_repo_checkout_config_is_never_seeded(tmp_path: Path) -> None:
    before = sorted(p.name for p in (ROOT / "config").iterdir())
    cfg.seed_default_config(cfg.DEFAULT_CONFIG_DIR)
    assert sorted(p.name for p in (ROOT / "config").iterdir()) == before


def test_packaging_files_exist() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "ENTRYPOINT" in dockerfile and "MIDE_HOME" in dockerfile
    for rel in ("scripts/install.sh", "scripts/install.ps1", "scripts/docker-entrypoint.sh"):
        assert (ROOT / rel).read_text(encoding="utf-8").strip()
    assert "package-data" in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
