#!/usr/bin/env bash
# Stage Tesseract + tessdata for bundling inside Nuitka retail builds (macOS).
# Run on the Mac build machine before build_macos.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${ROOT}/vendor/tesseract"
BIN="${DEST}/bin"
LIB="${DEST}/lib"
TESSDATA="${DEST}/tessdata"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: stage_tesseract_mac.sh must run on macOS." >&2
  exit 1
fi

if ! command -v tesseract >/dev/null 2>&1; then
  echo "ERROR: tesseract not found. Install: brew install tesseract" >&2
  exit 1
fi

TESS_BIN="$(command -v tesseract)"
BREW_PREFIX=""
if command -v brew >/dev/null 2>&1; then
  BREW_PREFIX="$(brew --prefix tesseract 2>/dev/null || true)"
fi

rm -rf "$DEST"
mkdir -p "$BIN" "$LIB" "$TESSDATA"

cp "$TESS_BIN" "$BIN/tesseract"
chmod +x "$BIN/tesseract"

# Language data — eng is required for UI OCR
ENG_SRC=""
if [[ -n "$BREW_PREFIX" && -f "${BREW_PREFIX}/share/tessdata/eng.traineddata" ]]; then
  ENG_SRC="${BREW_PREFIX}/share/tessdata/eng.traineddata"
else
  for src in \
    /opt/homebrew/share/tessdata/eng.traineddata \
    /usr/local/share/tessdata/eng.traineddata
  do
    if [[ -f "$src" ]]; then
      ENG_SRC="$src"
      break
    fi
  done
fi
if [[ -z "$ENG_SRC" ]]; then
  ENG_SRC="$(find /opt/homebrew/Cellar/tesseract /usr/local/Cellar/tesseract \
    -path '*/share/tessdata/eng.traineddata' 2>/dev/null | head -1 || true)"
fi
if [[ -n "$ENG_SRC" && -f "$ENG_SRC" ]]; then
  cp "$ENG_SRC" "$TESSDATA/eng.traineddata"
fi

if [[ ! -f "${TESSDATA}/eng.traineddata" ]]; then
  echo "ERROR: could not find eng.traineddata — check brew install tesseract" >&2
  exit 1
fi

# Bundle dylib dependencies so customer Macs do not need brew install tesseract
copy_dylib() {
  local src="$1"
  [[ -f "$src" ]] || return 0
  local base
  base="$(basename "$src")"
  [[ -f "${LIB}/${base}" ]] && return 0
  cp "$src" "${LIB}/${base}"
  install_name_tool -id "@rpath/${base}" "${LIB}/${base}" 2>/dev/null || true
}

echo "[INFO] Copying Tesseract dylib dependencies..."
while IFS= read -r lib; do
  lib="$(echo "$lib" | sed 's/^[[:space:]]*//;s/ (.*$//')"
  [[ "$lib" == "@executable_path"* ]] && continue
  [[ "$lib" == /usr/lib/* ]] && continue
  [[ "$lib" == /System/* ]] && continue
  copy_dylib "$lib"
done < <(otool -L "$BIN/tesseract" | tail -n +2)

install_name_tool -add_rpath "@executable_path/../lib" "$BIN/tesseract" 2>/dev/null || true

# Rewrite binary dylib paths to bundled @rpath copies where we have them
while IFS= read -r line; do
  old="$(echo "$line" | awk '{print $1}')"
  base="$(basename "$old")"
  if [[ -f "${LIB}/${base}" ]]; then
    install_name_tool -change "$old" "@rpath/${base}" "$BIN/tesseract" 2>/dev/null || true
  fi
done < <(otool -L "$BIN/tesseract" | tail -n +2)

echo "[OK] Staged Tesseract for Nuitka:"
echo "  ${BIN}/tesseract"
echo "  ${TESSDATA}/eng.traineddata"
echo "  $(find "$LIB" -name '*.dylib' 2>/dev/null | wc -l | tr -d ' ') dylibs in ${LIB}/"
