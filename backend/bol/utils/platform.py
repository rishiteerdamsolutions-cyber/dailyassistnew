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
