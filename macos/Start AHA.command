#!/bin/bash
# AHA — Artificial Human Assistant (macOS)
set -euo pipefail
cd "$(dirname "$0")"

fail() {
  echo ""
  echo "ERROR: $1"
  echo ""
  echo "Press Enter to close this window."
  read -r
  exit 1
}

echo "=========================================="
echo "  AHA — Artificial Human Assistant"
echo "=========================================="
echo ""

PY=""
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" &>/dev/null; then
    PY="$candidate"
    break
  fi
done
[[ -n "$PY" ]] || fail "Python 3 is not installed. Install Python 3.10+ from https://www.python.org/downloads/"

VER=$("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Using Python $VER ($PY)"

if [[ ! -d ".venv" ]]; then
  echo "[INFO] Creating virtual environment (first run)..."
  "$PY" -m venv .venv || fail "Could not create .venv"
fi

source .venv/bin/activate
python -m pip install --upgrade pip -q

echo "[INFO] Installing dependencies (first run may take 1–2 minutes)..."
pip install -q -r requirements.txt || fail "pip install failed"
pip install -q -e . || fail "Package install failed"

if lsof -ti :8000 &>/dev/null; then
  echo "[INFO] Stopping previous AHA server on port 8000..."
  lsof -ti :8000 | xargs kill -9 2>/dev/null || true
  sleep 1
fi

echo ""
echo "[INFO] Starting AHA..."
echo "[INFO] Keep this window open while you use the app."
echo ""

python app_webview.py
STATUS=$?

echo ""
if [[ $STATUS -ne 0 ]]; then
  echo "AHA exited with an error (code $STATUS)."
else
  echo "AHA has been closed."
fi
echo "Press Enter to close this window."
read -r
exit "$STATUS"
