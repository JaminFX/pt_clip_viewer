#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
trap 'echo; read -r -p "Press Return to close..."' EXIT
PYTHON="${PT_PYTHON:-/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14}"
if [ ! -x "$PYTHON" ]; then
    echo "Install Python 3.14 from python.org (macOS universal2 installer), or set PT_PYTHON."
    exit 1
fi
"$PYTHON" -m venv .venv-macos
.venv-macos/bin/python -m pip install --require-hashes -r requirements-build.lock
.venv-macos/bin/python verify_release.py
.venv-macos/bin/python verify_universal.py
.venv-macos/bin/python build_app.py
open release
