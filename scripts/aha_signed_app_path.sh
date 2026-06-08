#!/usr/bin/env bash
# Print the path to the last ad-hoc signed AHA.app (under /tmp, safe for zip/dmg).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PATH_FILE="${ROOT}/dist/.signed_app_path"
if [[ -f "$PATH_FILE" ]]; then
  cat "$PATH_FILE"
  exit 0
fi
if [[ -d "${ROOT}/dist/AHA.app" ]]; then
  echo "${ROOT}/dist/AHA.app"
  exit 0
fi
echo "ERROR: no signed AHA.app — run scripts/build_macos.sh first." >&2
exit 1
