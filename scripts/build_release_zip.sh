#!/usr/bin/env bash
# Build AHA-mac.zip / AHA-win.zip for /api/download (local server or upload to cloud).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/downloads"
PLATFORM="${1:-mac}"

mkdir -p "$OUT"
cd "$ROOT"

EXCLUDES=(
  ".git/*"
  ".venv/*"
  "*/.venv/*"
  ".env"
  ".env.*"
  "*adminsdk*.json"
  "rzp-key*.csv"
  "downloads/AHA-mac.zip"
  "downloads/AHA-win.zip"
  "VISIONBUTTONS/*"
  "vision_debug_crops/*"
  "vision_test_result.png"
  "storage files/*"
  "*.egg-info/*"
  ".cursor/*"
  "stitch/*"
)

case "$PLATFORM" in
  mac)
    ZIP="${OUT}/AHA-mac.zip"
    ;;
  win)
    ZIP="${OUT}/AHA-win.zip"
    ;;
  all)
    "$0" mac
    "$0" win
    exit 0
    ;;
  *)
    echo "Usage: $0 [mac|win|all]" >&2
    exit 1
    ;;
esac

echo "Building ${ZIP} ..."
rm -f "$ZIP"
zip -r "$ZIP" . -x "${EXCLUDES[@]}" >/dev/null
ls -lh "$ZIP"
echo "Done. Local: use /download. On Vercel: upload zip and set AHA_DOWNLOAD_MAC_URL or AHA_DOWNLOAD_WIN_URL."
