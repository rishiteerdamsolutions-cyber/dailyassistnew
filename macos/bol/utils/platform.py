"""macOS-only platform helpers for the BOL system."""

from __future__ import annotations

import subprocess
import time
from enum import Enum

import pyautogui


class OperatingSystem(str, Enum):
    MACOS = "Darwin"


def get_os() -> OperatingSystem:
    return OperatingSystem.MACOS


def get_close_window_hotkey() -> tuple[str, ...]:
    return ("command", "w")


def get_close_app_hotkey() -> tuple[str, ...]:
    return ("command", "q")


def get_new_tab_hotkey() -> tuple[str, ...]:
    return ("command", "t")


def get_address_bar_hotkey() -> tuple[str, ...]:
    return ("command", "l")


def get_select_all_hotkey() -> tuple[str, ...]:
    return ("command", "a")


def get_modifier_key() -> str:
    return "command"


def is_macos() -> bool:
    return True


def is_windows() -> bool:
    return False


def get_chrome_window_bounds() -> tuple[int, int, int, int] | None:
    script = '''
    tell application "Google Chrome"
        if not (exists window 1) then return "none"
        set b to bounds of window 1
        return (item 1 of b) & "," & (item 2 of b) & "," & (item 3 of b) & "," & (item 4 of b)
    end tell
    '''
    try:
        result = subprocess.check_output(
            ["osascript", "-e", script], timeout=2
        ).decode().strip()
        if result == "none":
            return None
        x1, y1, x2, y2 = [int(v.strip()) for v in result.split(",")]
        return x1, y1, x2 - x1, y2 - y1
    except Exception:
        return None


def navigate_chrome_url(url: str) -> bool:
    applescript = f'''
    tell application "Google Chrome"
        activate
        open location "{url}"
        delay 1
        repeat 20 times
            if not (loading of active tab of front window) then exit repeat
            delay 0.5
        end repeat
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", applescript], check=True)
        time.sleep(1.0)
        return True
    except Exception:
        return False


def maximize_chrome_window() -> None:
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "Google Chrome" to activate'],
            check=False,
        )
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "command", "f")
        time.sleep(1.5)
    except Exception:
        pass


def chrome_is_frontmost() -> bool:
    try:
        script = (
            'tell application "System Events" to get name of first '
            "application process whose frontmost is true"
        )
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True
        )
        front_app = result.stdout.strip()
        return not front_app or "Google Chrome" in front_app
    except Exception:
        return True


def submit_file_dialog_path(media_path: str) -> bool:
    path = str(media_path)
    try:
        import pyperclip

        pyperclip.copy(path)
        paste_hotkey = ("command", "v")
    except ImportError:
        paste_hotkey = None

    time.sleep(2.5)
    pyautogui.hotkey("command", "shift", "g")
    time.sleep(1.5)
    if paste_hotkey:
        pyautogui.hotkey(*paste_hotkey)
        time.sleep(0.5)
    else:
        pyautogui.typewrite(path, interval=0.03)
        time.sleep(0.5)
    pyautogui.press("return")
    time.sleep(1.5)
    pyautogui.press("return")
    time.sleep(2.0)
    return True


def upload_via_go_to_folder(media_path: str) -> None:
    path = str(media_path)
    pyautogui.hotkey("command", "shift", "g")
    time.sleep(1.0)
    pyautogui.typewrite(path, interval=0.03)
    time.sleep(0.5)
    pyautogui.press("return")
    time.sleep(1.5)
    pyautogui.press("return")
    time.sleep(1.5)


def get_chrome_launch_command(binary_path: str, profile_args: list[str]) -> list[str]:
    return ["open", "-a", "Google Chrome", "--args"] + profile_args
