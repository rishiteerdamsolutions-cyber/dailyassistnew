# AHA — Install Guide

**No app store. No signing required. Works on Mac and Windows.**

AHA runs as a desktop app built on Python + pywebview. Because it is not sold through the App Store or Microsoft Store, your OS will show a one-time security warning. This is normal — follow the steps below to open it anyway.

---

## Subscribe first (Mac or Windows)

1. Open AHA locally (`start_companion.command` or `start.bat`) or visit **http://127.0.0.1:8000/subscribe** when the app is running.
2. **Sign in** with your dailyassist.xyz account (Firebase email or Google).
3. **Pay with Razorpay** (test mode uses ₹1 if `AHA_PLAN_CORE_MONTHLY_PAISE=100` in `.env`).
4. Go to **http://127.0.0.1:8000/download** and download the zip for your platform.
5. Install using the steps below; sign in again — your license syncs from the cloud.

You can also enter a license key manually in the app if support sent you one.

---

## Requirements (both platforms)

| | Minimum |
|-|---------|
| Python | 3.10+ (3.12 recommended) |
| Chrome | Any recent version (for Tier-2 web tasks) |
| RAM | 4 GB |
| Storage | 500 MB |

Download Python from **https://www.python.org/downloads/**

---

## macOS

### Step 1 — Download & extract

Download the AHA zip from [dailyassist.xyz](https://dailyassist.xyz) and unzip it anywhere (e.g. your Desktop or Documents folder).

### Step 2 — First launch

Double-click **`start_companion.command`**.

You will see:

> *"start_companion.command" cannot be opened because it is from an unidentified developer.*

**Click Cancel** (not "Move to Trash").

### Step 3 — Allow the app

Open **System Settings → Privacy & Security**.  
Scroll down — you will see:

> *"start_companion.command" was blocked because it is not from an identified developer.*

Click **Open Anyway**, then click **Open** in the dialog that follows.

> On older macOS you can also right-click the file → **Open** → **Open**.

### Step 4 — Subsequent launches

After the first approval, double-clicking `start_companion.command` will open AHA directly — no more warnings.

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

Download the AHA zip from [dailyassist.xyz](https://dailyassist.xyz).  
Right-click the zip → **Extract All** → choose a folder (e.g. `C:\AHA`).

### Step 2 — First launch

Double-click **`start.bat`**.

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

Tier-1 (social media posting) never uses your API key.

---

## Uninstall

Delete the AHA folder. Your local settings and vault content are in:

- **Mac:** `~/.aha/` and `~/Downloads/aha/`
- **Windows:** `%USERPROFILE%\.aha\` and `%USERPROFILE%\Downloads\aha\`

Delete those folders too for a complete removal.

---

## Support

Visit [dailyassist.xyz](https://dailyassist.xyz) or email support@dailyassist.xyz
