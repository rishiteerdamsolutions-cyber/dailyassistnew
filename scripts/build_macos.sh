#!/usr/bin/env bash
# Nuitka retail build for macOS → dist/AHA.app (industry-standard compiled binary).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=scripts/nuitka_build.inc.sh
source "${ROOT}/scripts/nuitka_build.inc.sh"

# Prevent Finder/resource-fork metadata from being copied into build artifacts.
export COPYFILE_DISABLE=1
export COPY_EXTENDED_ATTRIBUTES_DISABLE=1

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: macOS Nuitka build must run on Darwin." >&2
  exit 1
fi

PY="$(nuitka_find_python)" || exit 1
echo "[INFO] Using $("$PY" --version)"

nuitka_prepare_venv "$PY" "$ROOT"

echo "[INFO] Staging Tesseract for customer machines (no brew install required)..."
chmod +x "${ROOT}/scripts/stage_tesseract_mac.sh"
"${ROOT}/scripts/stage_tesseract_mac.sh"

# codesign rejects resource forks / Finder metadata; sanitize the full tree.
echo "[INFO] Stripping .DS_Store / AppleDouble / xattr metadata..."
find "${ROOT}" -name '.DS_Store' -delete 2>/dev/null || true
find "${ROOT}" -name '._*' -delete 2>/dev/null || true
if command -v xattr >/dev/null 2>&1; then
  xattr -cr "${ROOT}" 2>/dev/null || true
fi
if command -v dot_clean >/dev/null 2>&1; then
  dot_clean -m "${ROOT}" 2>/dev/null || true
fi

PKG_FLAGS=()
while IFS= read -r _pkg_line; do
  [[ -n "$_pkg_line" ]] && PKG_FLAGS+=("$_pkg_line")
done < <(nuitka_package_flags)

echo "[INFO] Compiling AHA.app with Nuitka (standalone, no Python required on customer Mac)..."
set +e
"$PY" -m nuitka \
  --standalone \
  --macos-create-app-bundle \
  --macos-app-name="AHA" \
  --macos-app-version="1.0.0" \
  --macos-app-icon=none \
  --company-name="dailyassist.xyz" \
  --product-name="AHA" \
  --output-dir=dist \
  --output-filename=AHA \
  --include-data-dir=web=web \
  --include-data-dir=VISIONBUTTONS=VISIONBUTTONS \
  --include-data-dir=vendor/tesseract=tesseract \
  --include-data-files=INSTALL.md=INSTALL.md \
  --include-package-data=webview \
  --include-package-data=cv2 \
  --include-package-data=pytesseract \
  "${PKG_FLAGS[@]}" \
  --nofollow-import-to=webview.platforms.android \
  --nofollow-import-to=webview.platforms.qt \
  --nofollow-import-to=webview.platforms.winforms \
  --nofollow-import-to=webview.platforms.edgechromium \
  --nofollow-import-to=webview.platforms.edgehtml \
  --nofollow-import-to=webview.platforms.mshtml \
  --nofollow-import-to=webview.platforms.cef \
  --nofollow-import-to=tests \
  --nofollow-import-to=pytest \
  --assume-yes-for-downloads \
  app_webview.py
nuitka_exit=$?
set -e

# Nuitka may exit non-zero at codesign even when the bundle is complete.
if [[ ! -f "dist/app_webview.app/Contents/MacOS/AHA" ]]; then
  echo "ERROR: Nuitka did not produce dist/app_webview.app — check dist/ output." >&2
  ls -la dist/ >&2 || true
  exit 1
fi
if [[ "$nuitka_exit" -ne 0 ]]; then
  echo "[WARN] Nuitka exited $nuitka_exit (usually codesign) — finalizing bundle manually..."
fi

chmod +x "${ROOT}/scripts/finalize_mac_bundle.sh"
SIGNED_DIR="/tmp/aha-retail-latest"
rm -rf "$SIGNED_DIR"
mkdir -p "$SIGNED_DIR"
"${ROOT}/scripts/finalize_mac_bundle.sh" "dist/app_webview.app" "${SIGNED_DIR}/AHA.app"
mkdir -p dist
echo "${SIGNED_DIR}/AHA.app" > dist/.signed_app_path

# Best-effort local copy (iCloud Documents may break codesign verify; zip uses /tmp copy).
rm -rf dist/AHA.app
cp -R "${SIGNED_DIR}/AHA.app" dist/AHA.app 2>/dev/null || true
rm -rf dist/app_webview.app

echo "[OK] Signed retail bundle: ${SIGNED_DIR}/AHA.app"
echo "[OK] Zip/DMG will use the /tmp copy (avoids iCloud metadata)."
du -sh "${SIGNED_DIR}/AHA.app"
if [[ -d dist/AHA.app ]]; then
  echo "[OK] dist/AHA.app (local copy; run from /tmp if Gatekeeper complains)"
fi
