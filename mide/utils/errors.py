"""Clear, bilingual (FR/EN) messages for common user-facing errors."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from mide.utils.french import french_spacing


class MissingDependencyError(Exception):
    """An optional dependency is missing; ``extra`` is the ``mide-engine[extra]`` that installs it."""

    def __init__(self, package: str, extra: str) -> None:
        super().__init__(
            f"{package} is not installed. Install it with `pip install mide-engine[{extra}]`."
        )
        self.package = package
        self.extra = extra


MESSAGES: dict[str, dict[str, str]] = {
    "missing_dependency": {
        "fr": "{package} n'est pas installé. Installez-le avec `pip install mide-engine[{extra}]`.",
        "en": "{package} is not installed. Install it with `pip install mide-engine[{extra}]`.",
    },
    "not_found": {
        "fr": "Fichier ou dossier introuvable : {detail}. Vérifiez le chemin.",
        "en": "File or folder not found: {detail}. Check the path.",
    },
    "permission": {
        "fr": "Accès refusé : {detail}. Vérifiez les droits de lecture.",
        "en": "Permission denied: {detail}. Check read permissions.",
    },
    "encoding": {
        "fr": "Encodage illisible dans le fichier. Enregistrez-le en UTF-8 ou Latin-1.",
        "en": "Unreadable file encoding. Save the file as UTF-8 or Latin-1.",
    },
    "empty": {
        "fr": "Le fichier est vide ou ne contient aucune colonne exploitable.",
        "en": "The file is empty or has no usable column.",
    },
    "parse": {
        "fr": "Le fichier est mal formé (séparateur ou lignes incohérents) : {detail}",
        "en": "The file is malformed (inconsistent separator or rows): {detail}",
    },
    "memory": {
        "fr": "Mémoire insuffisante. Fermez d'autres applications ou utilisez un fichier plus petit.",
        "en": "Not enough memory. Close other applications or use a smaller file.",
    },
    "network": {
        "fr": "Réseau indisponible. MIDE n'en a besoin que pour télécharger un modèle.",
        "en": "Network unavailable. MIDE only needs it to download a model.",
    },
    "unknown": {
        "fr": "Erreur inattendue : {detail}",
        "en": "Unexpected error: {detail}",
    },
}


def classify(exc: BaseException) -> str:
    """Map an exception to a message key."""
    import pandas.errors as pde

    if isinstance(exc, MissingDependencyError):
        return "missing_dependency"
    if isinstance(exc, FileNotFoundError):
        return "not_found"
    if isinstance(exc, PermissionError):
        return "permission"
    if isinstance(exc, UnicodeError):
        return "encoding"
    if isinstance(exc, pde.EmptyDataError):
        return "empty"
    if isinstance(exc, pde.ParserError):
        return "parse"
    if isinstance(exc, MemoryError):
        return "memory"
    if isinstance(exc, ConnectionError):
        return "network"
    return "unknown"


def friendly_message(exc: BaseException, language: str = "fr") -> str:
    """Return a short, actionable message in ``language`` (``fr`` or ``en``)."""
    lang = language if language in ("fr", "en") else "fr"
    detail = getattr(exc, "filename", None) or str(exc) or type(exc).__name__
    template = MESSAGES[classify(exc)][lang]
    if lang == "fr":
        template = french_spacing(template)
    return template.format(
        detail=detail,
        package=getattr(exc, "package", ""),
        extra=getattr(exc, "extra", ""),
    )


def run_safely(func: Callable[[], Any], language: str = "fr") -> int:
    """Run ``func``; print a friendly error and return exit code 1 on failure."""
    try:
        func()
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as exc:  # noqa: BLE001 - last-resort handler for the CLI
        prefix = "Error: " if language == "en" else "Erreur : "
        print(f"{prefix}{friendly_message(exc, language)}", file=sys.stderr)
        return 1
    return 0
