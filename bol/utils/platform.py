"""
Platform detection utilities for the BOL system.

Provides OS-specific helpers for input injection,
browser management, and hotkey mapping.
"""

from __future__ import annotations

import platform
from enum import Enum


class OperatingSystem(str, Enum):
    """Supported operating systems."""

    MACOS = "Darwin"
    WINDOWS = "Windows"
    LINUX = "Linux"


def get_os() -> OperatingSystem:
    """Detect the current operating system."""
    system = platform.system()
    try:
        return OperatingSystem(system)
    except ValueError:
        raise RuntimeError(f"Unsupported operating system: {system}")


def get_close_window_hotkey() -> tuple[str, ...]:
    """
    Return the OS-appropriate hotkey sequence to close the current window.

    Returns
    -------
    tuple[str, ...]
        Key names for pyautogui.hotkey().
    """
    os = get_os()
    if os == OperatingSystem.MACOS:
        return ("command", "w")
    elif os == OperatingSystem.WINDOWS:
        return ("alt", "F4")
    return ("alt", "F4")


def get_close_app_hotkey() -> tuple[str, ...]:
    """
    Return the OS-appropriate hotkey sequence to quit the application.

    Returns
    -------
    tuple[str, ...]
        Key names for pyautogui.hotkey().
    """
    os = get_os()
    if os == OperatingSystem.MACOS:
        return ("command", "q")
    elif os == OperatingSystem.WINDOWS:
        return ("alt", "F4")
    return ("alt", "F4")


def get_new_tab_hotkey() -> tuple[str, ...]:
    """Return the OS-appropriate hotkey for opening a new browser tab."""
    os = get_os()
    if os == OperatingSystem.MACOS:
        return ("command", "t")
    return ("ctrl", "t")


def get_address_bar_hotkey() -> tuple[str, ...]:
    """Return the OS-appropriate hotkey for focusing the address bar."""
    os = get_os()
    if os == OperatingSystem.MACOS:
        return ("command", "l")
    return ("ctrl", "l")


def get_select_all_hotkey() -> tuple[str, ...]:
    """Return the OS-appropriate hotkey for select-all."""
    os = get_os()
    if os == OperatingSystem.MACOS:
        return ("command", "a")
    return ("ctrl", "a")


def get_modifier_key() -> str:
    """Return the primary modifier key name for the current OS."""
    os = get_os()
    if os == OperatingSystem.MACOS:
        return "command"
    return "ctrl"


def is_macos() -> bool:
    return get_os() == OperatingSystem.MACOS


def is_windows() -> bool:
    return get_os() == OperatingSystem.WINDOWS


def get_chrome_window_bounds() -> tuple[int, int, int, int] | None:
    """Return Chrome window (x, y, width, height) in logical pixels, or None."""
    if is_macos():
        import subprocess

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

    if is_windows():
        try:
            import pygetwindow as gw

            wins = gw.getWindowsWithTitle("Chrome")
            if not wins:
                return None
            win = wins[0]
            return win.left, win.top, win.width, win.height
        except Exception:
            return None

    return None


def navigate_chrome_url(url: str) -> bool:
    """Open *url* in Chrome and wait for the active tab to finish loading."""
    import subprocess
    import time

    if is_macos():
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

    if is_windows():
        import webbrowser

        try:
            webbrowser.get("chrome").open(url)
        except Exception:
            webbrowser.open(url)
        time.sleep(2.0)
        return True

    return False


def maximize_chrome_window() -> None:
    """Bring Chrome to the foreground and maximize for posting flows."""
    import subprocess
    import time

    import pyautogui

    if is_macos():
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
        return

    if is_windows():
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
    """True when Chrome appears to be the focused application."""
    if is_macos():
        import subprocess

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

    if is_windows():
        try:
            import pygetwindow as gw

            active = gw.getActiveWindow()
            if active is None:
                return True
            return "chrome" in (active.title or "").lower()
        except Exception:
            return True

    return True


def submit_file_dialog_path(media_path: str) -> bool:
    """Paste *media_path* into the native file picker and confirm."""
    import time

    import pyautogui

    path = str(media_path)
    try:
        import pyperclip

        pyperclip.copy(path)
        paste_hotkey = ("command", "v") if is_macos() else ("ctrl", "v")
    except ImportError:
        pyperclip = None
        paste_hotkey = None

    if is_macos():
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

    if is_windows():
        time.sleep(1.0)
        if paste_hotkey:
            pyautogui.hotkey(*paste_hotkey)
        else:
            pyautogui.typewrite(path, interval=0.03)
        time.sleep(1.0)
        pyautogui.press("enter")
        return True

    return False


def upload_via_go_to_folder(media_path: str) -> None:
    """Mac Go-to-Folder upload fallback used after clicking an upload trigger."""
    import time

    import pyautogui

    path = str(media_path)
    if is_macos():
        pyautogui.hotkey("command", "shift", "g")
        time.sleep(1.0)
        pyautogui.typewrite(path, interval=0.03)
        time.sleep(0.5)
        pyautogui.press("return")
        time.sleep(1.5)
        pyautogui.press("return")
        time.sleep(1.5)
        return

    if is_windows():
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
    """
    Build the command to launch Chrome with a specific profile.

    Parameters
    ----------
    binary_path : str
        Path to the Chrome binary.
    profile_args : list[str]
        Chrome command-line arguments for profile selection.

    Returns
    -------
    list[str]
        Complete command list for subprocess or os.system.
    """
    os = get_os()
    if os == OperatingSystem.MACOS:
        # On macOS, use 'open -a' to launch the .app bundle
        return ["open", "-a", "Google Chrome", "--args"] + profile_args
    return [binary_path] + profile_args
