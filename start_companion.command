#!/bin/bash
# Start AHA desktop companion (dev checkout).
set -euo pipefail
cd "$(dirname "$0")"

echo "Starting AHA — Artificial Human Assistant..."

if [[ ! -x .venv/bin/python ]]; then
  echo ""
  echo "ERROR: .venv not found."
  echo "  python3 -m venv .venv"
  echo "  .venv/bin/pip install -r requirements.txt"
  exit 1
fi

# Stop a stale server on 8000 so this checkout owns the port + session token.
if lsof -ti :8000 >/dev/null 2>&1; then
  echo "Stopping previous server on port 8000..."
  lsof -ti :8000 | xargs kill -9 2>/dev/null || true
  sleep 1
fi

# Local dev: skip Google sign-in + unlock agent APIs (never enable in production).
export AHA_ALLOW_DEV_LICENSE=1
export AHA_DEV_OPEN_GATES=1
export AHA_WEBVIEW_DEBUG=1

.venv/bin/python - <<'PY'
from aha.env_loader import load_dotenv
load_dotenv()
from aha.license import activate_license
r = activate_license("AHA-LOCAL-DEV-1234")
print("Dev license:", "OK" if r.get("valid") else r)
PY

echo ""
echo "Companion URL: http://127.0.0.1:8000/companion"
echo "If the window is blank, open that URL in Chrome to compare."
echo ""

exec .venv/bin/python app_webview.py
