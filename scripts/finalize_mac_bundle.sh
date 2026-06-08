#!/usr/bin/env bash
# Ad-hoc sign a Nuitka .app after codesign fails (common on iCloud Documents + macOS Sequoia).
# Signs in /tmp because iCloud re-applies xattrs under ~/Documents and breaks codesign verify.
set -euo pipefail

SRC="${1:?Usage: finalize_mac_bundle.sh source.app output.app}"
DEST="${2:?Usage: finalize_mac_bundle.sh source.app output.app}"

if [[ ! -f "${SRC}/Contents/MacOS/AHA" ]]; then
  echo "ERROR: Invalid Nuitka bundle (missing Contents/MacOS/AHA): $SRC" >&2
  exit 1
fi

WORKDIR="$(mktemp -d /tmp/aha-sign.XXXXXX)"
trap 'rm -rf "$WORKDIR"' EXIT
WORK_APP="${WORKDIR}/AHA.app"

echo "[INFO] Signing in ${WORKDIR} (outside iCloud Documents)..."
ditto --norsrc "$SRC" "$WORK_APP"
xattr -cr "$WORK_APP" 2>/dev/null || true
find "$WORK_APP" -name '._*' -delete 2>/dev/null || true

MACOS="${WORK_APP}/Contents/MacOS"
cat "${MACOS}/AHA" > "${MACOS}/AHA.clean"
chmod +x "${MACOS}/AHA.clean"
mv "${MACOS}/AHA.clean" "${MACOS}/AHA"

echo "[INFO] Ad-hoc signing bundle contents..."
find "$MACOS" -type f -print0 | while IFS= read -r -d '' f; do
  codesign --force --sign - "$f" 2>/dev/null || true
done
codesign --force --sign - "$WORK_APP"

if codesign --verify --deep --strict "$WORK_APP" >/dev/null 2>&1; then
  echo "[OK] codesign verify passed in ${WORKDIR}"
else
  echo "[WARN] codesign verify failed in workspace — continuing anyway." >&2
  codesign --verify --deep --strict "$WORK_APP" 2>&1 | tail -5 >&2 || true
fi

mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
# cp -R preserves com.apple.cs.CodeDirectory xattrs; ditto --norsrc strips them.
cp -R "$WORK_APP" "$DEST"
echo "[OK] Signed bundle written to: $DEST"
