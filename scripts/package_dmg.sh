#!/usr/bin/env bash
# Wrap dist/AHA.app (or downloads staging) into a drag-and-drop .dmg for Mac.
# Run AFTER scripts/build_desktop_release.sh mac
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
chmod +x "${ROOT}/scripts/aha_signed_app_path.sh"
if [[ -n "${1:-}" && "${1:0:1}" != "#" && -d "$1" ]]; then
  APP="$1"
else
  APP="$("${ROOT}/scripts/aha_signed_app_path.sh")"
fi
APP="${APP//$'\r'/}"
APP="${APP//$'\n'/}"
OUT="${ROOT}/downloads/AHA-mac.dmg"
STAGING="${ROOT}/dist/_dmg_staging"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: DMG packaging requires macOS." >&2
  exit 1
fi

if [[ ! -d "$APP" ]]; then
  echo "ERROR: AHA.app not found at: $APP" >&2
  echo "Run: ./scripts/build_desktop_release.sh mac" >&2
  exit 1
fi

rm -rf "$STAGING" "$OUT"
mkdir -p "$STAGING"
cp -R "$APP" "$STAGING/AHA.app"
ln -s /Applications "$STAGING/Applications"

hdiutil create \
  -volname "AHA" \
  -srcfolder "$STAGING" \
  -ov \
  -format UDZO \
  "$OUT"

rm -rf "$STAGING"
echo "[OK] $OUT"
ls -lh "$OUT"
