"""
Connect Bluetooth via System Settings — honest outcomes only.

Success = verified connected (system_profiler on Mac, OCR on screen as backup).
Never claim "clicked Connect" unless we verify the device actually connected.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Callable, Optional

import cv2

from bol.modules.m9_social.executor import _capture_screen, _human_click
from bol.utils.logging import get_logger

logger = get_logger(__name__)

ProgressFn = Callable[[int, str, str], None]

_IS_MAC = sys.platform == "darwin"
_IS_WIN = sys.platform == "win32"

_ROW_Y_SLACK = 32
_MAIN_PANEL_X_FRAC = 0.30
_DEVICE_LIST_Y_MIN_FRAC = 0.26

_CHROME_LABELS = frozenset({
    "bluetooth", "settings", "system settings", "connect", "connected",
    "not connected", "disconnect", "nearby", "devices", "my devices",
    "personal hotspot", "turn on", "turn off", "on", "off", "search",
    "apple id", "wifi", "network", "control center", "spotlight",
})


@dataclass
class TextBox:
    x: int
    y: int
    w: int
    h: int
    text: str
    conf: int

    @property
    def cx(self) -> int:
        return self.x + self.w // 2

    @property
    def cy(self) -> int:
        return self.y + self.h // 2

    @property
    def right(self) -> int:
        return self.x + self.w


@dataclass
class ConnectAttempt:
    actions: list[str] = field(default_factory=list)
    click_performed: bool = False

    def log(self, action: str) -> None:
        self.actions.append(action)
        logger.info("[BT] %s", action)


def _names_match(requested: str, found: str) -> bool:
    a = requested.strip().lower()
    b = found.strip().lower()
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.72


def _focus_bluetooth_settings() -> None:
    """Clicks must land on System Settings, not the AHA companion window."""
    if _IS_MAC:
        subprocess.run(
            ["osascript", "-e", 'tell application "System Settings" to activate'],
            capture_output=True,
            timeout=5,
        )
        time.sleep(0.9)


def _open_bluetooth_settings() -> bool:
    if _IS_MAC:
        for cmd in (
            ["open", "x-apple.systempreferences:com.apple.BluetoothSettings"],
            ["open", "-b", "com.apple.systempreferences", "/System/Library/PreferencePanes/Bluetooth.prefPane"],
        ):
            r = subprocess.run(cmd, capture_output=True, timeout=10)
            if r.returncode == 0:
                _focus_bluetooth_settings()
                return True
        return False
    if _IS_WIN:
        r = subprocess.run(["cmd", "/c", "start", "ms-settings:bluetooth"], timeout=10)
        return r.returncode == 0
    return False


def _mac_verify_connected(device_name: str) -> bool:
    """
    Ground truth on macOS — no guessing. Uses built-in system_profiler.
    """
    try:
        proc = subprocess.run(
            ["system_profiler", "SPBluetoothDataType"],
            capture_output=True,
            text=True,
            timeout=35,
        )
        text = proc.stdout or ""
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("system_profiler failed: %s", exc)
        return False

    section: Optional[str] = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if lower == "connected:":
            section = "connected"
            continue
        if lower == "not connected:":
            section = "not_connected"
            continue
        if stripped.endswith(":") and not line.startswith("\t\t"):
            if "connected" in lower and "not" not in lower:
                section = "connected"
            continue

        if section == "connected" and _names_match(device_name, stripped.rstrip(":")):
            return True
        if section == "not_connected" and _names_match(device_name, stripped.rstrip(":")):
            return False

    return False


def _wait_for_verified_connection(device_name: str, *, timeout: float = 18.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _IS_MAC and _mac_verify_connected(device_name):
            return True
        if _ocr_shows_connected(device_name):
            return True
        time.sleep(1.5)
    return False


def _is_settings_chrome(text: str) -> bool:
    t = text.strip().lower()
    if not t or t in _CHROME_LABELS or t == "bluetooth":
        return True
    return False


def _name_match_score(text: str, device_name: str) -> float:
    a = device_name.strip().lower()
    b = text.strip().lower()
    if not a or not b:
        return 0.0
    if a == b or a in b or b in a:
        return 0.95
    ratio = SequenceMatcher(None, a, b).ratio()
    words = [w for w in re.split(r"[\s\-_]+", a) if len(w) >= 4]
    if words and all(w in b for w in words):
        return max(ratio, 0.85)
    return ratio


def _mac_connect_via_accessibility(device_name: str, attempt: ConnectAttempt) -> bool:
    safe = device_name.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
tell application "System Settings" to activate
delay 2
tell application "System Events"
    tell process "System Settings"
        set frontmost to true
        if (count of windows) is 0 then return "no_window"
        return my findAndConnect(window 1, "{safe}")
    end tell
end tell

on elementText(el)
    set t to ""
    try
        set t to value of el as text
    end try
    if t is missing value or t is "" then
        try
            set t to name of el as text
        end try
    end if
    if t is missing value then return ""
    return t
end elementText

on nameMatches(elText, deviceName)
    return elText contains deviceName
end nameMatches

on findAndConnect(el, deviceName)
    set t to my elementText(el)
    if my nameMatches(t, deviceName) then
        try
            click button "Connect" of el
            return "clicked"
        end try
    end if
    try
        repeat with connBtn in (every button of el whose name is "Connect")
            set parentText to my elementText(el)
            if my nameMatches(parentText, deviceName) then
                click connBtn
                return "clicked"
            end if
        end repeat
    end try
    try
        repeat with child in (UI elements of el)
            set r to my findAndConnect(child, deviceName)
            if r is "clicked" then return r
        end repeat
    end try
    return "miss"
end findAndConnect
'''
    try:
        out = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=45,
        )
        result = (out.stdout or "").strip()
        err = (out.stderr or "").strip()
        logger.info("AX result=%r stderr=%r", result, err)
        if "assistive" in err.lower() or "accessibility" in err.lower():
            attempt.log("accessibility_denied — enable AHA in Privacy → Accessibility")
            return False
        if result == "clicked":
            attempt.log("accessibility: clicked Connect button")
            attempt.click_performed = True
            return True
        attempt.log("accessibility: Connect button not found in UI tree")
        return False
    except (subprocess.TimeoutExpired, OSError) as exc:
        attempt.log(f"accessibility error: {exc}")
        return False


def _extract_word_boxes(screen_bgr) -> list[TextBox]:
    try:
        import pytesseract
        from pytesseract import Output
    except ImportError:
        return []

    boxes: list[TextBox] = []
    gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
    for img in (gray, cv2.bitwise_not(gray)):
        data = pytesseract.image_to_data(img, output_type=Output.DICT, config="--psm 11")
        for i, raw in enumerate(data.get("text", [])):
            text = (raw or "").strip()
            if not text or _is_settings_chrome(text):
                continue
            try:
                conf = int(float(data["conf"][i]))
            except (ValueError, TypeError):
                conf = 0
            if conf < 35:
                continue
            w, h = int(data["width"][i]), int(data["height"][i])
            if w < 2 or h < 2:
                continue
            boxes.append(
                TextBox(
                    x=int(data["left"][i]),
                    y=int(data["top"][i]),
                    w=w,
                    h=h,
                    text=text,
                    conf=conf,
                )
            )
        if boxes:
            break
    return boxes


def _merge_boxes(group: list[TextBox]) -> TextBox:
    x1 = min(b.x for b in group)
    y1 = min(b.y for b in group)
    x2 = max(b.right for b in group)
    y2 = max(b.y + b.h for b in group)
    text = " ".join(b.text for b in sorted(group, key=lambda b: b.x))
    conf = max(b.conf for b in group)
    return TextBox(x=x1, y=y1, w=x2 - x1, h=y2 - y1, text=text, conf=conf)


def _group_by_line(boxes: list[TextBox], slack: int = 12) -> list[list[TextBox]]:
    if not boxes:
        return []
    sorted_boxes = sorted(boxes, key=lambda b: (b.cy, b.x))
    lines: list[list[TextBox]] = []
    for box in sorted_boxes:
        for line in lines:
            if abs(box.cy - line[0].cy) <= slack:
                line.append(box)
                break
        else:
            lines.append([box])
    return lines


def _in_device_list_zone(box: TextBox, screen_w: int, screen_h: int) -> bool:
    if box.x < int(screen_w * _MAIN_PANEL_X_FRAC):
        return False
    if box.y < int(screen_h * _DEVICE_LIST_Y_MIN_FRAC):
        return False
    if box.y > int(screen_h * 0.92):
        return False
    return True


def _find_device_box(
    boxes: list[TextBox], device_name: str, screen_w: int, screen_h: int,
) -> Optional[TextBox]:
    candidates: list[tuple[float, TextBox]] = []
    in_zone = [b for b in boxes if _in_device_list_zone(b, screen_w, screen_h)]

    for line in _group_by_line(in_zone):
        name_bits = [b for b in line if b.text.strip().lower() != "connect"]
        if not name_bits:
            continue
        merged = _merge_boxes(name_bits)
        if _is_settings_chrome(merged.text):
            continue
        score = _name_match_score(merged.text, device_name)
        if score >= 0.55:
            candidates.append((score, merged))

    for b in in_zone:
        if _is_settings_chrome(b.text):
            continue
        score = _name_match_score(b.text, device_name)
        if score >= 0.55:
            candidates.append((score, b))

    if not candidates:
        return None
    candidates.sort(key=lambda t: (-t[0], t[1].y))
    return candidates[0][1]


def _same_row(a: TextBox, b: TextBox) -> bool:
    return abs(a.cy - b.cy) <= _ROW_Y_SLACK


def _find_connect_on_device_row(
    boxes: list[TextBox], device: TextBox, screen_w: int, screen_h: int,
) -> Optional[TextBox]:
    candidates: list[tuple[int, int, TextBox]] = []
    for b in boxes:
        if b.text.strip().lower() != "connect":
            continue
        if not _in_device_list_zone(b, screen_w, screen_h):
            continue
        if not _same_row(device, b):
            continue
        if b.x < device.right - 20 or b.x > device.right + 420:
            continue
        candidates.append((abs(b.cy - device.cy), b.x, b))
    if not candidates:
        return None
    candidates.sort(key=lambda t: (t[0], t[1]))
    return candidates[0][2]


def _find_connected_on_device_row(
    boxes: list[TextBox], device: TextBox, screen_w: int, screen_h: int,
) -> bool:
    for b in boxes:
        bl = b.text.lower()
        if "connected" not in bl or "not connected" in bl:
            continue
        if not _in_device_list_zone(b, screen_w, screen_h):
            continue
        if _same_row(device, b) and b.x >= device.x:
            return True
    return False


def _ocr_shows_connected(device_name: str) -> bool:
    screen = _capture_screen()
    h, w = screen.shape[:2]
    boxes = _extract_word_boxes(screen)
    device = _find_device_box(boxes, device_name, w, h)
    if device and _find_connected_on_device_row(boxes, device, w, h):
        return True
    return False


def _scroll_device_list(screen_w: int, screen_h: int) -> None:
    import pyautogui

    _focus_bluetooth_settings()
    pyautogui.scroll(-5, x=int(screen_w * 0.58), y=int(screen_h * 0.58))
    time.sleep(0.6)


def _vision_click_connect(device_name: str, attempt: ConnectAttempt) -> bool:
    """Returns True only if a click was physically sent to the Connect target."""
    for scroll_try in range(6):
        _focus_bluetooth_settings()
        screen = _capture_screen()
        h, w = screen.shape[:2]
        boxes = _extract_word_boxes(screen)
        device = _find_device_box(boxes, device_name, w, h)

        if not device:
            attempt.log(f"vision: device row not found (scroll {scroll_try + 1}/6)")
            if scroll_try < 5:
                _scroll_device_list(w, h)
            continue

        attempt.log(f"vision: found device row {device.text!r} at y={device.y}")

        if _find_connected_on_device_row(boxes, device, w, h):
            attempt.log("vision: row already shows Connected")
            return False

        connect_btn = _find_connect_on_device_row(boxes, device, w, h)
        _focus_bluetooth_settings()
        if connect_btn:
            attempt.log(f"vision: clicking Connect at ({connect_btn.cx},{connect_btn.cy})")
            _human_click(connect_btn.cx, connect_btn.cy)
            attempt.click_performed = True
            return True

        btn_x = min(device.right + 100, w - 50)
        btn_y = device.cy
        attempt.log(f"vision: Connect OCR miss — clicking row button area ({btn_x},{btn_y})")
        _human_click(btn_x, btn_y)
        attempt.click_performed = True
        return True

    return False


def _failure_message(device_name: str, attempt: ConnectAttempt) -> str:
    steps = "; ".join(attempt.actions) if attempt.actions else "no actions recorded"
    base = (
        f"Could not confirm that “{device_name}” connected. "
        f"What I tried: {steps}. "
    )
    if not attempt.click_performed:
        base += (
            "I never reached a Connect click — check that the device appears in the list "
            "below the Bluetooth title (not just the sidebar). "
        )
    else:
        base += (
            "A click was sent but macOS did not report the device as connected afterward. "
        )
    base += (
        "Ensure System Settings is visible, AHA has Accessibility + Screen Recording, "
        "and wake the earbuds if they are asleep."
    )
    return base


def connect_via_system_settings(
    device_name: str,
    progress: Optional[ProgressFn] = None,
) -> dict[str, object]:
    device_name = (device_name or "").strip()
    if not device_name:
        return {"success": False, "message": "Device name is required (e.g. Noise Buds)."}

    attempt = ConnectAttempt()

    def _prog(step: int, desc: str, status: str = "running") -> None:
        if progress:
            progress(step, desc, status)

    _prog(1, "Opening Bluetooth settings")
    if not _open_bluetooth_settings():
        return {"success": False, "message": "Could not open Bluetooth settings on this OS."}
    attempt.log("opened Bluetooth settings")

    time.sleep(2.5)

    if _IS_MAC and _mac_verify_connected(device_name):
        return {
            "success": True,
            "message": f"{device_name} is already connected.",
            "verified": True,
        }

    # ── Mac accessibility click ───────────────────────────────────────────
    if _IS_MAC:
        _prog(2, f"Clicking Connect for {device_name} (System Settings UI)")
        if _mac_connect_via_accessibility(device_name, attempt):
            _prog(3, "Verifying connection with macOS")
            if _wait_for_verified_connection(device_name):
                return {
                    "success": True,
                    "message": f"Verified: {device_name} is connected.",
                    "verified": True,
                }
            attempt.log("accessibility click did not result in verified connection")

    # ── Vision click (Settings must be frontmost) ─────────────────────────
    _prog(2, f"Finding {device_name} in the device list")
    if _vision_click_connect(device_name, attempt):
        _prog(3, "Verifying connection")
        if _wait_for_verified_connection(device_name):
            return {
                "success": True,
                "message": f"Verified: {device_name} is connected.",
                "verified": True,
            }
        attempt.log("vision click did not result in verified connection")

    return {
        "success": False,
        "message": _failure_message(device_name, attempt),
        "verified": False,
    }
