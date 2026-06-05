#!/usr/bin/env bash
# Build secure retail desktop packages — compiled binary, NO Python source.
# Output: downloads/AHA-mac.zip or downloads/AHA-win.zip
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/downloads"
PLATFORM="${1:-mac}"

usage() {
  echo "Usage: $0 [mac|win|all]" >&2
  echo "  mac — build on macOS (creates AHA.app inside zip)" >&2
  echo "  win — build on Windows (creates AHA folder inside zip)" >&2
  exit 1
}

case "$PLATFORM" in
  mac|win|all) ;;
  *) usage ;;
esac

build_one() {
  local plat="$1"
  local os_name
  os_name="$(uname -s)"

  if [[ "$plat" == "mac" && "$os_name" != "Darwin" ]]; then
    echo "[skip] Mac retail build must run on macOS (current: $os_name)" >&2
    return 1
  fi
  if [[ "$plat" == "win" && "$os_name" != MINGW* && "$os_name" != MSYS* && "$os_name" != CYGWIN* ]]; then
    echo "[skip] Windows retail build must run on Windows (current: $os_name)" >&2
    return 1
  fi

  cd "$ROOT"
  mkdir -p "$OUT"

  local py=""
  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      ver="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
      major="${ver%%.*}"
      minor="${ver#*.}"
      if [[ "$major" -ge 3 && "$minor" -ge 10 ]]; then
        py="$candidate"
        break
      fi
    fi
  done
  if [[ -z "$py" ]]; then
    echo "ERROR: Python 3.10+ required (bol package). Install python3.10+ and retry." >&2
    return 1
  fi

  if [[ ! -d ".venv" ]]; then
    echo "[INFO] Creating .venv for build ($py)..."
    "$py" -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate

  pip install -q -r requirements.txt -e .
  pip install -q -r requirements-build.txt

  echo "[INFO] Running PyInstaller (retail — no source in output)..."
  pyinstaller packaging/AHA.spec --noconfirm --clean

  local zip_name="AHA-${plat}.zip"
  local staging="${ROOT}/dist/_package_staging"
  rm -rf "$staging"
  mkdir -p "$staging"

  if [[ "$plat" == "mac" ]]; then
    if [[ -d "${ROOT}/dist/AHA.app" ]]; then
      cp -R "${ROOT}/dist/AHA.app" "$staging/"
    elif [[ -d "${ROOT}/dist/AHA/AHA.app" ]]; then
      cp -R "${ROOT}/dist/AHA/AHA.app" "$staging/"
    else
      echo "ERROR: PyInstaller did not produce AHA.app — check packaging/AHA.spec" >&2
      return 1
    fi
    cp "${ROOT}/INSTALL.md" "$staging/"
  else
    if [[ ! -d "${ROOT}/dist/AHA" ]]; then
      echo "ERROR: PyInstaller did not produce dist/AHA — check packaging/AHA.spec" >&2
      return 1
    fi
    cp -R "${ROOT}/dist/AHA" "$staging/AHA"
    cp "${ROOT}/INSTALL.md" "$staging/"
  fi

  rm -f "${OUT}/${zip_name}"
  (cd "$staging" && zip -r -q "${OUT}/${zip_name}" .)
  rm -rf "$staging"

  "${ROOT}/scripts/verify_retail_zip.sh" "${OUT}/${zip_name}"

  echo "[OK] ${OUT}/${zip_name}"
  ls -lh "${OUT}/${zip_name}"
  local env_key="AHA_DOWNLOAD_MAC_URL"
  [[ "$plat" == "win" ]] && env_key="AHA_DOWNLOAD_WIN_URL"
  echo "Upload to Supabase aha-releases and set ${env_key} on Vercel."
}

if [[ "$PLATFORM" == "all" ]]; then
  build_one mac || true
  build_one win || true
else
  build_one "$PLATFORM"
fi
