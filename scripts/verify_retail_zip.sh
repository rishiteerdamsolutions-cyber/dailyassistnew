#!/usr/bin/env bash
# Fail if a customer zip still contains readable source (bol/, server.py, etc.).
set -euo pipefail

ZIP="${1:?Usage: verify_retail_zip.sh path/to/AHA-mac.zip}"

if [[ ! -f "$ZIP" ]]; then
  echo "ERROR: not found: $ZIP" >&2
  exit 1
fi

listing="$(unzip -Z1 "$ZIP" 2>/dev/null || unzip -l "$ZIP" | awk 'NR>3 {print $4}')"

# Source distributions ship these at zip root — retail must not.
for forbidden in "bol/" "aha/" "server.py" "app_webview.py" "start.bat" "start_companion.command"; do
  if echo "$listing" | grep -qF "$forbidden"; then
    echo "ERROR: $ZIP looks like a SOURCE zip (found:${forbidden})." >&2
    echo "Use scripts/build_desktop_release.sh — not build_release_zip.sh." >&2
    exit 1
  fi
done

# Retail Mac zip should contain AHA.app; Windows should contain AHA/AHA.exe
if echo "$listing" | grep -qE '^AHA\.app/'; then
  echo "[OK] retail Mac bundle detected in $ZIP"
elif echo "$listing" | grep -qE '^AHA/AHA\.exe'; then
  echo "[OK] retail Windows bundle detected in $ZIP"
else
  echo "WARN: expected AHA.app or AHA/AHA.exe in $ZIP — double-check before upload" >&2
fi
