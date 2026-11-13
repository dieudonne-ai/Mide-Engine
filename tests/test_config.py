from pathlib import Path

import pytest

from mide.config import ConfigError, load_config
from mide.utils.paths import app_dir


@pytest.fixture(autouse=True)
def mide_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home" / ".mide"
    monkeypatch.setenv("MIDE_HOME", str(home))
    return home


def test_defaults_from_repo_config(mide_home: Path) -> None:
    cfg = load_config()
    assert cfg.language == "fr"
    assert cfg.sources.sources == []
    assert set(cfg.models.profiles) == {"tiny", "small", "medium", "large"}
    assert cfg.models.profiles["tiny"].lora is False
    assert cfg.app_dir == mide_home


def test_app_dir_created(mide_home: Path) -> None:
    assert not mide_home.exists()
    app_dir()
    assert (mide_home / "models").is_dir()
    assert (mide_home / "index").is_dir()


def test_missing_files_use_defaults(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "empty")
    assert cfg.language == "fr"
    assert cfg.models.profiles == {}


def test_language_en(tmp_path: Path) -> None:
    (tmp_path / "default.yaml").write_text("language: en\n")
    assert load_config(tmp_path).language == "en"


def test_invalid_language_gives_clear_error(tmp_path: Path) -> None:
    (tmp_path / "default.yaml").write_text("language: de\n")
    with pytest.raises(ConfigError, match="default.yaml.*language"):
        load_config(tmp_path)


def test_unknown_key_rejected(tmp_path: Path) -> None:
    (tmp_path / "default.yaml").write_text("lang: fr\n")
    with pytest.raises(ConfigError, match="lang"):
        load_config(tmp_path)


def test_broken_yaml(tmp_path: Path) -> None:
    (tmp_path / "sources.yaml").write_text("sources: [unclosed\n")
    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_config(tmp_path)


def test_invalid_models(tmp_path: Path) -> None:
    (tmp_path / "models.yaml").write_text("profiles:\n  tiny:\n    embeddings: x\n")
    with pytest.raises(ConfigError, match="llm"):
        load_config(tmp_path)
