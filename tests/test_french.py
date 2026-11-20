import re
from datetime import date

import pytest

from mide import cli
from mide.utils.errors import MESSAGES, friendly_message
from mide.utils.french import NBSP, french_date, french_spacing

_PLAIN_SPACE_BEFORE_SIGN = re.compile(r" [:;?!](?:\s|$|[\"'`)])")


@pytest.mark.parametrize(("text", "expected"), [
    ("Erreur : {value}", f"Erreur{NBSP}: {{value}}"),
    ("trop peu ({n}) ; il en faut 20", "trop peu ({n})\u00a0; il en faut 20"),
    ("Télécharger {url} depuis internet ?", "Télécharger {url} depuis internet\u00a0?"),
    ("Exemple : mide ask \"Quoi ?\"", "Exemple\u00a0: mide ask \"Quoi\u00a0?\""),
    ("Fin :", "Fin\u00a0:"),
])
def test_french_spacing_makes_space_before_sign_non_breaking(text: str, expected: str) -> None:
    assert french_spacing(text) == expected


@pytest.mark.parametrize("text", [
    "10:30", "http://host/db", "ratio 3:2", "C:\\data", "Error: x", "a?b", "déjà\u00a0: ok", "",
])
def test_french_spacing_leaves_other_text_untouched(text: str) -> None:
    assert french_spacing(text) == text


def test_every_french_cli_template_has_non_breaking_spaces() -> None:
    # Every French CLI and error template renders without an ordinary space before ':', ';',
    # '?' or '!'; the English templates are unchanged and have none to begin with.
    for key, texts in cli.SOURCES_MESSAGES.items():
        assert not _PLAIN_SPACE_BEFORE_SIGN.search(french_spacing(texts["fr"])), key
        assert not _PLAIN_SPACE_BEFORE_SIGN.search(texts["en"]), key
    for key, texts in MESSAGES.items():
        assert not _PLAIN_SPACE_BEFORE_SIGN.search(texts["en"]), key


def test_sources_msg_uses_non_breaking_space_in_french_only() -> None:
    assert cli._sources_msg("error", "fr", value="x") == "Erreur\u00a0: x"
    assert cli._sources_msg("error", "en", value="x") == "Error: x"
    # Values are not reformatted (only the template is).
    assert cli._sources_msg("added", "fr", value="a : b") == "Source ajoutée\u00a0: a : b"


def test_friendly_message_uses_non_breaking_space_in_french_only() -> None:
    exc = FileNotFoundError(2, "No such file", "ventes.csv")
    assert friendly_message(exc, "fr").startswith("Fichier ou dossier introuvable\u00a0: ventes.csv")
    assert friendly_message(exc, "en").startswith("File or folder not found: ventes.csv")


def test_cli_french_output_has_no_plain_space_before_sign(tmp_path, monkeypatch) -> None:
    # `sources list`, `privacy`, an unknown `sources remove` and an empty `ask` in French have
    # no ordinary space before ':', ';' or '?'; English output keeps "Error: " etc.
    from typer.testing import CliRunner

    runner = CliRunner()
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    data = tmp_path / "data"
    data.mkdir()
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "sources.yaml").write_text(f"sources:\n  - {data}\n", encoding="utf-8")
    commands = [["sources", "list"], ["privacy"], ["sources", "remove", str(tmp_path / "nope")],
                ["ask", " "]]
    for language in ("fr", "en"):
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        outputs = []
        for command in commands:
            result = runner.invoke(cli.app, [*command, "--config-dir", str(cfg)])
            outputs.append(result.output)
        text = "\n".join(outputs).replace(str(tmp_path), "PATH")
        if language == "fr":
            assert not _PLAIN_SPACE_BEFORE_SIGN.search(text), text
            assert "Sources autorisées\u00a0:" in text and "Erreur\u00a0:" in text
        else:
            assert "\u00a0" not in text, text
            assert "Authorized sources:" in text and "Error:" in text


@pytest.mark.parametrize(("day", "expected"), [
    (date(2024, 10, 2), "2 octobre 2024"),
    (date(2024, 10, 1), "1er octobre 2024"),
    (date(2026, 2, 28), "28 février 2026"),
    (date(2025, 8, 15), "15 août 2025"),
])
def test_french_date(day, expected):
    assert french_date(day) == expected
