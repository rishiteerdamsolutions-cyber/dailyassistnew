# Shared Nuitka flags for AHA retail builds. Source from build scripts.
# shellcheck shell=bash

nuitka_find_python() {
  local py=""
  for candidate in python3.12 python3.11 python3.10; do
    if command -v "$candidate" >/dev/null 2>&1; then
      local ver major minor
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
    echo "ERROR: Python 3.10+ required for Nuitka retail build." >&2
    echo "  macOS: brew install python@3.12" >&2
    echo "  Windows: install Python 3.12 from python.org" >&2
    return 1
  fi
  echo "$py"
}

nuitka_prepare_venv() {
  local py="$1"
  local root="$2"
  cd "$root"
  if [[ -d ".venv" ]]; then
    if ! .venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
      echo "[INFO] Removing stale .venv (needs Python 3.10+)..."
      rm -rf .venv
    fi
  fi
  if [[ ! -d ".venv" ]]; then
    "$py" -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -q -U pip
  pip install -q -r requirements.txt -e .
  pip install -q -r requirements-build.txt
}

# Packages that must be bundled explicitly (lazy imports / extensions).
NUITKA_INCLUDE_PACKAGES=(
  aha
  bol
  server
  cv2
  PIL
  numpy
  pytesseract
  pyautogui
  mss
  psutil
  uvicorn
  fastapi
  multipart
  pydantic
  pydantic_settings
  firebase_admin
  supabase
  razorpay
  google.generativeai
)

nuitka_package_flags() {
  local pkg
  for pkg in "${NUITKA_INCLUDE_PACKAGES[@]}"; do
    printf '%s\n' "--include-package=${pkg}"
  done
}
