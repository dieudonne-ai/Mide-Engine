"""Download of GGUF model weights (the only network access allowed, with confirmation)."""

from __future__ import annotations

import hashlib
import urllib.request
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, cast

from mide.config import LLMSpec

HF_URL = "https://huggingface.co/{repo}/resolve/main/{file}"
CHUNK_SIZE = 1024 * 1024

Opener = Callable[[str], AbstractContextManager[Any]]
ProgressCallback = Callable[[int, int | None], None]


class DownloadError(Exception):
    """Raised when a model download fails or the file fails verification."""


class DownloadDeclined(DownloadError):
    """Raised when the user does not confirm the download."""


@dataclass(frozen=True)
class ModelInfo:
    """A model file expected for a hardware profile."""

    profile: str
    repo: str
    file: str
    path: Path
    installed: bool
    size_bytes: int | None


def model_path(models_dir: Path, spec: LLMSpec) -> Path:
    """Return the local path of a model file (rejects path traversal in the file name)."""
    if Path(spec.file).name != spec.file:
        raise DownloadError(f"Invalid model file name: {spec.file}")
    return models_dir / spec.file


def model_url(spec: LLMSpec) -> str:
    return HF_URL.format(repo=spec.repo, file=spec.file)


def list_models(profiles: dict[str, Any], models_dir: Path) -> list[ModelInfo]:
    """List the models declared in ``models.yaml`` and whether they are installed."""
    infos = []
    for name, models in profiles.items():
        path = model_path(models_dir, models.llm)
        installed = path.is_file()
        infos.append(
            ModelInfo(
                profile=name,
                repo=models.llm.repo,
                file=models.llm.file,
                path=path,
                installed=installed,
                size_bytes=path.stat().st_size if installed else None,
            )
        )
    return infos


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def _default_opener(url: str) -> AbstractContextManager[Any]:
    return cast(AbstractContextManager[Any], urllib.request.urlopen(url, timeout=30))


def download_model(
    spec: LLMSpec,
    models_dir: Path,
    confirm: Callable[[str, int | None], bool],
    *,
    expected_sha256: str | None = None,
    expected_size: int | None = None,
    progress: ProgressCallback | None = None,
    opener: Opener | None = None,
) -> Path:
    """Download ``spec`` into ``models_dir`` after ``confirm`` returns True.

    ``confirm(url, size)`` is called before any download starts. The file is written to a
    ``.part`` file, verified (size and optional SHA-256) and then moved into place.
    """
    target = model_path(models_dir, spec)
    if target.is_file():
        return target
    url = model_url(spec)
    open_url = opener or _default_opener
    models_dir.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    try:
        with open_url(url) as response:
            length = response.headers.get("Content-Length")
            total = int(length) if length else None
            if not confirm(url, total):
                raise DownloadDeclined("Download not confirmed.")
            done = 0
            with part.open("wb") as out:
                out_file = cast(BinaryIO, out)
                while block := response.read(CHUNK_SIZE):
                    out_file.write(block)
                    done += len(block)
                    if progress:
                        progress(done, total)
        size = part.stat().st_size
        if total is not None and size != total:
            raise DownloadError(f"Incomplete download: {size} of {total} bytes.")
        if expected_size is not None and size != expected_size:
            raise DownloadError(f"Unexpected size: {size} bytes, expected {expected_size}.")
        if expected_sha256 and sha256_of(part) != expected_sha256.lower():
            raise DownloadError("SHA-256 mismatch: the downloaded file is corrupted.")
        part.replace(target)
    except DownloadError:
        part.unlink(missing_ok=True)
        raise
    except OSError as exc:
        part.unlink(missing_ok=True)
        raise DownloadError(f"Download failed: {exc}") from exc
    return target
