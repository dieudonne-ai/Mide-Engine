"""Static type check of the ``mide`` package (mypy, non-strict, see pyproject.toml)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_mide_package_passes_mypy() -> None:
    api = pytest.importorskip("mypy.api")
    stdout, stderr, status = api.run(
        ["--config-file", str(ROOT / "pyproject.toml"), str(ROOT / "mide")]
    )
    assert status == 0, f"mypy found type errors:\n{stdout}{stderr}"
