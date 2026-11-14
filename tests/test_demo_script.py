"""End-to-end test of scripts/demo.sh (no LLM, no network, isolated workspace)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "demo.sh"
BASH = shutil.which("bash")


def test_script_has_five_questions_and_all_steps() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    for command in ("make_demo_data.py", "sources add", "scan", "index", "train", "ask", "report"):
        assert command in text
    block = text.split("QUESTIONS=(")[1].split(")")[0]
    assert len([line for line in block.splitlines() if line.strip().startswith('"')]) == 5


@pytest.mark.skipif(BASH is None, reason="bash not available")
def test_demo_runs_end_to_end(tmp_path: Path) -> None:
    bin_dir = Path(sys.executable).parent
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "PYTHON": sys.executable,
        "MIDE_DEMO_SKIP_RAG": "1",
    }
    result = subprocess.run(
        [BASH, str(SCRIPT), str(tmp_path / "work")],
        capture_output=True, text=True, env=env, timeout=300, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Rapport hebdomadaire MIDE" in result.stdout
    assert "Demo finished" in result.stdout
    assert (tmp_path / "work" / "home").is_dir()
