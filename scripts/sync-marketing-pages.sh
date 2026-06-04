#!/usr/bin/env bash
# Copy public marketing HTML into web/ for local server.py (mirrors route folders).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for f in index.html 404.html marketing.css marketing-tailwind-config.js; do
  cp "$ROOT/public/$f" "$ROOT/web/$f"
done
for page in pricing subscribe download how-it-works faq about contact legal; do
  mkdir -p "$ROOT/web/$page"
  cp "$ROOT/public/$page/index.html" "$ROOT/web/$page/index.html"
done
echo "Synced public/ -> web/"
