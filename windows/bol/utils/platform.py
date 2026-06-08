"""Windows-only platform helpers for the BOL system."""

from __future__ import annotations

import time
import webbrowser
from enum import Enum

import pyautogui


class OperatingSystem(str, Enum):
    WINDOWS = "Windows"


def get_os() -> OperatingSystem:
    return OperatingSystem.WINDOWS


def get_close_window_hotkey() -> tuple[str, ...]:
    return ("alt", "F4")


def get_close_app_hotkey() -> tuple[str, ...]:
    return ("alt", "F4")


def get_new_tab_hotkey() -> tuple[str, ...]:
    return ("ctrl", "t")


def get_address_bar_hotkey() -> tuple[str, ...]:
    return ("ctrl", "l")


def get_select_all_hotkey() -> tuple[str, ...]:
    return ("ctrl", "a")


def get_modifier_key() -> str:
    return "ctrl"


def is_macos() -> bool:
    return False


def is_windows() -> bool:
    return True


def get_chrome_window_bounds() -> tuple[int, int, int, int] | None:
    try:
        import pygetwindow as gw

        wins = gw.getWindowsWithTitle("Chrome")
        if not wins:
            return None
        win = wins[0]
        return win.left, win.top, win.width, win.height
    except Exception:
        return None


def navigate_chrome_url(url: str) -> bool:
    try:
        webbrowser.get("chrome").open(url)
    except Exception:
        webbrowser.open(url)
    time.sleep(2.0)
    return True


def maximize_chrome_window() -> None:
    try:
        import pygetwindow as gw

        wins = gw.getWindowsWithTitle("Chrome")
        if wins:
            win = wins[0]
            try:
                win.activate()
            except Exception:
                pass
            try:
                win.maximize()
            except Exception:
                pass
    except ImportError:
        pass
    time.sleep(0.5)
    pyautogui.press("f11")
    time.sleep(1.5)


def chrome_is_frontmost() -> bool:
    try:
        import pygetwindow as gw

        active = gw.getActiveWindow()
        if active is None:
            return True
        return "chrome" in (active.title or "").lower()
    except Exception:
        return True


def submit_file_dialog_path(media_path: str) -> bool:
    path = str(media_path)
    time.sleep(1.0)
    try:
        import pyperclip

        pyperclip.copy(path)
        pyautogui.hotkey("ctrl", "v")
    except ImportError:
        pyautogui.typewrite(path, interval=0.03)
    time.sleep(1.0)
    pyautogui.press("enter")
    return True


def upload_via_go_to_folder(media_path: str) -> None:
    path = str(media_path)
    try:
        import pyperclip

        pyperclip.copy(path)
        pyautogui.hotkey("ctrl", "v")
    except ImportError:
        pyautogui.typewrite(path, interval=0.03)
    time.sleep(1.0)
    pyautogui.press("enter")
    time.sleep(1.5)


def get_chrome_launch_command(binary_path: str, profile_args: list[str]) -> list[str]:
    return [binary_path] + profile_args
