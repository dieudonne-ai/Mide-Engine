"""The README must document every CLI command and stay bilingual."""

from pathlib import Path

from typer.main import get_command

from mide.cli import app

README = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")


def test_every_command_is_documented() -> None:
    for name in get_command(app).commands:  # type: ignore[attr-defined]
        assert f"mide {name}" in README, name


def test_bilingual_sections() -> None:
    for heading in ("## English", "## Français", "### Privacy FAQ", "### FAQ confidentialité"):
        assert heading in README


def test_quick_start_steps() -> None:
    for step in ("make_demo_data.py", "mide sources add demo_data", "mide scan", "mide report"):
        assert step in README
