import hashlib
from pathlib import Path
from typing import Self

import pytest
from typer.testing import CliRunner

from mide import cli
from mide.config import LLMSpec, ProfileModels
from mide.llm import downloader
from mide.llm.downloader import DownloadDeclined, DownloadError, download_model, list_models

SPEC = LLMSpec(repo="org/model", file="m.gguf")
DATA = b"x" * 2500


class FakeResponse:
    def __init__(self, data: bytes, length: int | None = None) -> None:
        self._data = data
        self.pos = 0
        n = len(data) if length is None else length
        self.headers = {"Content-Length": str(n)}

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *a: object) -> None:
        return None

    def read(self, n: int) -> bytes:
        chunk = self._data[self.pos : self.pos + n]
        self.pos += len(chunk)
        return chunk


def opener_for(data: bytes, length: int | None = None, calls: list[str] | None = None):
    def _open(url: str) -> FakeResponse:
        if calls is not None:
            calls.append(url)
        return FakeResponse(data, length)

    return _open


def test_download_ok(tmp_path: Path) -> None:
    seen: list[tuple[int, int | None]] = []
    path = download_model(
        SPEC,
        tmp_path,
        lambda u, s: True,
        expected_sha256=hashlib.sha256(DATA).hexdigest(),
        progress=lambda d, t: seen.append((d, t)),
        opener=opener_for(DATA),
    )
    assert path.read_bytes() == DATA
    assert seen[-1] == (len(DATA), len(DATA))
    assert not list(tmp_path.glob("*.part"))


def test_declined_writes_nothing(tmp_path: Path) -> None:
    with pytest.raises(DownloadDeclined):
        download_model(SPEC, tmp_path, lambda u, s: False, opener=opener_for(DATA))
    assert list(tmp_path.iterdir()) == []


def test_existing_file_not_downloaded(tmp_path: Path) -> None:
    (tmp_path / "m.gguf").write_bytes(b"old")
    calls: list[str] = []
    download_model(SPEC, tmp_path, lambda u, s: True, opener=opener_for(DATA, calls=calls))
    assert calls == []


def test_hash_mismatch_cleans_up(tmp_path: Path) -> None:
    with pytest.raises(DownloadError, match="SHA-256"):
        download_model(
            SPEC, tmp_path, lambda u, s: True, expected_sha256="0" * 64, opener=opener_for(DATA)
        )
    assert list(tmp_path.iterdir()) == []


def test_incomplete_download(tmp_path: Path) -> None:
    with pytest.raises(DownloadError, match="Incomplete"):
        download_model(
            SPEC, tmp_path, lambda u, s: True, opener=opener_for(DATA, length=len(DATA) + 10)
        )
    assert list(tmp_path.iterdir()) == []


def test_path_traversal_rejected(tmp_path: Path) -> None:
    with pytest.raises(DownloadError):
        download_model(
            LLMSpec(repo="a/b", file="../evil.gguf"),
            tmp_path,
            lambda u, s: True,
            opener=opener_for(DATA),
        )


def test_list_models(tmp_path: Path) -> None:
    (tmp_path / "m.gguf").write_bytes(b"abc")
    profiles = {
        "tiny": ProfileModels(llm=SPEC, embeddings="e"),
    }
    infos = list_models(profiles, tmp_path)
    assert infos[0].installed and infos[0].size_bytes == 3


def _cfg(tmp_path: Path) -> Path:
    cdir = tmp_path / "config"
    cdir.mkdir()
    (cdir / "models.yaml").write_text(
        "profiles:\n  tiny:\n    llm: {repo: org/model, file: m.gguf}\n    embeddings: e\n"
    )
    return cdir


def test_cli_pull_requires_confirmation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    calls: list[str] = []
    monkeypatch.setattr(downloader, "_default_opener", opener_for(DATA, calls=calls))
    runner = CliRunner()
    args = ["models", "pull", "--profile", "tiny", "--config-dir", str(_cfg(tmp_path))]
    result = runner.invoke(cli.app, args, input="n\n")
    assert result.exit_code == 1
    assert not (tmp_path / "home" / "models" / "m.gguf").exists()
    result = runner.invoke(cli.app, [*args, "--yes"])
    assert result.exit_code == 0
    assert (tmp_path / "home" / "models" / "m.gguf").read_bytes() == DATA
    listing = runner.invoke(
        cli.app, ["models", "list", "--config-dir", str(_cfg_dir := tmp_path / "config")]
    )
    assert "[installed]" in listing.output and _cfg_dir.exists()
