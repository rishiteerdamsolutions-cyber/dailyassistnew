#!/usr/bin/env bash
# Open local dev gates: skip Firebase sign-in + license checks for agent work.
# NEVER set these on Vercel or in customer retail builds.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ROOT}/.env"
DEV_KEY="AHA-LOCAL-DEV-1234"

ensure_env_var() {
  local key="$1"
  local value="$2"
  if [[ -f "$ENV_FILE" ]] && grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    return 0
  fi
  echo "${key}=${value}" >> "$ENV_FILE"
  echo "[OK] Added ${key} to .env"
}

ensure_env_var "AHA_ALLOW_DEV_LICENSE" "1"
ensure_env_var "AHA_DEV_OPEN_GATES" "1"

if [[ ! -d ".venv" ]]; then
  echo "[INFO] Creating .venv..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate

if ! python -c "import server" >/dev/null 2>&1; then
  echo "[INFO] Installing dependencies (requires Python 3.10+)..."
  pip install -q -r requirements.txt -e .
fi

python - <<PY
from aha.env_loader import load_dotenv
load_dotenv()
from aha.license import activate_license
result = activate_license("${DEV_KEY}")
print("[OK] Dev license:", result)
PY

echo ""
echo "=========================================="
echo "  AHA dev gates OPEN (local only)"
echo "  - No Google sign-in required"
echo "  - Agent / orchestrator APIs unlocked"
echo "  - Dev license: ${DEV_KEY}"
echo "=========================================="
echo ""
echo "Starting server → http://127.0.0.1:8000/companion"
echo "Press Ctrl+C to stop."
echo ""

if command -v open >/dev/null 2>&1; then
  (sleep 2 && open "http://127.0.0.1:8000/companion") &
fi

exec uvicorn server:app --host 127.0.0.1 --port 8000 --reload
