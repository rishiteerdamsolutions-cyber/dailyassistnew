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


def _clamp_to_bounds(x: int, y: int) -> tuple[int, int]:
    """Force an (x,y) coordinate to stay strictly inside the Chrome window."""
    bounds = _chrome_bounds()
    if not bounds: return x, y
    bx, by, bw, bh = bounds
    # Keep it at least 2 pixels away from the absolute edge to avoid triggering hot corners/dock
    cx = max(bx + 2, min(x, bx + bw - 2))
    cy = max(by + 2, min(y, by + bh - 2))
    return cx, cy

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
        # Clamp every intermediate point
        points.append(_clamp_to_bounds(int(x), int(y)))
    return points

def _yield_if_human_override(expected_x: int, expected_y: int) -> tuple[int, int]:
    """Check if human grabbed the mouse. If so, yield until they stop."""
    import math
    cx, cy = pyautogui.position()
    dist = math.hypot(cx - expected_x, cy - expected_y)
    
    if dist > 20: # 20 pixel threshold for human interference
        logger.warning(f"HUMAN OVERRIDE DETECTED! Mouse drifted {dist:.1f}px from expected. Yielding...")
        # Wait until mouse stops moving
        last_hx, last_hy = cx, cy
        stable_count = 0
        while stable_count < 10: # Wait for 1 second of complete stability
            time.sleep(0.1)
            nx, ny = pyautogui.position()
            if abs(nx - last_hx) < 2 and abs(ny - last_hy) < 2:
                stable_count += 1
            else:
                stable_count = 0 # reset if they keep moving
            last_hx, last_hy = nx, ny
            
        logger.info("Human has released the mouse. Resuming from new position...")
        return last_hx, last_hy
        
    return cx, cy

def _execute_bezier_move(tx: int, ty: int, duration: float) -> None:
    """Move mouse to target using a Bezier curve with a waypoint (installment)."""
    cx, cy = pyautogui.position()
    
    # Generate a waypoint 30-80 pixels away from the final target to create hesitation
    angle = random.uniform(0, 2 * 3.14159)
    dist = random.uniform(30, 80)
    wx = int(tx + dist * np.cos(angle))
    wy = int(ty + dist * np.sin(angle))
    
    # Clamp waypoint to ensure the hesitation doesn't dip into the dock
    wx, wy = _clamp_to_bounds(wx, wy)
    
    # Move to waypoint
    points1 = _bezier_curve(cx, cy, wx, wy, num_points=random.randint(10, 20))
    sleep_time1 = (duration * 0.7) / max(len(points1), 1)
    
    expected_x, expected_y = cx, cy
    for px, py in points1:
        cx, cy = _yield_if_human_override(expected_x, expected_y)
        if (cx, cy) != (expected_x, expected_y):
            # Recalculate remaining path if human grabbed it!
            points1 = _bezier_curve(cx, cy, wx, wy, num_points=random.randint(10, 20))
            # Just jump to next loop iteration
            
        pyautogui.moveTo(px, py, _pause=False)
        expected_x, expected_y = px, py
        time.sleep(sleep_time1)
        
    # Hesitate at waypoint
    time.sleep(random.uniform(0.1, 0.3))
    
    # Final micro-movement to target
    points2 = _bezier_curve(wx, wy, tx, ty, num_points=random.randint(5, 10))
    sleep_time2 = (duration * 0.3) / max(len(points2), 1)
    
    expected_x, expected_y = wx, wy
    for px, py in points2:
        cx, cy = _yield_if_human_override(expected_x, expected_y)
        if (cx, cy) != (expected_x, expected_y):
            points2 = _bezier_curve(cx, cy, tx, ty, num_points=random.randint(5, 10))
            
        pyautogui.moveTo(px, py, _pause=False)
        expected_x, expected_y = px, py
        time.sleep(sleep_time2)


def _is_within_chrome_bounds(x: int, y: int) -> bool:
    bounds = _chrome_bounds()
    if not bounds: return True # If we can't get bounds, assume it's fine (or if it's OS dialog)
    bx, by, bw, bh = bounds
    return bx <= x <= bx + bw and by <= y <= by + bh

def _human_click(x: int, y: int, ignore_bounds: bool = False) -> None:
    """
    Click at (x, y) with a smooth Bezier curve move.
    Applies drift calibration offset.
    """
    if not ignore_bounds and not _is_within_chrome_bounds(x, y):
        logger.error(f"ABORT CLICK: Coordinate ({x}, {y}) is outside Chrome window! Agent prevented from clicking random apps.")
        return

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


def _human_move(x: int, y: int, ignore_bounds: bool = False) -> None:
    """
    Move mouse to (x, y) with a smooth Bezier curve without clicking.
    """
    if not ignore_bounds and not _is_within_chrome_bounds(x, y):
        logger.error(f"ABORT MOVE: Coordinate ({x}, {y}) is outside Chrome window! Agent prevented from drifting.")
        return

    tx = x + CLICK_DRIFT_OFFSET_X
    ty = y + CLICK_DRIFT_OFFSET_Y
    
    time.sleep(random.uniform(0.2, 0.5))
    duration = random.uniform(0.5, 1.0)
    _execute_bezier_move(tx, ty, duration)
    time.sleep(random.uniform(0.1, 0.3))

def _find_and_click(
    step: Step,
    lib: VisionButtonLibrary,
    screenshot: np.ndarray,
    chrome_offset: tuple[int, int] = (0, 0),
    click_offset: tuple[int, int] = (0, 0),
) -> bool:
    """
    Try template match first, then OCR text fallback.
    Every proposed click is evaluated by the Swarm Council before execution.
    Returns True if something was clicked.
    """
    import cv2

    # 1. Template match
    if step.template:
        match = lib.find(step.template, screenshot)
        if match:
            rx = random.randint(-match.bbox.width // 4, match.bbox.width // 4) if match.bbox.width > 4 else 0
            ry = random.randint(-match.bbox.height // 4, match.bbox.height // 4) if match.bbox.height > 4 else 0
            cx = match.bbox.x + match.bbox.width // 2 + chrome_offset[0] + rx + click_offset[0]
            cy = match.bbox.y + match.bbox.height // 2 + chrome_offset[1] + ry + click_offset[1]

            # --- SWARM COUNCIL EVALUATION ---
            try:
                from bol.modules.m12_swarm import swarm_council
                decision = swarm_council.evaluate(
                    action_type="click", x=cx, y=cy, screenshot=screenshot,
                    context={"target_text": step.template, "all_bboxes": []}
                )
                if not decision.approved:
                    logger.warning("SWARM VETOED template '%s': %s", step.template, decision.reason)
                    # Fall through to OCR fallback instead of clicking a bad target
                else:
                    _human_click(cx, cy, ignore_bounds=(step.action == ActionType.OS_OPEN))
                    logger.info("Template match '%s' → clicked (%d, %d) conf=%.3f",
                                step.template, cx, cy, match.confidence)
                    return True
            except ImportError:
                # Swarm not available — click anyway (backwards compatible)
                _human_click(cx, cy, ignore_bounds=(step.action == ActionType.OS_OPEN))
                logger.info("Template match '%s' → clicked (%d, %d) conf=%.3f",
                            step.template, cx, cy, match.confidence)
                return True

    # 2. OCR text fallback
    if step.text_fallback:
        from bol.modules.m3_visual.ocr import OCREngine
        ocr = OCREngine()

        below = getattr(step, 'spatial_anchor_below', None)
        above = getattr(step, 'spatial_anchor_above', None)
        right_of = getattr(step, 'spatial_anchor_right_of', None)
        left_of = getattr(step, 'spatial_anchor_left_of', None)

        bboxes = ocr.find_text_on_screen(
            screenshot, target=step.text_fallback,
            below=below, above=above, right_of=right_of, left_of=left_of
        )

        # First-line defense: filter out Chrome URL/tab bar area
        bboxes = [b for b in bboxes if b.y > 90]

        if bboxes:
            for box in bboxes:
                rx = random.randint(-box.width // 4, box.width // 4) if box.width > 4 else 0
                ry = random.randint(-box.height // 4, box.height // 4) if box.height > 4 else 0

                x = box.x + box.width // 2 + chrome_offset[0] + rx + click_offset[0]
                y = box.y + box.height // 2 + chrome_offset[1] + ry + click_offset[1]

                # --- SWARM COUNCIL EVALUATION ---
                try:
                    from bol.modules.m12_swarm import swarm_council
                    decision = swarm_council.evaluate(
                        action_type="click", x=x, y=y, screenshot=screenshot,
                        context={
                            "target_text": step.text_fallback,
                            "all_bboxes": bboxes,
                            "has_spatial_anchor": bool(below or above or right_of or left_of)
                        }
                    )
                    if not decision.approved:
                        logger.warning("SWARM VETOED '%s' at (%d,%d): %s", step.text_fallback, x, y, decision.reason)
                        continue  # Try the next candidate box
                except ImportError:
                    pass  # Swarm not available — proceed anyway

                _human_click(x, y, ignore_bounds=(step.action == ActionType.OS_OPEN))
                logger.info("OCR match '%s' → clicked (%d, %d)", step.text_fallback, x, y)
                return True

    logger.warning("Could not find: template=%s, text=%s", step.template, step.text_fallback)
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

    def _save_paused_state(self, reason: str, screenshot: np.ndarray = None) -> None:
        import os
        import cv2
        import time
        pause_dir = Path("/Users/nandagiriaditya/GEMINI/ARTIFICIALHUMANAGENT/PAUSED_STATES")
        pause_dir.mkdir(exist_ok=True)
        if screenshot is None:
            screenshot = _capture_screen()
        filename = pause_dir / f"paused_{reason}_{int(time.time())}.png"
        cv2.imwrite(str(filename), screenshot)

    def _verify_stable_state(self, step: Step) -> float:
        """
        Check if Chrome is in focus and if there's no login screen.
        If an issue is found, enter an infinite polling loop (every 10s).
        Returns the total seconds slept, so the caller can adjust its timeout.
        """
        import pytesseract
        import cv2
        import subprocess
        
        time_slept = 0.0
        while True:
            is_unstable = False
            
            # 1. Check if Chrome is frontmost (unless it's an OS dialog step)
            if step.action != ActionType.OS_OPEN:
                try:
                    script = 'tell application "System Events" to get name of first application process whose frontmost is true'
                    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                    front_app = result.stdout.strip()
                    if front_app and "Google Chrome" not in front_app:
                        logger.warning("[PAUSED] '%s' is in focus, not Chrome. Waiting 10s...", front_app)
                        self._save_paused_state("out_of_focus")
                        is_unstable = True
                except Exception as e:
                    pass
            
            # 2. Check for login screens
            if not is_unstable:
                screenshot = _capture_screen()
                gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
                text_data = pytesseract.image_to_string(gray, config='--psm 11').lower()
                
                login_keywords = ["log in", "sign in to x", "sign in to linkedin", "password", "forgot password", "link with qr code"]
                if any(kw in text_data for kw in login_keywords):
                    logger.warning("[PAUSED] Login screen or logged out state detected. Waiting 10s...")
                    self._save_paused_state("login_screen", screenshot)
                    is_unstable = True

            if is_unstable:
                time.sleep(10)
                time_slept += 10.0
            else:
                break
                
        return time_slept

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
                
                # --- SMART RECOVERY (ROLLBACK) ---
                logger.info("Triggering Smart Recovery Rollback...")
                try:
                    pyautogui.hotkey('command', 'r')  # Refresh page
                    time.sleep(1.5)
                    pyautogui.press('return')  # Accept any "Leave site?" alerts
                    time.sleep(0.5)
                    pyautogui.press('esc')     # Dismiss any other popups
                except Exception as e:
                    logger.error(f"Rollback failed: {e}")

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

    def _dismiss_obstructive_modals(self, step: Step) -> bool:
        """Heuristic to dismiss common interrupting popups on social media."""
        from bol.modules.m3_visual.ocr import OCREngine
        ocr = OCREngine()
        screenshot, offset = self._get_cropped_screen_and_offset(step)
        
        # Added OK and No based on user feedback for Instagram Reel modals
        dismiss_words = ["OK", "Not Now", "Cancel", "Close", "No Thanks", "Leave", "Skip", "Decline", "Dismiss", "No"]
        for word in dismiss_words:
            bboxes = ocr.find_text_on_screen(screenshot, target=word)
            if bboxes:
                box = bboxes[0]
                x = box.x + box.width // 2 + offset[0]
                y = box.y + box.height // 2 + offset[1]
                logger.info(f"Found obstructive modal dismissal button '{word}'. Clicking it.")
                _human_click(x, y)
                time.sleep(1.0)
                return True
        return False

    def _wait_and_find_and_click(self, step: Step, max_wait: float = 15.0) -> bool:
        start_time = time.time()
        click_offset = (getattr(step, 'offset_x', 0), getattr(step, 'offset_y', 0))
        
        has_scrolled = False
        has_dismissed_modals = False
        
        while time.time() - start_time < max_wait:
            time_slept = self._verify_stable_state(step)
            if time_slept > 0:
                start_time += time_slept  # Extend timeout so it doesn't fail due to pause
                
            screenshot, offset = self._get_cropped_screen_and_offset(step)
            if _find_and_click(step, self._lib, screenshot, offset, click_offset):
                return True
                
            elapsed = time.time() - start_time
            
            # Modal Dismissal: If 75% through timeout, try dismissing popups
            if elapsed > (max_wait * 0.75) and not has_dismissed_modals and step.action != ActionType.OS_OPEN:
                logger.info("75% through timeout, attempting to dismiss any obstructive modals...")
                if self._dismiss_obstructive_modals(step):
                    # Reset timeout partially to allow element to be found after modal closes
                    start_time = time.time() - (max_wait / 4.0) 
                has_dismissed_modals = True
                continue

            time.sleep(0.5)
            
        logger.warning(f"Timeout ({max_wait}s) waiting for element: {step.description}")
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
            
            # Maximize the window to true macOS full screen mode using a physical keyboard shortcut.
            # This completely bypasses all AppleScript/System Events permission blocks.
            try:
                import pyautogui
                applescript = 'tell application "Google Chrome" to activate'
                subprocess.run(["osascript", "-e", applescript])
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'command', 'f')
                time.sleep(1.5) # Wait for the fullscreen animation to finish
            except Exception as e:
                logger.error("Failed to maximize Chrome automatically: %s", e)
            return True

        if step.action == ActionType.WAIT:
            self._verify_stable_state(step)
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
                time_slept = self._verify_stable_state(step)
                if time_slept > 0:
                    start_time += time_slept
                    
                screenshot, offset = self._get_cropped_screen_and_offset(step)
                matches = self._lib.find_all(step.hover_template, screenshot)
                
                if not matches:
                    # Fallback to direct OCR if template isn't found
                    # We create a dummy step just for this OCR check
                    hover_step = Step(number=0, description="hover", action=ActionType.CLICK, text_fallback=step.hover_verify_text)
                    if _find_and_click(hover_step, self._lib, screenshot, offset):
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
            
            # Verify state before typing to ensure focus hasn't been lost
            self._verify_stable_state(step)
            
            # Type character by character with a truly randomized gap between EVERY key
            for char in text:
                pyautogui.typewrite(char)
                time.sleep(random.uniform(0.04, 0.18))
                
            # Post-typing pause
            time.sleep(random.uniform(0.3, 0.7))
            return True

        if step.action == ActionType.PRESS_ENTER:
            logger.info("PRESS_ENTER Action: pressing return key natively.")
            self._verify_stable_state(step)
            time.sleep(random.uniform(0.5, 1.0))
            pyautogui.press('return')
            time.sleep(random.uniform(0.5, 1.0))
            return True

        if step.action == ActionType.OS_OPEN:
            self._verify_stable_state(step)
            # The OS file picker is open. If media_path given, type it in first.
            media_path = params.get(step.file_key or "media_path", "")
            if media_path:
                # Use Cmd+Shift+G to navigate to path in macOS file dialog
                time.sleep(2.0)  # wait for dialog animation
                pyautogui.hotkey('command', 'shift', 'g')
                time.sleep(1.0)
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
            time.sleep(2.0)
            # Handle file dialog
            media_path = params.get(step.file_key or "media_path", "")
            if media_path:
                pyautogui.hotkey('command', 'shift', 'g')
                time.sleep(1.0)
                pyautogui.typewrite(str(media_path), interval=0.03)
                time.sleep(0.5)
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
