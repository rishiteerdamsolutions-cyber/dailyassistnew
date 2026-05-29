from __future__ import annotations

import json
import time
import webbrowser
import cv2
import base64
from PIL import Image
import random
import pyautogui

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from bol.config import BOLConfig
from bol.modules.m3_visual.cortex import VisualCortex
from bol.modules.m5_linguistic.engine import LinguisticEngine
from bol.modules.m4_policy.personality import ALL_PERSONALITIES
from bol.modules.m6_bridge.bridge import AccessibilityBridge
from bol.schemas.kinematic import Point2D
from bol.schemas.bridge import ClickEvent, MouseButton
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class AutonomousCompanion:
    """
    Stateful ReAct loop orchestrator that uses Gemini to analyze screenshots
    and dictate the next physical action (click, type, open_url, ask, pause).
    """

    def __init__(self, config: BOLConfig) -> None:
        self.config = config
        self.cortex = VisualCortex(config)
        self.bridge = AccessibilityBridge()
        self.needs_vision = False
        self.ling_engine = LinguisticEngine(personality=ALL_PERSONALITIES[0])

        if not config.gemini_api_key or genai is None:
            raise ValueError("Gemini API key missing or google-generativeai not installed.")

        genai.configure(api_key=config.gemini_api_key)

        system_instruction = (
            "You are an autonomous web agent named BOL Companion. You are interacting with a user and looking at screenshots of their screen.\n"
            "The user will give you an intent, and you must decide the next step to achieve it.\n"
            "IMPORTANT: You MUST respond in pure JSON format (do not use markdown code blocks). Choose ONE of the following actions:\n"
            '1. {"action": "open_url", "url": "https://..."} - Opens a URL.\n'
            '2. {"action": "click", "target": "Exact Text on Screen"} - Clicks a button. To click the very bottom occurrence (usually CTA/Submit buttons), use negative indexing: "Post[-1]".\n'
            '3. {"action": "type", "text": "Something to type"} - Types the text biologically. ONLY use this when a text field is ALREADY active and focused.\n'
            '4. {"action": "ask", "message": "Question for user"} - Ask the user a question if you need clarification (e.g. which flight to choose).\n'
            '5. {"action": "pause", "message": "Reason"} - Pause execution so the user can complete a manual task (like OTP or Payment).\n'
            '6. {"action": "done", "message": "Completion message"} - Indicate the task is complete.\n'
            '7. {"action": "request_vision", "message": "Reason"} - Request to see the full screenshot if text is ambiguous (e.g. to find a specific colored button).\n'
            '8. {"action": "hotkey", "keys": ["command", "space"]} - Executes a system keyboard shortcut (e.g., ["enter"], ["command", "c"]).\n\n'
            "CRITICAL RULES:\n"
            "1. When the user first gives you a task, you MUST use the 'ask' action to outline your plan and ask for confirmation. Do NOT use open_url, click, or type until the user explicitly confirms.\n"
            "2. Always reply with exactly ONE JSON object. Example: {\"action\": \"click\", \"target\": \"Search Flights\"}\n"
            "3. If you need to click a submit/post/next CTA button, ALWAYS use 'request_vision' first. Before clicking, explicitly ask yourself: 'Is this an intermediary step (like Next) or a final step (like Post)?' Look at the visual screenshot to confirm the exact text of the button (e.g. Next or Post) before proceeding.\n"
            "4. If you know what button to click but it fails because the OCR engine cannot read it (e.g. due to white text on a blue background), do NOT guess random other words. Instead, use the pause action to gracefully hand off to the user: {\"action\": \"pause\", \"message\": \"I have prepared the post, but my text engine cannot clearly read the final button. Please click Post manually to finish!\"}\n"
            "5. When using the 'click' action on long text (like a full product title), DO NOT output the entire 20-word string. The text engine will fail to match it exactly. Instead, pick a SHORT, UNIQUE substring (1-3 words) like {\"action\": \"click\", \"target\": \"Micromax All-New J3\"}.\n"
            "6. AVOID TEXT vs BUTTON AMBIGUITY: The local click engine cannot tell the difference between plain text and buttons. If you want to click a button named 'Avakaya', but the word 'Avakaya' also appears in a header, the Python engine will intercept the click and reply with 'DISAMBIGUATION REQUIRED' and an image with numbered boxes. You MUST look at the numbered red boxes and reply with the correct index to click the button (e.g. {\"action\": \"click\", \"target\": \"Avakaya[2]\"}).\n"
            "7. NEVER try to click the system UI logs (e.g. 'I'm done with manual steps, Resume Agent!'). When you see a resume message, it means you should look at the actual webpage and continue your task.\n"
            "8. MAC OS NAVIGATION: To open a local application (like System Settings or Chrome), DO NOT try to click its name if it isn't clearly visible. Instead, output the hotkey action `[\"command\", \"space\"]` to open Spotlight Search. Wait for the next step, then use `type` to type the app name (e.g. \"System Settings\"). Wait for the next step, then use `hotkey` `[\"enter\"]` to launch it."
        )

        try:
            self.model = genai.GenerativeModel(
                model_name=config.gemini_model_name,
                system_instruction=system_instruction
            )
        except Exception:
            # Fallback for older SDKs that don't support system_instruction natively
            self.model = genai.GenerativeModel(model_name=config.gemini_model_name)

        self.chat = self.model.start_chat(history=[])
        self.is_paused = False
        self.latest_bgr = None

    def _capture_and_encode(self):
        _, img_bgr = self.cortex.capture_current_state()
        self.latest_bgr = img_bgr
        rgb_image = img_bgr[..., ::-1]
        return Image.fromarray(rgb_image)

    def _draw_and_encode_base64(self, bboxes=None, draw_numbers=False):
        if self.latest_bgr is None:
            return None
            
        img_copy = self.latest_bgr.copy()
        if bboxes:
            for idx, box in enumerate(bboxes):
                top_left = (box.x, box.y)
                bottom_right = (box.x + box.width, box.y + box.height)
                cv2.rectangle(img_copy, top_left, bottom_right, (0, 0, 255), 4)
                
                if draw_numbers:
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    text = f"[{idx}]"
                    text_size = cv2.getTextSize(text, font, 1.5, 3)[0]
                    # Try to place text to the left, else to the right
                    text_x = box.x - text_size[0] - 10 if box.x > text_size[0] + 10 else box.x + box.width + 10
                    text_y = box.y + (box.height + text_size[1]) // 2
                    
                    cv2.rectangle(img_copy, (text_x - 5, text_y - text_size[1] - 5), (text_x + text_size[0] + 5, text_y + 5), (0, 0, 0), -1)
                    cv2.putText(img_copy, text, (text_x, text_y), font, 1.5, (0, 255, 0), 3)

        _, buffer = cv2.imencode('.jpg', img_copy)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{img_base64}"

    def step(self, user_message: str = None) -> dict:
        """
        Runs one step of the ReAct loop.
        Returns a dict describing what happened, to be sent to the UI.
        """
        self.is_paused = False
        messages_out = []
        
        # 1. Take screenshot
        pil_image = self._capture_and_encode()

        # 2. Extract OCR Text locally
        ocr_result = self.cortex._ocr.extract_text(self.latest_bgr)
        screen_text = ocr_result.full_text if ocr_result.full_text else "No text found on screen."

        # 3. Build Prompt
        prompt = f"Here are all the text elements currently visible on the screen: {screen_text}\n"
        if user_message:
            prompt += f"The user says: {user_message}"
        else:
            prompt += "What is the next logical step?"

        logger.info(f"Sending text-only prompt to Gemini: {prompt}")
        
        try:
            while True:
                # Send message to stateful chat with retry for rate limits
                max_retries = 3
                response = None
                for attempt in range(max_retries):
                    try:
                        if self.needs_vision:
                            response = self.chat.send_message([prompt, pil_image])
                        else:
                            response = self.chat.send_message(prompt)
                        break
                    except Exception as e:
                        if "429" in str(e) and attempt < max_retries - 1:
                            import re
                            delay = 15.0 # Default fallback
                            match = re.search(r'retry in (\d+(?:\.\d+)?)s', str(e))
                            if match:
                                delay = float(match.group(1)) + 1.0
                            logger.warning(f"Rate limited (429). Retrying in {delay}s...")
                            time.sleep(delay)
                        else:
                            raise e
                
                raw_text = response.text.strip()
                
                # Clean JSON if model wrapped it in markdown
                if raw_text.startswith("```json"):
                    raw_text = raw_text.split("```json")[1]
                if raw_text.endswith("```"):
                    raw_text = raw_text.rsplit("```", 1)[0]
                raw_text = raw_text.strip()

                try:
                    action_data = json.loads(raw_text)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON from model: {raw_text}")
                    messages_out.append(f"Agent generated invalid action format: {raw_text}")
                    return {"status": "error", "messages": messages_out, "image_data": self._draw_and_encode_base64()}

                action = action_data.get("action")
                
                if action == "request_vision":
                    self.needs_vision = True
                    msg = action_data.get("message", "Requesting visual context to disambiguate the screen.")
                    logger.info(f"AI requested vision: {msg}. Retrying immediately...")
                    continue
                
                self.needs_vision = False
                break
            
            if action == "open_url":
                url = action_data.get("url", "")
                messages_out.append(f"Opening URL in Chrome: {url}")
                import sys
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
                    # Fallback to system default if Chrome is missing
                    webbrowser.open(url)
                
                time.sleep(3) # Wait for page load
                return {"status": "success", "messages": messages_out, "image_data": self._draw_and_encode_base64()}

            elif action == "click":
                import re
                from bol.modules.m2_kinematic.bezier import BezierEngine
                
                raw_target = action_data.get("target", "")
                search_word = raw_target.strip()
                target_idx = 0
                has_explicit_index = False
                match = re.search(r'[\[\(](-?\d+)[\]\)]$', search_word)
                if match:
                    val = int(match.group(1))
                    if val > 0:
                        target_idx = val - 1
                    else:
                        target_idx = val
                    search_word = search_word[:match.start()].strip()
                    has_explicit_index = True
                    
                messages_out.append(f"Agent attempting to click: '{search_word}' (Index {target_idx})")
                
                # Use local OCR to find the text
                bboxes = self.cortex._ocr.find_text_on_screen(self.latest_bgr, search_word)
                
                if not bboxes:
                    msg = f"My text engine couldn't physically locate '{search_word}'. Please click it manually and press Resume!"
                    messages_out.append(msg)
                    self.is_paused = True
                    return {"status": "success", "messages": messages_out, "is_paused": True, "image_data": self._draw_and_encode_base64()}
                
                # Sort bounding boxes top-to-bottom, left-to-right (bucket y into lines of 15px)
                bboxes = sorted(bboxes, key=lambda b: (b.y // 15, b.x))
                
                if len(bboxes) > 1 and not has_explicit_index:
                    msg = f"DISAMBIGUATION REQUIRED: I found {len(bboxes)} instances of '{search_word}'. Look at the numbered boxes in the image. Reply immediately with the correct index to click the button/link, e.g. {{\"action\": \"click\", \"target\": \"{search_word}[1]\"}}."
                    messages_out.append(msg)
                    # Return success to keep the loop going, but provide the numbered image
                    return {"status": "success", "messages": messages_out, "image_data": self._draw_and_encode_base64(bboxes=bboxes, draw_numbers=True)}
                
                try:
                    box = bboxes[target_idx]
                except IndexError:
                    msg = f"I found '{search_word}', but requested index {target_idx} is out of bounds. Please click it manually and press Resume!"
                    messages_out.append(msg)
                    self.is_paused = True
                    return {"status": "success", "messages": messages_out, "is_paused": True, "image_data": self._draw_and_encode_base64()}
                click_target = self.cortex._targeting.compute_click_target(box)
                final_point = Point2D(x=click_target.click_x, y=click_target.click_y)
                
                # Physically move the mouse using Bezier Engine
                current_pos = self.bridge.get_cursor_position()
                dist = current_pos.distance_to(final_point)
                if dist > 2.0:
                    cp = BezierEngine.generate_control_points(current_pos, final_point)
                    traj = BezierEngine.sample_trajectory(cp, num_steps=30)
                    dur = BezierEngine.calculate_duration_ms(dist)
                    self.bridge.execute_movement(traj, dur)
                    time.sleep(random.uniform(0.1, 0.3)) # Human hesitation
                
                # Execute physical click
                click_event = ClickEvent(
                    target_x=int(final_point.x),
                    target_y=int(final_point.y),
                    button=MouseButton.LEFT,
                    pre_click_delay_ms=random.uniform(100, 250)
                )
                self.bridge.execute_click(click_event)
                messages_out.append(f"Successfully clicked '{search_word}'.")
                
                return {"status": "success", "messages": messages_out, "image_data": self._draw_and_encode_base64(bboxes=[box])}

            elif action == "type":
                text = action_data.get("text", "")
                messages_out.append(f"Agent typing: '{text}'")
                
                payload = self.ling_engine.prepare_payload(text)
                seq = self.ling_engine.generate_keystroke_sequence(payload)
                self.bridge.execute_keystroke_sequence(seq.events)
                
                return {"status": "success", "messages": messages_out, "image_data": self._draw_and_encode_base64()}
            elif action == "hotkey":
                keys = action_data.get("keys", [])
                if keys:
                    messages_out.append(f"Agent pressing hotkey: {keys}")
                    pyautogui.hotkey(*keys)
                return {"status": "success", "messages": messages_out, "image_data": self._draw_and_encode_base64()}

            elif action == "ask":
                msg = action_data.get("message", "I have a question.")
                messages_out.append(msg)
                return {"status": "success", "messages": messages_out, "is_asking": True, "image_data": self._draw_and_encode_base64()}

            elif action == "pause":
                msg = action_data.get("message", "Pausing for manual interaction.")
                messages_out.append(msg)
                self.is_paused = True
                return {"status": "success", "messages": messages_out, "is_paused": True, "image_data": self._draw_and_encode_base64()}

            elif action == "done":
                msg = action_data.get("message", "Task complete.")
                messages_out.append(msg)
                return {"status": "success", "messages": messages_out, "is_done": True, "image_data": self._draw_and_encode_base64()}

            else:
                messages_out.append(f"Unknown action: {action}")
                return {"status": "error", "messages": messages_out, "image_data": self._draw_and_encode_base64()}

        except Exception as e:
            logger.error(f"Error in agent step: {str(e)}")
            messages_out.append(f"System error: {str(e)}")
            return {"status": "error", "messages": messages_out, "image_data": self._draw_and_encode_base64()}
