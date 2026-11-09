#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
trap 'echo; read -r -p "Press Return to close..."' EXIT
PYTHON="${PT_PYTHON:-python3}"
if [ ! -x .venv-macos/bin/python ]; then
    "$PYTHON" -m venv .venv-macos
fi
.venv-macos/bin/python -m pip install --require-hashes -r requirements-runtime.lock
.venv-macos/bin/python pt_clip_viewer.py
