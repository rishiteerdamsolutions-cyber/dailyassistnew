# Customer downloads (retail — **no source code**)

| File | Contents |
|------|----------|
| `AHA-mac.zip` | **`AHA.app`** + `INSTALL.md` (compiled binary) |
| `AHA-win.zip` | **`AHA/`** folder + `INSTALL.md` (compiled binary) |

Customers do **not** receive `.py` agent source, `bol/`, or repo files.

## Build (maintainers only)

**Ship gate:** **Nuitka** retail build (`build_desktop_release.sh` / `build_macos.sh`).  
Compiled native binary — customers do not install Python.

```bash
chmod +x scripts/build_desktop_release.sh scripts/launch_gate_check.sh

# macOS (must run on a Mac with Python 3.10+):
./scripts/build_desktop_release.sh mac
./scripts/package_dmg.sh          # optional → downloads/AHA-mac.dmg

# Windows (must run on Windows with Python 3.10+):
./scripts/build_desktop_release.sh win

# Honest status (no guessing):
./scripts/launch_gate_check.sh
```

Requires: Python 3.10+, `pip install -r requirements-build.txt`

**Build machine also needs Tesseract** (staged into the bundle — customers do not install it):
- macOS: `brew install tesseract` then `scripts/stage_tesseract_mac.sh` (runs automatically in `build_macos.sh`)
- Windows: install [UB Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) then `scripts\stage_tesseract_win.bat`

**Warning:** Small zips (~600 KB) that contain `bol/` are **source** bundles — never upload those to `aha-releases`.

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
