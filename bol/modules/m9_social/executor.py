"""
Social Media Flow Executor.

Given a SocialFlow and task parameters (media_path, caption, etc.),
this executes each step in order using:
  1. VisionButtonLibrary template matching (primary)
  2. OCR text fallback (secondary)
  3. Verification after each step before proceeding

Zero footprint: pure OS mouse/keyboard, no JS injection.
"""

from __future__ import annotations

import time
import subprocess
import pyautogui
import numpy as np
import cv2
from pathlib import Path
from typing import Any, Optional
from bol.modules.m9_social.flows import (
    SocialFlow, Step, ActionType, detect_flow, FLOW_REGISTRY
)
from bol.modules.m3_visual.vision_buttons import VisionButtonLibrary
from bol.utils.logging import get_logger

logger = get_logger(__name__)

# ── Retina-safe pyautogui click ───────────────────────────────────────────────
# On Retina macs, pyautogui operates in LOGICAL pixels (same as mss capture).
# The AppleScript window bounds are also in logical pixels.
# So no extra scaling needed — just pass coordinates directly.

pyautogui.FAILSAFE = True
import random
# Remove static PAUSE so we can inject truly random, non-repetitive pauses manually
pyautogui.PAUSE = 0.01 

CLICK_DRIFT_OFFSET_X = 0   # calibrate if clicks still drift
CLICK_DRIFT_OFFSET_Y = 0


def _capture_screen() -> np.ndarray:
    """Capture full screen, return BGR numpy array."""
    import mss
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        arr = np.frombuffer(shot.raw, dtype=np.uint8).reshape(
            (shot.height, shot.width, 4)
        )
        import cv2
        return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)


def _chrome_bounds() -> tuple[int, int, int, int] | None:
    """Get Chrome window bounds via AppleScript. Returns (x, y, w, h) or None."""
    try:
        script = '''
        tell application "Google Chrome"
            if not (exists window 1) then return "none"
            set b to bounds of window 1
            return (item 1 of b) & "," & (item 2 of b) & "," & (item 3 of b) & "," & (item 4 of b)
        end tell
        '''
        result = subprocess.check_output(['osascript', '-e', script], timeout=2).decode().strip()
        if result == "none":
            return None
        x1, y1, x2, y2 = [int(v.strip()) for v in result.split(',')]
        return x1, y1, x2 - x1, y2 - y1
    except Exception:
        return None


def _bezier_curve(x0: int, y0: int, x3: int, y3: int, num_points: int = 20) -> list[tuple[int, int]]:
    """Generate a Cubic Bezier curve from (x0,y0) to (x3,y3) with random control points."""
    # Control points random offset (amplitude based on distance)
    dist = ((x3 - x0)**2 + (y3 - y0)**2)**0.5
    offset = max(10, int(dist * 0.2))
    
    x1 = x0 + random.randint(-offset, offset)
    y1 = y0 + random.randint(-offset, offset)
    x2 = x3 + random.randint(-offset, offset)
    y2 = y3 + random.randint(-offset, offset)
    
    points = []
    for i in range(num_points + 1):
        t = i / num_points
        x = (1-t)**3 * x0 + 3*(1-t)**2 * t * x1 + 3*(1-t)*t**2 * x2 + t**3 * x3
        y = (1-t)**3 * y0 + 3*(1-t)**2 * t * y1 + 3*(1-t)*t**2 * y2 + t**3 * y3
        points.append((int(x), int(y)))
    return points

def _execute_bezier_move(tx: int, ty: int, duration: float) -> None:
    """Move mouse to target using a Bezier curve."""
    cx, cy = pyautogui.position()
    num_points = random.randint(15, 30)
    points = _bezier_curve(cx, cy, tx, ty, num_points)
    
    sleep_time = duration / len(points)
    for px, py in points:
        pyautogui.moveTo(px, py, _pause=False)
        time.sleep(sleep_time)


def _human_click(x: int, y: int) -> None:
    """
    Click at (x, y) with a smooth Bezier curve move.
    Applies drift calibration offset.
    """
    tx = x + CLICK_DRIFT_OFFSET_X
    ty = y + CLICK_DRIFT_OFFSET_Y
    
    # Pre-action hesitation (non-repetitive)
    time.sleep(random.uniform(0.2, 0.6))
    
    # Move along a randomized Bezier curve
    duration = random.uniform(0.6, 1.2)
    _execute_bezier_move(tx, ty, duration)
    
    # Micro-pause before the actual click
    time.sleep(random.uniform(0.05, 0.2))
    pyautogui.click()
    logger.debug("Clicked (%d, %d)", tx, ty)
    
    # Post-action pause
    time.sleep(random.uniform(0.1, 0.4))


def _human_move(x: int, y: int) -> None:
    """
    Move mouse to (x, y) with a smooth Bezier curve without clicking.
    """
    tx = x + CLICK_DRIFT_OFFSET_X
    ty = y + CLICK_DRIFT_OFFSET_Y
    
    time.sleep(random.uniform(0.2, 0.5))
    duration = random.uniform(0.5, 1.0)
    _execute_bezier_move(tx, ty, duration)
    time.sleep(random.uniform(0.1, 0.3))

def _find_and_click(
    template: Optional[str],
    text_fallback: Optional[str],
    lib: VisionButtonLibrary,
    screenshot: np.ndarray,
    chrome_offset: tuple[int, int] = (0, 0),
    click_offset: tuple[int, int] = (0, 0),
) -> bool:
    """
    Try template match first, then OCR text fallback.
    Returns True if something was clicked.
    """
    import cv2

    # 1. Template match
    if template:
        match = lib.find(template, screenshot)
        if match:
            # Randomize click within the inner 50% of the bounding box to avoid clicking exact center
            rx = random.randint(-match.bbox.width // 4, match.bbox.width // 4) if match.bbox.width > 4 else 0
            ry = random.randint(-match.bbox.height // 4, match.bbox.height // 4) if match.bbox.height > 4 else 0
            cx = match.bbox.x + match.bbox.width // 2 + chrome_offset[0] + rx + click_offset[0]
            cy = match.bbox.y + match.bbox.height // 2 + chrome_offset[1] + ry + click_offset[1]
            _human_click(cx, cy)
            logger.info("Template match '%s' → clicked (%d, %d) conf=%.3f",
                        template, cx, cy, match.confidence)
            return True

    # 2. OCR text fallback
    if text_fallback:
        try:
            import pytesseract
            gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            inverted = cv2.bitwise_not(gray)
            
            needle_words = [w for w in text_fallback.lower().split() if len(w) > 2]
            if not needle_words:
                needle_words = [text_fallback.lower()]

            for img_variant in [gray, inverted]:
                data = pytesseract.image_to_data(
                    img_variant, output_type=pytesseract.Output.DICT, config='--psm 11'
                )
                for i, word in enumerate(data['text']):
                    w = word.strip().lower()
                    if w and int(data['conf'][i]) > 40:
                        # Check if any significant needle word is in the detected word
                        if any(nw in w for nw in needle_words) or (w in text_fallback.lower() and len(w) > 3):
                            rx = random.randint(-data['width'][i] // 4, data['width'][i] // 4) if data['width'][i] > 4 else 0
                            ry = random.randint(-data['height'][i] // 4, data['height'][i] // 4) if data['height'][i] > 4 else 0
                            x = data['left'][i] + data['width'][i] // 2 + chrome_offset[0] + rx + click_offset[0]
                            y = data['top'][i] + data['height'][i] // 2 + chrome_offset[1] + ry + click_offset[1]
                            _human_click(x, y)
                            logger.info("OCR fallback '%s' matched '%s' → clicked (%d, %d)", text_fallback, w, x, y)
                            return True
        except Exception as e:
            logger.warning("OCR fallback failed: %s", e)

    logger.warning("Could not find: template=%s, text=%s", template, text_fallback)
    return False


class SocialFlowExecutor:
    """
    Executes a SocialFlow step by step.

    Usage:
        executor = SocialFlowExecutor()
        result = executor.run("instagram_post", {
            "media_path": "/path/to/photo.jpg",
            "caption": "Hello world!",
        })
    """

    def __init__(self) -> None:
        self._lib = VisionButtonLibrary()

    def run(
        self,
        task_id: str,
        params: dict[str, Any],
        progress_callback=None,   # optional: fn(step_num, description) for UI updates
    ) -> dict[str, Any]:
        """
        Execute a social media posting flow.

        Parameters
        ----------
        task_id : str
            e.g. "instagram_post", "whatsapp_status"
        params : dict
            Task parameters:
              media_path (str): absolute path to media file (optional)
              caption (str): post caption/text (optional)
              tweet_text (str): tweet content for X (optional)
              message (str): WhatsApp DM message (optional)
              contact_name (str): WhatsApp DM recipient (optional)
        progress_callback : callable, optional
            Called as progress_callback(step_num, description, status)
        """
        flow = FLOW_REGISTRY.get(task_id)
        if not flow:
            return {"success": False, "error": f"Unknown task: {task_id}"}

        logger.info("Starting flow: %s (%d steps)", flow.task_id, len(flow.steps))
        results = []

        for step in flow.steps:
            desc = f"[Step {step.number}/{len(flow.steps)}] {step.description}"
            logger.info(desc)
            if progress_callback:
                progress_callback(step.number, step.description, "running")

            try:
                ok = self._execute_step(step, params, flow)
                if ok:
                    ok = self._verify_step_confirmation(step)
            except Exception as e:
                logger.error("Step %d failed: %s", step.number, e)
                ok = False

            results.append({
                "step": step.number,
                "description": step.description,
                "success": ok,
            })

            if not ok and step.action != ActionType.CONFIRM_DONE:
                logger.error("Flow aborted at step %d", step.number)
                return {
                    "success": False,
                    "stopped_at_step": step.number,
                    "error": f"Could not complete: {step.description}",
                    "steps": results,
                }

            # Minimal stability pause between steps (polling handles the real waiting now)
            time.sleep(0.5)

        logger.info("Flow '%s' completed successfully.", flow.task_id)
        if progress_callback:
            progress_callback(len(flow.steps), "Done", "complete")

        return {"success": True, "steps": results}

    def _get_cropped_screen_and_offset(self, step: Step) -> tuple[np.ndarray, tuple[int, int]]:
        screenshot = _capture_screen()
        bounds = _chrome_bounds()
        offset = (0, 0)
        
        # Crop to Chrome window bounding box
        if bounds and step.action != ActionType.OS_OPEN:
            x, y, w, h = bounds
            sh, sw, _ = screenshot.shape
            x = max(0, min(x, sw - 1))
            y = max(0, min(y, sh - 1))
            w = max(1, min(w, sw - x))
            h = max(1, min(h, sh - y))
            
            screenshot = screenshot[y : y + h, x : x + w]
            offset = (x, y)
            
        return screenshot, offset

    def _wait_and_find_and_click(self, step: Step, max_wait: float = 15.0) -> bool:
        start_time = time.time()
        click_offset = (getattr(step, 'offset_x', 0), getattr(step, 'offset_y', 0))
        while time.time() - start_time < max_wait:
            screenshot, offset = self._get_cropped_screen_and_offset(step)
            if _find_and_click(step.template, step.text_fallback, self._lib, screenshot, offset, click_offset):
                return True
            time.sleep(0.5)
        logger.warning(f"Timeout ({max_wait}s) waiting for element: {step.description}")
        return False

    def _verify_step_confirmation(self, step: Step, max_wait: float = 12.0) -> bool:
        """Wait until confirm_template or confirm_text appears after a step."""
        if not step.confirm_template and not step.confirm_text:
            return True

        start = time.time()
        needle = (step.confirm_text or "").lower()

        while time.time() - start < max_wait:
            screenshot, _offset = self._get_cropped_screen_and_offset(step)

            if step.confirm_template:
                match = self._lib.find(step.confirm_template, screenshot)
                if match:
                    logger.info(
                        "Step %d confirmed via template '%s' (conf=%.3f)",
                        step.number,
                        step.confirm_template,
                        match.confidence,
                    )
                    return True

            if needle:
                try:
                    import pytesseract

                    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
                    text = pytesseract.image_to_string(gray, config="--psm 11").lower()
                    if needle in text:
                        logger.info(
                            "Step %d confirmed via text '%s'",
                            step.number,
                            step.confirm_text,
                        )
                        return True
                except Exception as exc:
                    logger.warning("Confirmation OCR failed: %s", exc)

            time.sleep(0.5)

        logger.warning(
            "Step %d confirmation timeout: template=%s text=%s",
            step.number,
            step.confirm_template,
            step.confirm_text,
        )
        return False

    def _execute_step(self, step: Step, params: dict, flow: SocialFlow) -> bool:
        """Execute one step and return True if successful."""

        if step.action == ActionType.CONFIRM_DONE:
            return True  # nothing to do — flow is complete

        if step.optional_if_no_key and not params.get(step.optional_if_no_key):
            logger.info("Skipping optional step %d (missing key: %s)", step.number, step.optional_if_no_key)
            return True

        if getattr(step, 'skip_if_key', None) and params.get(step.skip_if_key):
            logger.info("Skipping step %d (key is present: %s)", step.number, step.skip_if_key)
            return True

        if step.action == ActionType.NAVIGATE:
            url = step.url or ""
            logger.info("Navigating Chrome to: %s", url)
            subprocess.run(["open", "-a", "Google Chrome", url])
            time.sleep(2.0)  # Wait briefly for Chrome to launch
            
            # Maximize the window natively (respecting the macOS dock) to prevent elements from being hidden
            applescript = """
            tell application "Google Chrome"
                activate
                set zoomed of front window to true
            end tell
            """
            subprocess.run(["osascript", "-e", applescript])
            time.sleep(0.5)
            return True

        if step.action == ActionType.WAIT:
            time.sleep(step.wait_seconds)
            return True

        # For click, type, upload, os_open — capture screen first
        screenshot, offset = self._get_cropped_screen_and_offset(step)

        if step.action == ActionType.CLICK:
            return self._wait_and_find_and_click(step, max_wait=max(15.0, step.wait_seconds))

        if step.action == ActionType.HOVER_AND_VERIFY:
            if not step.hover_template or not step.hover_verify_text:
                logger.error("HOVER_AND_VERIFY requires hover_template and hover_verify_text")
                return False
                
            import pytesseract
            verify_text = step.hover_verify_text.lower()
            
            start_time = time.time()
            max_wait = max(15.0, step.wait_seconds)
            
            while time.time() - start_time < max_wait:
                screenshot, offset = self._get_cropped_screen_and_offset(step)
                matches = self._lib.find_all(step.hover_template, screenshot)
                
                if not matches:
                    # Fallback to direct OCR if template isn't found
                    if _find_and_click(None, step.hover_verify_text, self._lib, screenshot, offset):
                        return True
                    time.sleep(0.5)
                    continue
                    
                for match in matches:
                    cx = match.bbox.center_x + offset[0]
                    cy = match.bbox.center_y + offset[1]
                    logger.info("HOVER_AND_VERIFY: Hovering over candidate at (%d, %d)", cx, cy)
                    _human_move(cx, cy)
                    
                    # Wait for hover tooltip animation
                    time.sleep(0.8)
                    
                    hover_screen = _capture_screen()
                    gray = cv2.cvtColor(hover_screen, cv2.COLOR_BGR2GRAY)
                    text_data_1 = pytesseract.image_to_string(gray, config='--psm 11').lower()
                    
                    inverted = cv2.bitwise_not(gray)
                    text_data_2 = pytesseract.image_to_string(inverted, config='--psm 11').lower()
                    
                    if verify_text in text_data_1 or verify_text in text_data_2:
                        logger.info("HOVER_AND_VERIFY: Verified '%s' on screen. Clicking!", step.hover_verify_text)
                        pyautogui.click()
                        return True
                        
                time.sleep(0.5)
                
            logger.warning("HOVER_AND_VERIFY: Timeout waiting for hover verify text '%s'", step.hover_verify_text)
            return False

        if step.action == ActionType.TYPE:
            text_key = step.type_text_key or ""
            text = params.get(text_key, "")
            if not text:
                logger.warning("No text provided for key '%s', skipping type step", text_key)
                return True  # optional step
                
            # If step has a template or text fallback, click it first to focus the text area!
            if step.template or step.text_fallback:
                logger.info("TYPE Action: Finding and clicking input field first using template/OCR.")
                self._wait_and_find_and_click(step, max_wait=5.0)
            
            # Click to focus the text area first (find it by context)
            time.sleep(random.uniform(0.5, 1.0))
            
            # Type character by character with a truly randomized gap between EVERY key
            for char in text:
                pyautogui.typewrite(char)
                time.sleep(random.uniform(0.04, 0.18))
                
            # Post-typing pause
            time.sleep(random.uniform(0.3, 0.7))
            return True

        if step.action == ActionType.PRESS_ENTER:
            logger.info("PRESS_ENTER Action: pressing return key natively.")
            time.sleep(random.uniform(0.5, 1.0))
            pyautogui.press('return')
            time.sleep(random.uniform(0.5, 1.0))
            return True

        if step.action == ActionType.OS_OPEN:
            # The OS file picker is open. If media_path given, type it in first.
            media_path = params.get(step.file_key or "media_path", "")
            if media_path:
                # Use Cmd+Shift+G to navigate to path in macOS file dialog
                time.sleep(0.5)
                pyautogui.hotkey('command', 'shift', 'g')
                time.sleep(0.5)
                pyautogui.typewrite(str(media_path), interval=0.03)
                time.sleep(0.5)
                pyautogui.press('return')
                time.sleep(1.0)
                pyautogui.press('return')  # confirm selection
                time.sleep(1.5) # Wait for dialog to close and browser to process upload
                return True # Dialog is closed, we are done with this step!

            # If no media path (or we want to click Open manually), do it here
            return self._wait_and_find_and_click(step, max_wait=max(15.0, step.wait_seconds))

        if step.action == ActionType.UPLOAD:
            # Upload = click trigger + OS_OPEN combined
            clicked = self._wait_and_find_and_click(step, max_wait=max(15.0, step.wait_seconds))
            if not clicked:
                return False
            time.sleep(1.5)
            # Handle file dialog
            media_path = params.get(step.file_key or "media_path", "")
            if media_path:
                pyautogui.hotkey('command', 'shift', 'g')
                time.sleep(0.5)
                pyautogui.typewrite(str(media_path), interval=0.03)
                pyautogui.press('return')
                time.sleep(0.8)
                pyautogui.press('return')
                time.sleep(0.5)
            return True

        return False


# ─── Convenience function for the agent to call ───────────────────────────────
_executor: Optional[SocialFlowExecutor] = None

def get_executor() -> SocialFlowExecutor:
    global _executor
    if _executor is None:
        _executor = SocialFlowExecutor()
    return _executor


def run_social_task(task_id: str, params: dict, progress_callback=None) -> dict:
    """Top-level entry point. Called by the agent orchestrator."""
    return get_executor().run(task_id, params, progress_callback)


def detect_and_run(user_text: str, params: dict, progress_callback=None) -> Optional[dict]:
    """
    Auto-detect the social media task from user text and run it.
    Returns None if no social media task detected.
    """
    flow = detect_flow(user_text)
    if flow is None:
        return None
    return run_social_task(flow.task_id, params, progress_callback)
