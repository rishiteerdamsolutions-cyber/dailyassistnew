import time
import re
import sys
import webbrowser
import pyautogui
import random

from bol.config import BOLConfig
from bol.modules.m3_visual.cortex import VisualCortex
from bol.modules.m5_linguistic.engine import LinguisticEngine
from bol.modules.m4_policy.personality import ALL_PERSONALITIES
from bol.modules.m6_bridge.bridge import AccessibilityBridge
from bol.schemas.kinematic import Point2D
from bol.schemas.bridge import ClickEvent, MouseButton
from bol.utils.logging import get_logger
from bol.modules.m8_orchestrator.ota_fetcher import fetch_latest_workflows
from bol.modules.m2_kinematic.bezier import BezierEngine

logger = get_logger(__name__)

class WorkflowRunner:
    """
    Executes a predefined JSON DSL workflow linearly without requiring LLM inference.
    Used for highly deterministic social media assistance flows.
    """
    def __init__(self, config: BOLConfig):
        self.config = config
        self.cortex = VisualCortex(config)
        self.bridge = AccessibilityBridge()
        self.ling_engine = LinguisticEngine(personality=ALL_PERSONALITIES[0])

    def run_workflow(self, workflow_id: str, context: dict):
        """
        Executes a workflow.
        context should contain variables like {"$FILE_PATH": "/path/to/media.mp4", "$CAPTION": "Hello World"}
        """
        all_workflows = fetch_latest_workflows()
        
        if "workflows" not in all_workflows or workflow_id not in all_workflows["workflows"]:
            logger.error(f"Workflow '{workflow_id}' not found in remote or local configuration.")
            return False

        steps = all_workflows["workflows"][workflow_id]
        logger.info(f"Starting deterministic workflow: {workflow_id} ({len(steps)} steps)")
        
        for idx, step in enumerate(steps):
            action = step.get("action")
            raw_target = step.get("target", "")
            
            # Substitute context variables
            for key, val in context.items():
                if key in raw_target:
                    raw_target = raw_target.replace(key, str(val))
            
            logger.info(f"Executing Step {idx+1}: {action} -> {raw_target}")
            
            if action == "navigate":
                self._execute_navigate(raw_target)
            elif action == "click":
                self._execute_click(raw_target)
            elif action == "click_offset":
                off_x = step.get("offset_x", 0)
                off_y = step.get("offset_y", 0)
                self._execute_click(raw_target, offset_x=off_x, offset_y=off_y)
            elif action == "type":
                self._execute_type(raw_target)
            elif action == "upload_native":
                self._execute_upload_native(raw_target)
            else:
                logger.warning(f"Unknown action: {action}")
            
            # Wait between steps to let UI update
            time.sleep(random.uniform(2.0, 4.0))
            
        logger.info(f"Workflow {workflow_id} complete.")
        return True

    def _execute_navigate(self, url: str):
        if hasattr(self.config, "browser_window_enabled") and self.config.browser_window_enabled:
            from bol.modules.m6_bridge.browser import get_browser_manager
            manager = get_browser_manager(self.config)
            manager.launch(url)
            return

        try:
            if sys.platform == 'darwin':
                chrome_path = 'open -a "Google Chrome" %s'
                webbrowser.get(chrome_path).open(url)
            elif sys.platform == 'win32':
                chrome_path = 'C:/Program Files/Google/Chrome/Application/chrome.exe %s'
                webbrowser.get(chrome_path).open(url)
            else:
                webbrowser.open(url)
        except Exception:
            webbrowser.open(url)
        time.sleep(5) # Let the page load

    def _execute_click(self, target: str, offset_x: int = 0, offset_y: int = 0):
        # Capture current screen
        _, img_bgr = self.cortex.capture_current_state()
        
        # 1. Handle Template Matches (ICON-*)
        if target.startswith("ICON-"):
            # Mocking template match for now, normally calls cv2.matchTemplate
            logger.info(f"Template matching for {target} not fully implemented, falling back to screen center.")
            center_x, center_y = 500, 500 # Fallback
            self._move_and_click(center_x + offset_x, center_y + offset_y)
            return

        # 2. Handle Text Matches (T-, B-, Bup-, etc)
        search_word = target.strip()
        target_idx = 0
        has_explicit_index = False
        match = re.search(r'[\[\(](-?\d+)[\]\)]$', search_word)
        if match:
            val = int(match.group(1))
            target_idx = val - 1 if val > 0 else val
            search_word = search_word[:match.start()].strip()
            has_explicit_index = True

        bboxes = self.cortex._ocr.find_text_on_screen(img_bgr, search_word)
        if not bboxes:
            logger.error(f"Could not find '{search_word}' on screen.")
            return
            
        # Sort top-to-bottom
        bboxes = sorted(bboxes, key=lambda b: (b.y // 15, b.x))
        
        try:
            box = bboxes[target_idx]
            click_target = self.cortex._targeting.compute_click_target(box)
            final_x = click_target.click_x + offset_x
            final_y = click_target.click_y + offset_y
            if hasattr(self.config, "browser_window_enabled") and self.config.browser_window_enabled:
                final_x += self.config.browser_window_x
                final_y += self.config.browser_window_y
            self._move_and_click(final_x, final_y)
        except IndexError:
            logger.error(f"Index {target_idx} out of bounds for '{search_word}'")

    def _move_and_click(self, x: float, y: float):
        final_point = Point2D(x=x, y=y)
        current_pos = self.bridge.get_cursor_position()
        dist = current_pos.distance_to(final_point)
        if dist > 2.0:
            cp = BezierEngine.generate_control_points(current_pos, final_point)
            traj = BezierEngine.sample_trajectory(cp, num_steps=30)
            dur = BezierEngine.calculate_duration_ms(dist)
            self.bridge.execute_movement(traj, dur)
            time.sleep(random.uniform(0.1, 0.3))
            
        click_event = ClickEvent(
            target_x=int(final_point.x),
            target_y=int(final_point.y),
            button=MouseButton.LEFT,
            pre_click_delay_ms=random.uniform(100, 250)
        )
        self.bridge.execute_click(click_event)

    def _execute_type(self, text: str):
        payload = self.ling_engine.prepare_payload(text)
        seq = self.ling_engine.generate_keystroke_sequence(payload)
        self.bridge.execute_keystroke_sequence(seq.events)

    def _execute_upload_native(self, file_path: str):
        """
        Handles the OS native file upload dialog.
        Types the absolute path and presses enter.
        """
        time.sleep(2) # wait for native dialog to appear
        # On Mac, you usually hit Cmd+Shift+G to enter absolute path, then type path, then enter
        if sys.platform == 'darwin':
            pyautogui.hotkey('command', 'shift', 'g')
            time.sleep(1)
            pyautogui.write(file_path, interval=0.05)
            time.sleep(1)
            pyautogui.press('enter')
            time.sleep(1)
            pyautogui.press('enter')
        else:
            # Windows native dialog types directly into filename box
            pyautogui.write(file_path, interval=0.05)
            time.sleep(1)
            pyautogui.press('enter')
