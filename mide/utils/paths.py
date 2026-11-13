"""Application data paths (``~/.mide`` by default)."""

from __future__ import annotations

import os
from pathlib import Path

HOME_ENV = "MIDE_HOME"
SUBDIRS = ("models", "index", "models_trained")


def app_dir(create: bool = True) -> Path:
    """Return the application data folder, creating it (and subfolders) if needed.

    The location can be overridden with the ``MIDE_HOME`` environment variable.
    """
    root = Path(os.environ.get(HOME_ENV) or Path.home() / ".mide").expanduser()
    if create:
        root.mkdir(parents=True, exist_ok=True)
        for name in SUBDIRS:
            (root / name).mkdir(exist_ok=True)
    return root
