# PyInstaller spec — AHA retail desktop (no source in customer download).
# Build: scripts/build_desktop_release.sh mac|win

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent.parent

block_cipher = None

_datas = [
    (str(ROOT / "web"), "web"),
    (str(ROOT / "VISIONBUTTONS"), "VISIONBUTTONS"),
    (str(ROOT / "INSTALL.md"), "."),
]

_hidden = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "engineio.async_drivers.threading",
    "google.auth.transport.requests",
    "firebase_admin",
    "supabase",
    "razorpay",
    "webview",
    "cv2",
    "PIL",
    "pytesseract",
    "pyautogui",
    "aha",
    "bol",
]

a = Analysis(
    [str(ROOT / "app_webview.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=_datas,
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "packaging" / "aha_retail_hook.py")],
    excludes=["tests", "pytest", "tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AHA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AHA",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="AHA.app",
        icon=None,
        bundle_identifier="xyz.dailyassist.aha",
        info_plist={
            "NSHighResolutionCapable": "True",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleDisplayName": "AHA",
        },
    )
