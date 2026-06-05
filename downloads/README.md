# Customer downloads (retail — **no source code**)

| File | Contents |
|------|----------|
| `AHA-mac.zip` | **`AHA.app`** + `INSTALL.md` (compiled binary) |
| `AHA-win.zip` | **`AHA/`** folder + `INSTALL.md` (compiled binary) |

Customers do **not** receive `.py` agent source, `bol/`, or repo files.

## Build (maintainers only)

```bash
chmod +x scripts/build_desktop_release.sh

# macOS (must run on a Mac):
./scripts/build_desktop_release.sh mac

# Windows (must run on Windows):
./scripts/build_desktop_release.sh win
```

Requires: Python 3.10+, `pip install -r requirements-build.txt`

**Legacy source zip** (do not ship to customers): `scripts/build_release_zip.sh`

## Host on production (Vercel)

1. Supabase → Storage → public bucket `aha-releases`
2. Upload `AHA-mac.zip` / `AHA-win.zip`
3. Vercel env:
   - `AHA_DOWNLOAD_MAC_URL`
   - `AHA_DOWNLOAD_WIN_URL`
4. Redeploy → verify `/api/billing/ready` → `"downloads": {"mac": true, "win": true}`

## Security (retail build)

- PyInstaller bundle — bytecode only, not readable source tree
- `AHA_ALLOW_DEV_LICENSE` **disabled** in retail builds
- License still enforced via **Firebase + Supabase** (cloud)
- Optional later: Apple notarization + Windows Authenticode signing

See `DISTRIBUTION.md` and `INSTALL.md`.
