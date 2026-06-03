# AHA — Distribution

Product site: [dailyassist.xyz](https://dailyassist.xyz)

## Default distribution (current)

AHA ships as a **zip download** from dailyassist.xyz — not through the Mac App Store or Microsoft Store.

| Platform | Launcher | First-run security |
|----------|----------|-------------------|
| macOS | `start_companion.command` | Gatekeeper &ldquo;unidentified developer&rdquo; — user uses **Open Anyway** (see `INSTALL.md`) |
| Windows | `start.bat` | SmartScreen — user chooses **Run anyway** (see `INSTALL.md`) |

This path avoids Apple notarization and Microsoft code signing. Users accept one-time OS warnings; see `INSTALL.md` for step-by-step screenshots-style instructions.

### Package contents

Include in the zip:

- Application source / frozen bundle
- `start_companion.command` (macOS) and `start.bat` (Windows)
- `INSTALL.md`
- `LICENSE` or link to `web/legal.html`
- `.env.example` (no secrets)

Exclude: `.env`, `*adminsdk*.json`, `.venv` (Windows/Mac installer creates local venv on first run)

---

## Optional: signed macOS build (enterprise)

When you have an **Apple Developer** account and want fewer Gatekeeper warnings:

1. Build the app bundle (e.g. PyInstaller or py2app wrapping `app_webview.py`).
2. Sign with Developer ID Application:
   ```bash
   codesign --deep --force --verify --verbose \
     --sign "Developer ID Application: Your Name (TEAMID)" \
     AHA.app
   ```
3. Notarize and staple:
   ```bash
   xcrun notarytool submit AHA.zip --apple-id "..." --team-id "..." --password "app-specific-password" --wait
   xcrun stapler staple AHA.app
   ```
4. Distribute the stapled `.app` or `.dmg`.

Unsigned zip remains valid for early adopters; notarization is optional polish, not a requirement for Tier-1/Tier-2 functionality.

---

## Optional: Windows code signing

For fewer SmartScreen prompts, sign `start.bat` launcher or the main `.exe` with an Authenticode certificate from a trusted CA, then timestamp:

```powershell
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a AHA.exe
```

---

## Permissions (required for full assistant)

Users must grant OS permissions documented in the companion **first-run guide** and `INSTALL.md`:

- **macOS:** Accessibility (mouse/keyboard), Screen Recording (vision)
- **Windows:** Allow the app when prompted; add antivirus exclusion if needed for `pyautogui`

---

## Support

- Website: [dailyassist.xyz](https://dailyassist.xyz)
- Email: support@dailyassist.xyz
