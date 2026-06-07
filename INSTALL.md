# AHA — Install Guide

**No app store. No signing required. Works on Mac and Windows.**

AHA runs as a **compiled desktop app** (not source code). Because it is not sold through the App Store or Microsoft Store, your OS may show a one-time security warning. This is normal — follow the steps below to open it anyway.

**You do not need to install Python** — the retail download includes everything to run.

---

## Subscribe first (Mac or Windows)

1. Visit **[dailyassist.xyz/subscribe](https://www.dailyassist.xyz/subscribe)** and **Sign in with Google**.
2. Complete payment with Razorpay, or enter a coupon code if you have one.
3. Go to **[dailyassist.xyz/download](https://www.dailyassist.xyz/download)** and download the zip for your platform.
5. Install using the steps below; sign in with Google in the app — your license syncs from the cloud.

You can also enter a license key manually in the app if support sent you one.

---

## Requirements (both platforms)

| | Minimum |
|-|---------|
| Chrome | Any recent version (for social posting flows) |
| RAM | 4 GB |
| Storage | 500 MB |

---

## macOS

### Step 1 — Download & extract

Download **AHA-mac.zip** from [dailyassist.xyz/download](https://www.dailyassist.xyz/download) (after Google sign-in + subscription). Unzip — you get **`AHA.app`**.

### Step 2 — First launch

Double-click **`AHA.app`**.

If macOS says the app is from an unidentified developer: **System Settings → Privacy & Security → Open Anyway**, or right-click **AHA.app** → **Open** → **Open**.

### Step 3 — Subsequent launches

Double-click **AHA.app** as usual.

### Accessibility permission (required for Tier-2 assistant tasks)

The first time AHA helps by moving your mouse or keyboard, macOS will ask:

> *Allow "Terminal" (or "AHA") to control your computer?*

Click **Allow** in **System Settings → Privacy & Security → Accessibility**.  
Without this, Tier-2 tasks (helping you click buttons in other apps) will not work.

The AHA companion also shows a **permissions guide** on first launch — use **Open System Settings** there if you need help.

### Screen Recording permission (required for vision)

If AHA asks for screen recording access, grant it in:  
**System Settings → Privacy & Security → Screen Recording**

---

## Windows

### Step 1 — Download & extract

Download **AHA-win.zip** from [dailyassist.xyz/download](https://www.dailyassist.xyz/download).  
Right-click the zip → **Extract All** → you get an **`AHA`** folder with **`AHA.exe`** inside.

### Step 2 — First launch

Double-click **`AHA.exe`** inside the extracted `AHA` folder.

Windows SmartScreen may show:

> *Windows protected your PC — Microsoft Defender SmartScreen prevented an unrecognized app from starting.*

### Step 3 — Allow the app

Click **More info** (in the SmartScreen dialog).  
Then click **Run anyway**.

> This only happens once per download. Future launches open directly.

### Step 4 — Dependencies install automatically

The first run installs Python packages into a local `.venv` folder inside the AHA directory. This takes 1–2 minutes on first run. A window will open when ready.

### Antivirus note

Some antivirus tools may flag `pyautogui` or the venv as suspicious because they can control the mouse. This is a false positive — AHA uses these only to perform tasks *you* ask it to do. Add the AHA folder to your antivirus exclusions if this occurs.

---

## Adding your API key (Tier-2)

1. Open AHA → click the **gear icon** (⚙) in the top-right of the chat panel.
2. Select **Google Gemini** or **OpenAI** from the dropdown.
3. Paste your API key and click **Save Key**.

Your key is stored locally on your machine only (`~/.aha/config.json`). It is never sent to our servers.

Tier-1 (social posting, dev workspace, system tasks) never uses your API key.

---

## Uninstall

Delete the AHA folder. Your local settings and vault content are in:

- **Mac:** `~/.aha/` and `~/Downloads/aha/`
- **Windows:** `%USERPROFILE%\.aha\` and `%USERPROFILE%\Downloads\aha\`

Delete those folders too for a complete removal.

---

## Support

Visit [dailyassist.xyz](https://dailyassist.xyz) or email support@dailyassist.xyz
