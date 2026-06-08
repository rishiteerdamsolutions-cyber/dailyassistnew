#!/usr/bin/env bash
# Retail release packages — Nuitka compiled binary, NO Python source in customer zip.
# Output: downloads/AHA-mac.zip or downloads/AHA-win.zip
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/downloads"
PLATFORM="${1:-mac}"

usage() {
  echo "Usage: $0 [mac|win|all]" >&2
  echo "  mac — Nuitka on macOS → AHA.app in zip (+ optional .dmg)" >&2
  echo "  win — run scripts/build_windows_release.bat on Windows" >&2
  exit 1
}

case "$PLATFORM" in
  mac|win|all) ;;
  *) usage ;;
esac

package_mac_zip() {
  local zip_name="AHA-mac.zip"
  local signed_app
  chmod +x "${ROOT}/scripts/aha_signed_app_path.sh"
  signed_app="$("${ROOT}/scripts/aha_signed_app_path.sh")"

  if [[ ! -d "$signed_app" ]]; then
    echo "ERROR: signed AHA.app missing — run scripts/build_macos.sh first." >&2
    return 1
  fi

  rm -f "${OUT}/${zip_name}"
  mkdir -p "$OUT"
  # Zip from /tmp signed copy so iCloud does not invalidate ad-hoc signatures.
  ditto -c -k --sequesterRsrc --keepParent "$signed_app" "${OUT}/${zip_name}.app.zip"
  rm -f "${OUT}/${zip_name}"
  mv "${OUT}/${zip_name}.app.zip" "${OUT}/${zip_name}"

  "${ROOT}/scripts/verify_retail_zip.sh" "${OUT}/${zip_name}"
  echo "[OK] ${OUT}/${zip_name}"
  ls -lh "${OUT}/${zip_name}"

  if [[ "${AHA_SKIP_DMG:-}" != "1" ]]; then
    echo "[INFO] Building DMG..."
    "${ROOT}/scripts/package_dmg.sh"
  else
    echo "Skipped DMG (AHA_SKIP_DMG=1). Run: ./scripts/package_dmg.sh"
  fi
  echo "Upload to Supabase aha-releases → set AHA_DOWNLOAD_MAC_URL on Vercel."
}

build_mac() {
  local os_name
  os_name="$(uname -s)"
  if [[ "$os_name" != "Darwin" ]]; then
    echo "[skip] Mac Nuitka build must run on macOS (current: $os_name)" >&2
    return 1
  fi
  mkdir -p "$OUT"
  "${ROOT}/scripts/build_macos.sh"
  package_mac_zip
}

build_win_hint() {
  echo "ERROR: Windows Nuitka build must run on Windows." >&2
  echo "  Run: scripts\\build_windows_release.bat" >&2
  return 1
}

if [[ "$PLATFORM" == "all" ]]; then
  build_mac || true
  build_win_hint || true
elif [[ "$PLATFORM" == "mac" ]]; then
  build_mac
else
  build_win_hint
fi
