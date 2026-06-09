#!/usr/bin/env bash
# Copy latest web UI into ~/Applications/AHA.app (no full rebuild).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL="${HOME}/Applications/AHA.app/Contents/MacOS/web"

if [[ ! -d "$INSTALL" ]]; then
  echo "ERROR: $INSTALL not found — install AHA first." >&2
  exit 1
fi

cp "${ROOT}/web/companion.html" "${INSTALL}/"
cp "${ROOT}/web/auth-desktop.html" "${INSTALL}/" 2>/dev/null || true
cp "${ROOT}/web/open-accessibility.html" "${INSTALL}/"
cp "${ROOT}/web/open-screen-recording.html" "${INSTALL}/"

echo "[OK] Synced web UI to ${INSTALL}"
echo "Quit AHA (Dock → Quit), then: open ~/Applications/AHA.app"
