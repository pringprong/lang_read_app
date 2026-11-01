#!/usr/bin/env bash
# Build the LangRead desktop app with PyInstaller (Linux).
# On Windows, run the equivalent command in PowerShell (see README.md).
set -euo pipefail
cd "$(dirname "$0")/.."

VENV=".venv"
if [ ! -x "$VENV/bin/pyinstaller" ]; then
    echo "Installing PyInstaller…"
    "$VENV/bin/pip" install pyinstaller
fi

echo "Building LangRead…"
"$VENV/bin/pyinstaller" \
    --noconfirm \
    --name LangRead \
    --windowed \
    --collect-data langread \
    src/langread/main.py

echo ""
echo "Build complete: dist/LangRead/"
echo "Smoke test:  QT_QPA_PLATFORM=offscreen LANGREAD_DATA_DIR=/tmp/langread-smoke dist/LangRead/LangRead --smoke-test && echo OK"
