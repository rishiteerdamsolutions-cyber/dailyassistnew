#!/usr/bin/env bash
# Honest local launch-gate check — no hallucination. Run from repo root.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

pass=0
fail=0
warn=0

ok()   { echo "[PASS] $*"; pass=$((pass + 1)); }
bad()  { echo "[FAIL] $*"; fail=$((fail + 1)); }
note() { echo "[WARN] $*"; warn=$((warn + 1)); }

echo "=== AHA Launch Gate (local) ==="
echo ""

# Code — Gemini quota wired
if grep -q "check_direct_access_quota" vercel_backend/gemini_proxy.py 2>/dev/null; then
  ok "Gemini spam protection wired in gemini_proxy.py"
else
  bad "Gemini spam protection NOT wired"
fi

# Code — Cloud auth wired
if grep -q "validate_cloud_caller" vercel_backend/routes.py 2>/dev/null; then
  ok "Cloud API auth wired in vercel_backend/routes.py"
else
  bad "Cloud API auth NOT wired"
fi

# Code — Desktop sends Firebase token
if grep -q "firebase_id_token" aha/cloud_client.py 2>/dev/null; then
  ok "Desktop cloud_client sends firebase_id_token"
else
  bad "Desktop cloud_client missing firebase_id_token"
fi

# Unit tests
if python3 -m pytest tests/test_token_quota.py tests/test_cloud_auth.py tests/test_daily_usage.py -q >/dev/null 2>&1; then
  ok "Usage + auth unit tests pass"
else
  bad "Usage + auth unit tests FAIL — run pytest"
fi

# Retail artifacts
if [[ -f downloads/AHA-mac.zip ]]; then
  if ./scripts/verify_retail_zip.sh downloads/AHA-mac.zip >/dev/null 2>&1; then
    ok "downloads/AHA-mac.zip is a valid RETAIL bundle"
  else
    bad "downloads/AHA-mac.zip is SOURCE/legacy (contains bol/) — DELETE and run: ./scripts/build_desktop_release.sh mac"
  fi
else
  bad "downloads/AHA-mac.zip missing — run: ./scripts/build_desktop_release.sh mac (Nuitka; Python 3.10+ on Mac)"
fi

if [[ -f downloads/AHA-mac.dmg ]]; then
  ok "downloads/AHA-mac.dmg exists"
else
  note "downloads/AHA-mac.dmg missing — optional: ./scripts/package_dmg.sh"
fi

if [[ -f downloads/AHA-win.zip ]]; then
  if unzip -l downloads/AHA-win.zip 2>/dev/null | grep -q "AHA/AHA.exe"; then
    ok "downloads/AHA-win.zip is a valid RETAIL bundle"
  else
    bad "downloads/AHA-win.zip is SOURCE/legacy — DELETE and rebuild on Windows"
  fi
else
  note "downloads/AHA-win.zip missing — build on Windows: scripts/build_desktop_release.sh win"
fi

# Nuitka (experimental — not ship gate)
if [[ -d dist/AHA.app ]] && [[ ! -f downloads/AHA-mac.zip ]]; then
  note "dist/AHA.app exists but retail zip not packaged (Nuitka-only build?)"
fi

echo ""
echo "=== Cannot verify locally (manual / prod) ==="
note "Supabase migration 006_daily_usage.sql run in prod dashboard"
note "Vercel env: GEMINI_API_KEY, SUPABASE_*, FIREBASE_SERVICE_ACCOUNT_JSON, AHA_REQUIRE_CLOUD_AUTH=1"
note "AHA_DOWNLOAD_MAC_URL / AHA_DOWNLOAD_WIN_URL after Supabase upload"
note "Live Razorpay or COUPON100 smoke: subscribe → license → download → sign-in"
note "Mac E2E: one social flow + one local command on clean machine"
note "Code signing / notarization (optional UX)"

echo ""
echo "--- Summary: ${pass} pass, ${fail} fail, ${warn} warn ---"
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
