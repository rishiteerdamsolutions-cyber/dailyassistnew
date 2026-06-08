#!/usr/bin/env bash
# Install signed retail AHA to ~/Applications and launch (fixes Accessibility list).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="/tmp/aha-retail-latest/AHA.app"
INSTALL="${HOME}/Applications/AHA.app"

if [[ -f "${ROOT}/dist/.signed_app_path" ]]; then
  SRC="$(tr -d '\r\n' < "${ROOT}/dist/.signed_app_path")"
fi

if [[ ! -f "${SRC}/Contents/MacOS/AHA" ]]; then
  echo "ERROR: Retail app not found at: ${SRC}" >&2
  echo "Run: cd ~/Documents/dailyassist && ./scripts/build_desktop_release.sh mac" >&2
  exit 1
fi

echo "[INFO] Installing to ${INSTALL} (macOS lists apps here in Accessibility)..."
rm -rf "${INSTALL}"
cp -R "${SRC}" "${INSTALL}"
xattr -dr com.apple.quarantine "${INSTALL}" 2>/dev/null || true

echo "[INFO] Launching AHA..."
osascript -e 'quit app "AHA"' 2>/dev/null || true
sleep 1
open "${INSTALL}"

echo ""
echo "=== Accessibility (required) ==="
echo "1. Wait for the AHA window to appear (~10 seconds)."
echo "2. macOS may show a popup: click Open System Settings and allow AHA."
echo "3. If no popup: System Settings -> Privacy & Security -> Accessibility"
echo "4. Click the + button (bottom left), choose Applications -> AHA -> Open"
echo "5. Turn ON the toggle for AHA (or Python if that is what you see)."
echo ""
echo "Opening Accessibility settings now..."
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
