# AHA — Distribution

Product site: [dailyassist.xyz](https://dailyassist.xyz)

## Default distribution (retail — secure)

Customers receive a **compiled desktop app** in a zip — **not** Python source.

| Platform | Customer gets | First-run security |
|----------|---------------|-------------------|
| macOS | `AHA.app` + `INSTALL.md` | Gatekeeper “unidentified developer” — **Open Anyway** (`INSTALL.md`) |
| Windows | `AHA/AHA.exe` + `INSTALL.md` | SmartScreen — **Run anyway** (`INSTALL.md`) |

### Build (maintainers)

```bash
# macOS (Python 3.10+ required — brew install python@3.12):
./scripts/build_desktop_release.sh mac
./scripts/package_dmg.sh   # optional → downloads/AHA-mac.dmg

# Windows (on a Windows machine with Python 3.10+):
scripts\build_windows_release.bat
```

Output: `downloads/AHA-mac.zip` or `downloads/AHA-win.zip`.  
`scripts/verify_retail_zip.sh` runs automatically — it **rejects** zips that still contain `bol/`, `server.py`, etc.

**Do not ship** `scripts/build_release_zip.sh` output to customers (legacy source tree — dev only).

### Security layers (today)

1. **No source in download** — Nuitka compiled binary, not `bol/` / `aha/` files
2. **Dev license bypass disabled** — `AHA_ALLOW_DEV_LICENSE` cannot work in retail builds (`packaging/aha_retail_hook.py`)
3. **Cloud license gate** — Firebase sign-in + Supabase `aha_licenses` (Razorpay or coupon)
4. **Paid download gate** — `/api/download/*` checks active subscription before redirecting to zip URL
5. **Secrets never in zip** — `.env`, Firebase JSON, Razorpay keys stay on Vercel / maintainer machine only

### Host on production

1. Supabase Storage → public bucket `aha-releases`
2. Upload retail zips (after `verify_retail_zip.sh` passes)
3. Vercel env: `AHA_DOWNLOAD_MAC_URL`, `AHA_DOWNLOAD_WIN_URL`
4. Redeploy → `GET /api/billing/ready` should show `"downloads": {"mac": true, "win": true}`

Also fix on Vercel if not done: valid `FIREBASE_SERVICE_ACCOUNT_JSON`, matching Razorpay test/live keys.

---

## Optional: Apple notarization (fewer Mac warnings)

When you have an **Apple Developer** account:

```bash
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name (TEAMID)" \
  AHA.app
xcrun notarytool submit AHA.zip --apple-id "..." --team-id "..." --password "app-specific-password" --wait
xcrun stapler staple AHA.app
```

Notarization improves trust UX; **license enforcement** remains cloud-side.

---

## Optional: Windows Authenticode

```powershell
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a AHA.exe
```

---

## Permissions (required for full assistant)

- **macOS:** Accessibility, Screen Recording
- **Windows:** Allow when prompted; antivirus exclusion if needed

See companion first-run guide and `INSTALL.md`.

---

## Support

- Website: [dailyassist.xyz](https://dailyassist.xyz)
- Email: support@dailyassist.xyz
