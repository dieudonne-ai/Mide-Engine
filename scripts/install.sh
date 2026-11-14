#!/usr/bin/env bash
# Linux/macOS installer: creates a virtualenv in ~/.mide/venv and installs MIDE Engine.
# Usage: ./scripts/install.sh [extras]   (e.g. ./scripts/install.sh ui,llm,rag)
set -euo pipefail
EXTRAS="${1:-ui}"
HOME_DIR="${MIDE_HOME:-$HOME/.mide}"
command -v python3 >/dev/null || { echo "Python 3.11+ is required." >&2; exit 1; }
python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' \
    || { echo "Python 3.11+ is required." >&2; exit 1; }
mkdir -p "$HOME_DIR"
python3 -m venv "$HOME_DIR/venv"
"$HOME_DIR/venv/bin/pip" install --upgrade pip
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$HOME_DIR/venv/bin/pip" install "$ROOT[$EXTRAS]"
echo "Installed. Run: $HOME_DIR/venv/bin/mide doctor"
