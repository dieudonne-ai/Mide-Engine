#!/usr/bin/env bash
# End-to-end MIDE demo: data -> consent -> scan -> index -> train -> 5 questions -> report.
# Runs without any intervention, in an isolated workspace (nothing touches ~/.mide or config/).
# Usage: ./scripts/demo.sh [workdir]
# Env:   MIDE_DEMO_SKIP_RAG=1  skip indexing (no `rag` extra / no embedding model available)
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${1:-$(mktemp -d)}"
PY="${PYTHON:-python3}"
export MIDE_HOME="$WORK/home"
CONFIG="$WORK/config"
mkdir -p "$MIDE_HOME" "$CONFIG"
cp "$ROOT"/config/*.yaml "$CONFIG"/
echo "sources: []" > "$CONFIG/sources.yaml"

MIDE=(mide)
command -v mide >/dev/null || MIDE=("$PY" -m mide.cli)
step() { printf '\n== %s ==\n' "$1"; }
# Optional steps (index, ask) must never stop the demo: report why and go on.
optional() { "$@" || echo "(skipped: step unavailable here - $1 $2 returned an error)"; }

step "1/7 Generate fictional business data"
"$PY" "$ROOT/scripts/make_demo_data.py" "$WORK/demo_data" || exit 1

step "2/7 Authorize the demo folder (explicit consent)"
"${MIDE[@]}" sources add "$WORK/demo_data" --config-dir "$CONFIG" || exit 1

step "3/7 Catalog of datasets"
"${MIDE[@]}" scan --config-dir "$CONFIG" || exit 1

step "4/7 Index documents"
if [ "${MIDE_DEMO_SKIP_RAG:-0}" = "1" ]; then
    echo "(skipped: MIDE_DEMO_SKIP_RAG=1)"
else
    optional "${MIDE[@]}" index --config-dir "$CONFIG"
fi

step "5/7 Train a model on the sales data"
"${MIDE[@]}" train --dataset sales --target amount --config-dir "$CONFIG" || exit 1

step "6/7 Five business questions"
QUESTIONS=(
    "Which products sell best?"
    "What is the sales forecast for the next weeks?"
    "Which customers are at risk of churn?"
    "Which marketing channel performs best?"
    "What are my 3 priority actions this week?"
)
for q in "${QUESTIONS[@]}"; do
    printf '\n> %s\n' "$q"
    optional "${MIDE[@]}" ask "$q" --config-dir "$CONFIG"
done

step "7/7 Weekly report"
"${MIDE[@]}" report --config-dir "$CONFIG" || exit 1

printf '\nDemo finished. Workspace: %s\n' "$WORK"
