#!/bin/sh
# Entrypoint: `demo` generates the fictional dataset and authorizes it; anything else goes to `mide`.
set -e
if [ "$1" = "demo" ]; then
    python /app/scripts/make_demo_data.py /workspace/demo_data
    mide sources add /workspace/demo_data
    mide scan
    exec mide report
fi
exec mide "$@"
