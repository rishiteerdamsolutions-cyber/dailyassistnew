#!/usr/bin/env bash
# Build AHA for release — macOS .app (run from this macos/ folder).
set -euo pipefail
cd "$(dirname "$0")"

echo "Building AHA for macOS release..."
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: Run this script on a Mac." >&2
  exit 1
fi

PY=""
for c in python3.12 python3.11 python3.10 python3; do
  command -v "$c" &>/dev/null && PY="$c" && break
done
[[ -n "$PY" ]] || { echo "Python 3.10+ required." >&2; exit 1; }

[[ -d .venv ]] || "$PY" -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt -e .
pip install -q nuitka ordered-set zstandard 2>/dev/null || pip install -q pyinstaller

if python -c "import nuitka" 2>/dev/null; then
  python -m nuitka \
    --standalone \
    --macos-create-app-bundle \
    --macos-app-name="AHA" \
    --output-dir=dist \
    --include-data-dir=web=web \
    --include-data-dir=VISIONBUTTONS=VISIONBUTTONS \
    --include-package=aha \
    --include-package=bol \
    --assume-yes-for-downloads \
    app_webview.py
  [[ -d dist/app_webview.app ]] && mv -f dist/app_webview.app dist/AHA.app
  echo "[OK] dist/AHA.app — double-click to run"
else
  echo "Nuitka not available; install with: pip install nuitka"
  exit 1
fi
