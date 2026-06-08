from __future__ import annotations

import json
import time
import webbrowser
import cv2
import base64
from PIL import Image
import random
import pyautogui
import numpy as np

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
        self.needs_vision = True
        self.ling_engine = LinguisticEngine(personality=ALL_PERSONALITIES[0])

        # Tier-2 LLM keys: resolved at runtime via aha.byok (BYOK file + .env fallback).
        system_instruction = (
            "You are a human-assisted web agent named AHA Companion. You are interacting with a user and looking at screenshots of their screen.\n"
            "PHILOSOPHY & COMPLIANCE: When a user asks to post on a platform, a hardcoded Python flow handles it. If the user asks for general web automation tasks (e.g., shopping on Amazon) and BYOK is enabled, you CAN browse the web autonomously.\n"
            "IMPORTANT: You MUST respond in pure JSON format (do not use markdown code blocks). Every response MUST include 'current_plan_step', 'next_plan_step' (integers), and an 'intent' string explaining your reasoning. Choose ONE of the following actions:\n"
            '1. {"action": "ask", "message": "Question or response to user", "plan": [...], "current_plan_step": X, "next_plan_step": Y, "intent": "..."} - Chat with the user or answer questions.\n'
            '2. {"action": "open_url", "url": "https://...", "current_plan_step": X, "next_plan_step": Y, "intent": "..."} - Open a URL in the browser to start an autonomous web task.\n'
            '3. {"action": "click", "target": "search_word", "current_plan_step": X, "next_plan_step": Y, "intent": "..."} - Click an element on the screen.\n'
            '4. {"action": "type", "text": "text to type", "current_plan_step": X, "next_plan_step": Y, "intent": "..."} - Type text into the currently focused field.\n'
            '5. {"action": "pause", "message": "Reason", "current_plan_step": X, "next_plan_step": Y, "intent": "..."} - Pause for manual steps.\n'
            '6. {"action": "done", "message": "Message", "current_plan_step": X, "next_plan_step": Y, "intent": "..."} - Complete a chat conversation or task.\n\n'
            "CRITICAL RULES:\n"
            "1. Always reply with exactly ONE JSON object.\n"
            "2. If the user asks for guidance on how to do something manually on the screen, use your vision capabilities to look at the screenshot and use the 'ask' action to tell them where to click or what to do.\n"
            "3. If the user asks about ANY social media platform (Facebook, Instagram, X, etc.), you MUST include this exact string anywhere in your chat response: '[COLLAPSE:Platform Terms:Just so you know, we don't encourage going against the rules of the platform on which this limited computer use tool is being used, so always be mindful of their terms of service!]' Do not use words like 'Agent', 'User', or 'System'. Make it sound completely natural and conversational.\n"
        )

        self.system_instruction = system_instruction
        self.chat_history = []
        self.current_plan = None
        self.current_plan_step = 0
        self.is_paused = False
        self.latest_bgr = None

    def _capture_and_encode(self):
        import time
        max_attempts = 5
        threshold = 0.02
        
        _, prev_bgr = self.cortex.capture_current_state()
        
        for _ in range(max_attempts):
            time.sleep(0.3)
            _, curr_bgr = self.cortex.capture_current_state()
            
            # Check diff to see if screen has settled
            diff = np.abs(prev_bgr.astype(int) - curr_bgr.astype(int))
            change_ratio = np.sum(diff > 10) / diff.size
            
            if change_ratio < threshold:
                prev_bgr = curr_bgr
                break
                
            prev_bgr = curr_bgr
            logger.debug(f"Screen not settled yet (diff: {change_ratio:.3f}), waiting...")
            
        self.latest_bgr = prev_bgr
        rgb_image = prev_bgr[..., ::-1]
        return Image.fromarray(rgb_image)

    def _draw_and_encode_base64(self, bboxes=None, draw_numbers=False):
        if self.latest_bgr is None:
            return None
            
        img_copy = self.latest_bgr.copy()
        if bboxes:
            use_compact = len(bboxes) > 5
            box_thickness = 2 if use_compact else 4
            font_scale = 0.55 if use_compact else 1.2
            font_thickness = 1 if use_compact else 2
            
            for idx, item in enumerate(bboxes):
                # Support both BoundingBox and OCRWord elements
                if hasattr(item, "bounding_box"):
                    box = item.bounding_box
                else:
                    box = item
                    
                top_left = (box.x, box.y)
                bottom_right = (box.x + box.width, box.y + box.height)
                cv2.rectangle(img_copy, top_left, bottom_right, (0, 0, 255), box_thickness)
                
                if draw_numbers:
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    text = f"[{idx}]"
                    text_size = cv2.getTextSize(text, font, font_scale, font_thickness)[0]
                    
                    if use_compact:
                        # Place label slightly offset above/inside the top-left corner
                        text_x = box.x
                        text_y = box.y - 3 if box.y > 15 else box.y + box.height + 15
                    else:
                        text_x = box.x - text_size[0] - 10 if box.x > text_size[0] + 10 else box.x + box.width + 10
                        text_y = box.y + (box.height + text_size[1]) // 2
                    
                    # Bound checks
                    h, w = img_copy.shape[:2]
                    text_x = max(0, min(text_x, w - text_size[0]))
                    text_y = max(text_size[1], min(text_y, h - 5))
                    
                    cv2.rectangle(img_copy, (text_x - 3, text_y - text_size[1] - 3), (text_x + text_size[0] + 3, text_y + 3), (0, 0, 0), -1)
                    cv2.putText(img_copy, text, (text_x, text_y), font, font_scale, (0, 255, 0), font_thickness, cv2.LINE_AA)

        _, buffer = cv2.imencode('.jpg', img_copy)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{img_base64}"

    def _get_openai_messages(self, prompt: str, current_image_base64: str | None = None) -> list[dict]:
        """
        Converts internal `self.chat_history` (mixed list of Content objects or dicts)
        to OpenAI messages schema.
        We strip out base64/media inline_data from history to optimize token cost,
        and only keep the current image base64 if vision is active for this step.
        """
        messages = []
        
        # Prepend the system instruction as a system message
        messages.append({
            "role": "system",
            "content": self.system_instruction
        })
        
        for msg in self.chat_history:
            # Detect role
            if hasattr(msg, "role"):
                role = msg.role
            elif isinstance(msg, dict) and "role" in msg:
                role = msg["role"]
            else:
                continue
            
            # Map model -> assistant, anything else to user
            openai_role = "assistant" if role == "model" else "user"
            
            # Extract text parts
            text_parts = []
            if hasattr(msg, "parts"):
                parts = msg.parts
            elif isinstance(msg, dict) and "parts" in msg:
                parts = msg["parts"]
            else:
                parts = []
                
            for part in parts:
                if isinstance(part, dict):
                    if "text" in part:
                        text_parts.append(part["text"])
                elif isinstance(part, str):
                    text_parts.append(part)
                elif hasattr(part, "text") and part.text:
                    text_parts.append(part.text)
                # Ignore inline_data / image parts in history
                
            if text_parts:
                messages.append({
                    "role": openai_role,
                    "content": "\n".join(text_parts)
                })
                
        # Now append the current turn's content
        current_content = []
        current_content.append({"type": "text", "text": prompt})
        
        if self.needs_vision and current_image_base64:
            current_content.append({
                "type": "image_url",
                "image_url": {
                    "url": current_image_base64
                }
            })
            
        messages.append({
            "role": "user",
            "content": current_content
        })
        
        return messages

    def step(self, user_message: str | None = None, is_native_app: bool = False):
        """
        Executes one step of the agent loop.
        Returns a dict describing what happened, to be sent to the UI.
        """
        self.is_paused = False
        messages_out = []

        # ── TIER-1 LOCAL: OS / DEV / FILES — LLM BLOCKED ─────────────────────
        # Local tasks (git, .env.local, Bluetooth, projects) run via m9_local +
        # m9_native only. On failure, return error — LLM does NOT take over.
        if user_message:
            from bol.modules.m9_local.parser import detect_local_task
            from bol.modules.m9_local.executor import run_local_task

            local_task = detect_local_task(user_message)
            if local_task:
                messages_out.append(
                    f"🖥️ [LOCAL] {local_task.description} — deterministic (no LLM)"
                )

                def _local_progress(step_num, desc, status):
                    logger.info("[Local %s] Step %d: %s [%s]",
                                local_task.flow_id, step_num, desc, status)

                result = run_local_task(local_task, _local_progress)
                ok = bool(result.get("success"))
                if ok:
                    messages_out.append(f"✅ {result.get('message', 'Done.')}")
                else:
                    messages_out.append(
                        f"❌ {result.get('error') or result.get('message', 'Local task failed')}"
                    )

                self._capture_and_encode()
                return {
                    "status": "success" if ok else "error",
                    "messages": messages_out,
                    "is_done": ok,
                    "image_data": self._draw_and_encode_base64(),
                }

        # ── SOCIAL MEDIA: FLOW EXECUTOR ONLY — LLM BLOCKED ──────────────────
        # Social media tasks are EXCLUSIVELY handled by the deterministic flow
        # executor in m9_social. The LLM is NEVER used for these tasks.
        # If the flow fails, an error is returned — the LLM does NOT take over.
        if user_message:
            import re as _re
            from bol.modules.m9_social.flows import detect_flow
            from bol.modules.m9_social.executor import run_social_task

            flow = detect_flow(user_message)
            if flow:
                # ── Extract params from user message ──────────────────────────
                params = {}

                # Media file path
                path_match = _re.search(
                    r'(/[^\s]+\.(jpg|jpeg|png|mp4|mov|gif|webp))',
                    user_message, _re.IGNORECASE
                )
                if path_match:
                    params["media_path"] = path_match.group(1)
                else:
                    file_match = _re.search(
                        r'\b(image|photo|pic|video|media|file)\s+(?:named|called|with\s+name|nmed)?\s*[\'"]?([a-zA-Z0-9_\-\.]+)[\'"]?\b',
                        user_message, _re.IGNORECASE
                    )
                    if file_match:
                        filename_query = file_match.group(2).lower()
                        stop_words = {"and", "with", "some", "the", "a", "an", "text", "txt", "on", "in", "to", "for", "fb", "from", "vault"}
                        if filename_query not in stop_words:
                            import os
                            from pathlib import Path
                            search_dirs = [Path.home() / "Downloads", Path.home() / "Desktop", Path.home() / "Documents"]
                            found_path = None
                            for d in search_dirs:
                                if not d.exists():
                                    continue
                                for root, _, files in os.walk(d):
                                    for f in files:
                                        if filename_query in f.lower() and f.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.gif', '.webp')):
                                            found_path = os.path.join(root, f)
                                            break
                                    if found_path:
                                        break
                                if found_path:
                                    break
                            if found_path:
                                params["media_path"] = found_path

                # Caption — quoted text first (double or single quotes)
                caption_match = _re.search(
                    r'["\'\u201c\u201d\u2018\u2019]([^""\'\'\u201c\u201d\u2018\u2019]+)["\'\u201c\u201d\u2018\u2019]',
                    user_message
                )
                if caption_match:
                    params["caption"] = caption_match.group(1)
                else:
                    stripped = _re.sub(
                        r'\b(post|share|upload|write|send|tweet|on|to|in|the|a|an|and|with|only|'
                        r'facebook|fb|fcbk|facebok|facebk|fcebk|acebok|facebkok|fcbook|fbook|faceboook|fbc|'
                        r'instagram|insta|instgrm|instgram|ig|instrm|instagam|instagrm|intagram|inst|'
                        r'linkedin|linkdin|linkdn|li|linkd\sin|linked\sin|lnkdin|lkin|linkden|linkin|'
                        r'whatsapp|watsap|whsatapp|whasap|wahtsapp|whtsapp|wapp|wahtsap|wtsap|whstapp|whtsp|wa|whatsap|watsapp|wtsp|watsp|whtap|'
                        r'twitter|x\.com|x|twiter|twtter|twitr|twt|twtr|'
                        r'status|story|reel|message|dm|photo|video|pic|image|media|file)\b',
                        '', user_message, flags=_re.IGNORECASE
                    ).strip()
                    if 'filename_query' in locals() and filename_query and filename_query not in stop_words:
                        stripped = stripped.replace(filename_query, "", 1).replace(filename_query.lower(), "", 1).strip()

                    stripped = _re.sub(r'\s+', ' ', stripped).strip(' /.,!?')
                    if stripped and stripped.lower() not in ["and txt", "txt", "text", "and text", "some text"]:
                        params["caption"] = stripped

                if "caption" in params:
                    params["tweet_text"] = params["caption"]
                    params["message"] = params["caption"]

                # ── Vault Fallback (Content Calendar) ─────────────────────────
                from datetime import date
                from aha.storage_vault import vault_root

                today = date.today()
                today_day = today.day
                today_year = today.year
                today_month = today.month

                slot_base = vault_root() / "Slots"

                if slot_base.exists() and "media_path" not in params:
                    matched_slot_dir = None
                    for slot_dir in slot_base.iterdir():
                        if slot_dir.is_dir() and slot_dir.name.lower() == flow.platform.lower():
                            matched_slot_dir = slot_dir
                            break

                    if matched_slot_dir:
                        target_dir = matched_slot_dir / str(today_year) / str(today_month)

                        img_dir = target_dir / "Images"
                        vid_dir = target_dir / "Videos"

                        found_img = None
                        if img_dir.exists():
                            for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                                p = img_dir / f"{today_day}{ext}"
                                if p.exists() and p.stat().st_size > 0:
                                    found_img = p
                                    break
                            if not found_img:
                                for p in img_dir.iterdir():
                                    if p.is_file() and p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                                        if p.stat().st_size > 0:
                                            found_img = p
                                            break

                        found_vid = None
                        if vid_dir.exists():
                            for ext in [".mp4", ".mov", ".webm"]:
                                p = vid_dir / f"{today_day}{ext}"
                                if p.exists() and p.stat().st_size > 0:
                                    found_vid = p
                                    break
                            if not found_vid:
                                for p in vid_dir.iterdir():
                                    if p.is_file() and p.suffix.lower() in [".mp4", ".mov", ".webm"]:
                                        if p.stat().st_size > 0:
                                            found_vid = p
                                            break

                        msg_lower = user_message.lower()
                        wants_video = any(w in msg_lower for w in ["video", "reel", "story", "clip", "mp4"])
                        wants_image = any(w in msg_lower for w in ["image", "photo", "pic", "picture", "png", "jpg"])
                        wants_text_only = any(w in msg_lower for w in ["text only", "only text", "without image", "without video", "no image", "no video", "no media", "without media", "just text"])
                        wants_no_text = any(w in msg_lower for w in ["no text", "without text", "only image", "image only", "only video", "video only", "just video", "just image", "zero text"])

                        if "caption" in params and not wants_image and not wants_video:
                            wants_text_only = True

                        if "text" in msg_lower and not wants_image and not wants_video:
                            wants_text_only = True

                        if not wants_text_only:
                            if wants_video and not wants_image:
                                if found_vid:
                                    params["media_path"] = str(found_vid.resolve())
                            elif wants_image and not wants_video:
                                if found_img:
                                    params["media_path"] = str(found_img.resolve())
                            else:
                                if found_img and found_vid:
                                    params["media_path"] = str(found_img.resolve())
                                elif found_img:
                                    params["media_path"] = str(found_img.resolve())
                                elif found_vid:
                                    params["media_path"] = str(found_vid.resolve())

                        if wants_no_text and "caption" not in params:
                            params["caption"] = ""

                        if "caption" not in params:
                            txt_path = target_dir / "Texts" / f"{today_day}.txt"
                            if txt_path.exists() and txt_path.stat().st_size > 0:
                                try:
                                    params["caption"] = txt_path.read_text(encoding="utf-8").strip()
                                    params["tweet_text"] = params["caption"]
                                    params["message"] = params["caption"]
                                except Exception:
                                    pass

                if flow.task_id == "facebook_text_post" and params.get("media_path"):
                    from bol.modules.m9_social.flows import FLOW_REGISTRY
                    if "facebook_post" in FLOW_REGISTRY:
                        flow = FLOW_REGISTRY["facebook_post"]
                        logger.info("Upgraded flow to facebook_post because media was found.")

                if flow.platform == "instagram" and not params.get("media_path"):
                    msg = (
                        "❌ I cannot post to Instagram because no image or video was found! "
                        "Instagram requires media. Please attach a file or schedule one in the Vault."
                    )
                    logger.error(msg)
                    self._capture_and_encode()
                    return {
                        "status": "error",
                        "messages": [msg],
                        "is_done": True,
                        "image_data": self._draw_and_encode_base64(),
                    }

                # ── Run the flow — no LLM involvement ────────────────────────
                disclaimer = (
                    f"[COLLAPSE:Platform Terms:Just so you know, we don't encourage going against the rules of {flow.platform.capitalize()} "
                    "or any other platform on which this limited computer use tool is being used. Always be mindful "
                    "of their terms of service! Anyway, I'll get this started for you.]"
                )
                messages_out.append(disclaimer)
                
                messages_out.append(
                    f"🎯 [{flow.platform.upper()}] {flow.description} — "
                    f"running {len(flow.steps)} steps (no LLM)"
                )

                def _progress(step_num, desc, status):
                    logger.info("[Flow %s] Step %d/%d: %s [%s]",
                                flow.task_id, step_num, len(flow.steps), desc, status)

                result = run_social_task(flow.task_id, params, _progress)

                if result.get("success"):
                    messages_out.append(f"✅ Done — {flow.description}")
                else:
                    stopped = result.get("stopped_at_step", "?")
                    error = result.get("error", "Unknown error")
                    messages_out.append(
                        f"❌ Flow stopped at step {stopped}: {error}\n"
                        f"Please check the screen and try again."
                    )

                # HARD RETURN — LLM never runs for social media tasks
                self._capture_and_encode()
                return {
                    "status": "success",
                    "messages": messages_out,
                    "is_done": True,
                    "image_data": self._draw_and_encode_base64(),
                }
        # ─────────────────────────────────────────────────────────────────────

        # ── LOCAL MUNDANE CHATBOT (NO AI) ────────────────────────────────────
        if user_message:
            msg_lower = user_message.strip().lower()
            import re
            msg_clean = re.sub(r'[^a-z0-9\s]', '', msg_lower)
            words = msg_clean.split()
            
            # Greetings
            if msg_clean in ["hi", "hello", "hey", "sup", "greetings", "good morning", "good evening", "hi there"]:
                return {
                    "status": "success",
                    "messages": ["Hi! How can I assist you today?"],
                    "image_data": self._draw_and_encode_base64(),
                }
                
            # Product info
            product_patterns = [
                r"^what is this( product)?( about)?$", 
                r"^what do you do$", 
                r"^how can you help( me)?$", 
                r"^what are you$", 
                r"^who are you$"
            ]
            if any(re.match(p, msg_clean) for p in product_patterns):
                return {
                    "status": "success",
                    "messages": ["You may use me whichever way you want to assist you in building your career or something like that!"],
                    "image_data": self._draw_and_encode_base64(),
                }
                
            # Generic parrot for short phrases/words (including bad words)
            command_keywords = ["open", "go", "click", "type", "search", "find", "scroll", "book", "buy", "navigate", "post", "share", "yes", "proceed", "resume", "next", "continue"]
            is_command = any(kw in msg_clean for kw in command_keywords)
            
            # If it's a short phrase (1-2 words) and doesn't contain a command keyword, parrot it.
            if len(words) <= 2 and not is_command:
                return {
                    "status": "success",
                    "messages": [f"'{user_message}' - I don't know the meaning of this so I repeated it back to you!"],
                    "image_data": self._draw_and_encode_base64(),
                }
        # ─────────────────────────────────────────────────────────────────────

        # ── TIER-1 ONLY PRODUCT MODE — block Tier-2 LLM ─────────────────────
        from aha.product_mode import TIER1_ONLY_HELP, tier1_only_mode

        if tier1_only_mode():
            self._capture_and_encode()
            return {
                "status": "success",
                "messages": [TIER1_ONLY_HELP],
                "image_data": self._draw_and_encode_base64(),
            }

        # 1. Take screenshot
        pil_image = self._capture_and_encode()

        # 2. Extract OCR Text locally
        ocr_result = self.cortex._ocr.extract_text(self.latest_bgr)
        screen_text = ocr_result.full_text if ocr_result.full_text else "No text found on screen."

        # Clear plan if a new user request arrives (but NOT on auto-continue or confirmations)
        auto_continue_keywords = ["yes", "proceed", "resume", "go ahead", "continue", "next step", "please continue", "user_resumed"]
        if user_message and not any(kw in user_message.lower() for kw in auto_continue_keywords):
            self.current_plan = None
            self.current_plan_step = 0

        # Group words into blocks for visual overlays
        import re
        grouped_blocks = self.cortex._ocr.group_words_into_blocks(ocr_result.words, self.latest_bgr)
        
        candidate_blocks = []
        for b in grouped_blocks:
            clean_txt = re.sub(r'\s*\[.*?\]', '', b.text).strip()
            word_count = len(clean_txt.split())
            is_interactive = "[type:button]" in b.text.lower() or "[intent:" in b.text.lower()
            is_short = 0 < word_count <= 5
            cta_keywords = ["search", "submit", "login", "pay", "book", "add", "post", "next", "continue", "yes", "no", "cancel", "ok", "confirm", "cart"]
            has_cta = any(kw in clean_txt.lower() for kw in cta_keywords)
            
            if is_interactive or is_short or has_cta:
                # Expand text bbox to the enclosing button/container for precise clicking
                expanded_bbox, _ = self.cortex._ocr._expand_to_button(self.latest_bgr, b.bounding_box)
                from bol.schemas.visual import OCRWord
                candidate_blocks.append(OCRWord(text=b.text, bounding_box=expanded_bbox, confidence=b.confidence))
                
        self.last_candidate_blocks = candidate_blocks

        # 3. Build Prompt with structured Interactive Element catalog
        prompt = f"Here are all the text elements currently visible on the screen: {screen_text}\n"
        
        interactive_elements = []
        for word in ocr_result.words:
            if "[type:button]" in word.text or "[intent:" in word.text:
                interactive_elements.append(word.text)
                
        if interactive_elements:
            prompt += "\n\nDetected Interactive UI Elements (Buttons/Links) on Screen:\n"
            for elem in sorted(list(set(interactive_elements))):
                prompt += f"- {elem}\n"
                
        if candidate_blocks:
            prompt += "\n\nLabeled Visual Interactive Elements on Screen (Numbers correspond to the green [X] boxes overlaid on the image):\n"
            for idx, b in enumerate(candidate_blocks):
                prompt += f"[{idx}]: \"{b.text}\"\n"
                
        if user_message:
            prompt += f"\nThe user says: {user_message}"
        else:
            prompt += "\nWhat is the next logical step?"

        # 4. Hierarchical Plan-based Model Routing
        use_pro = False
        if self.current_plan and self.current_plan_step < len(self.current_plan):
            step_info = self.current_plan[self.current_plan_step]
            complexity = step_info.get("complexity", "simple").lower()
            if complexity == "hard":
                use_pro = True
            logger.info(f"Plan Routing: Step {self.current_plan_step} ('{step_info.get('description')}') is '{complexity}' -> Routing to {'Pro' if use_pro else 'Cheap'} model.")
        else:
            # Fallback to visual triggers if plan is not initialized yet
            critical_intents = ["[intent:purchase]", "[intent:agree]", "[intent:form_confirm]", "[intent:authenticate]"]
            has_critical_intent = any(intent in screen_text.lower() for intent in critical_intents)
            has_web_buttons = False
            for word in ocr_result.words:
                w_lower = word.text.lower()
                if "[zone:main-content]" in w_lower and "[type:button]" in w_lower:
                    has_web_buttons = True
                    break
            if has_critical_intent or has_web_buttons:
                use_pro = True
            logger.info(f"Visual Routing: No plan yet -> Routing to {'Pro' if use_pro else 'Cheap'} model.")
            
        # Determine routing to OpenAI vs Gemini (BYOK + .env)
        from aha.byok import apply_byok_to_config, tier2_api_key_missing_message

        apply_byok_to_config(self.config)

        use_openai = False
        if use_pro and self.config.openai_api_key:
            use_openai = True
            model_name = self.config.openai_model_name
        else:
            model_name = self.config.gemini_model_name if use_pro else self.config.gemini_model_name

        missing = tier2_api_key_missing_message(self.config, use_openai=use_openai)
        if missing:
            return {
                "status": "error",
                "messages": [missing],
                "image_data": self._draw_and_encode_base64(),
            }

        if not use_openai and self.config.gemini_api_key:
            genai.configure(api_key=self.config.gemini_api_key)

        # ALWAYS send the screenshot so the model can see the webpage
        self.needs_vision = True

        logger.info(f"Routing to {'OpenAI' if use_openai else 'Gemini'} model '{model_name}'.")

        try:
            # Determine if we need to draw labeled boxes on visual input
            current_image_base64 = None
            labeled_pil_image = pil_image
            
            if self.needs_vision:
                current_image_base64 = self._draw_and_encode_base64(bboxes=candidate_blocks, draw_numbers=True)
                if current_image_base64:
                    try:
                        header, encoded = current_image_base64.split(",", 1)
                        img_data = base64.b64decode(encoded)
                        import io
                        labeled_pil_image = Image.open(io.BytesIO(img_data))
                    except Exception as e:
                        logger.warning(f"Failed to decode base64 back to labeled PIL image: {e}")
            
            while True:
                # Send message with retry for rate limits
                max_retries = 3
                response_text = None
                for attempt in range(max_retries):
                    try:
                        if use_openai:
                            from openai import OpenAI
                            client = OpenAI(api_key=self.config.openai_api_key)
                            
                            messages = self._get_openai_messages(prompt, current_image_base64)
                            
                            has_img = any(isinstance(m.get("content"), list) and any(c.get("type") == "image_url" for c in m["content"]) for m in messages)
                            logger.info(f"Sending prompt to OpenAI model '{model_name}' (messages: {len(messages)}, with_image: {has_img})")
                            
                            response = client.chat.completions.create(
                                model=model_name,
                                messages=messages,
                                response_format={"type": "json_object"}
                            )
                            response_text = response.choices[0].message.content
                            
                            # Manually append the turn to history for OpenAI
                            self.chat_history.append({"role": "user", "parts": [prompt]})
                            self.chat_history.append({"role": "model", "parts": [response_text]})
                        else:
                            try:
                                model = genai.GenerativeModel(
                                    model_name=model_name,
                                    system_instruction=self.system_instruction
                                )
                            except Exception:
                                model = genai.GenerativeModel(model_name=model_name)
                                
                            chat = model.start_chat(history=self.chat_history)
                            if self.needs_vision:
                                response = chat.send_message([prompt, labeled_pil_image])
                            else:
                                response = chat.send_message(prompt)
                            response_text = response.text
                            # Save updated history
                            self.chat_history = chat.history
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
                
                raw_text = response_text.strip()
                
                # Clean JSON if model wrapped it in markdown
                if raw_text.startswith("```json"):
                    raw_text = raw_text.split("```json")[1]
                if raw_text.endswith("```"):
                    raw_text = raw_text.rsplit("```", 1)[0]
                raw_text = raw_text.strip()

                try:
                    action_data = json.loads(raw_text)
                    if isinstance(action_data, str):
                        action_data = {"action": "done", "message": action_data}
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON from model: {raw_text}")
                    messages_out.append(f"Agent generated invalid action format: {raw_text}")
                    return {"status": "error", "messages": messages_out, "image_data": self._draw_and_encode_base64()}

                # Update hierarchical plan if returned by model
                if "plan" in action_data:
                    self.current_plan = action_data["plan"]
                    self.current_plan_step = 0
                    logger.info(f"New hierarchical plan loaded: {self.current_plan}")
                    
                # Progress to the next step suggested by the model
                if "next_plan_step" in action_data:
                    self.current_plan_step = int(action_data["next_plan_step"])
                    logger.info(f"Progressed to plan step: {self.current_plan_step}")

                action = action_data.get("action")
                
                intent_msg = action_data.get("intent")
                if intent_msg:
                    messages_out.append(f"Intent: {intent_msg}")
                
                if action == "request_vision":
                    self.needs_vision = True
                    msg = action_data.get("message", "Requesting visual context to disambiguate the screen.")
                    logger.info(f"AI requested vision: {msg}. Retrying immediately...")
                    continue
                
                # Keep vision always on so the model always sees the screenshot
                break
            
            if action == "open_url":
                url = action_data.get("url", "")
                
                if is_native_app:
                    messages_out.append(f"Opening in-app browser to: {url}")
                    return {"status": "success", "messages": messages_out, "image_data": self._draw_and_encode_base64(), "open_browser_url": url}
                else:
                    import subprocess
                    import sys
                    messages_out.append(f"Opening URL in Google Chrome: {url}")

                    # Sanitize URL so it cannot break out of AppleScript string context.
                    safe_url = url.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "").replace("\r", "")

                    if sys.platform == "darwin":
                        try:
                            applescript = (
                                'tell application "Google Chrome"\n'
                                '    activate\n'
                                '    if not (exists (window 1)) then\n'
                                '        make new window\n'
                                '    end if\n'
                                '    tell window 1\n'
                                f'        make new tab with properties {{URL:"{safe_url}"}}\n'
                                '    end tell\n'
                                'end tell'
                            )
                            subprocess.run(["osascript", "-e", applescript], check=True, timeout=10)
                            time.sleep(2.5)

                            bounds_script = (
                                'tell application "Google Chrome"\n'
                                '    set b to bounds of window 1\n'
                                '    return (item 1 of b) & "," & (item 2 of b) & "," & (item 3 of b) & "," & (item 4 of b)\n'
                                'end tell'
                            )
                            result = subprocess.check_output(
                                ["osascript", "-e", bounds_script], timeout=5
                            ).decode().strip()
                            parts = [int(x.strip()) for x in result.split(",")]
                            x1, y1, x2, y2 = parts
                            import requests as _req
                            try:
                                _req.post(
                                    "http://127.0.0.1:8000/api/config/set_browser_region",
                                    json={"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1},
                                    timeout=1,
                                )
                            except Exception:
                                pass
                            messages_out.append(
                                f"Chrome opened at region ({x1},{y1},{x2-x1}×{y2-y1}) — agent now watching Chrome."
                            )
                        except Exception as e:
                            logger.warning(f"AppleScript Chrome open failed: {e}. Falling back.")
                            subprocess.run(["open", "-a", "Google Chrome", safe_url])
                            time.sleep(3)

                    elif sys.platform == "win32":
                        try:
                            chrome_paths = [
                                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                            ]
                            chrome_exe = next((p for p in chrome_paths if Path(p).exists()), None)
                            if chrome_exe:
                                subprocess.Popen([chrome_exe, safe_url])
                            else:
                                # Fallback: os.startfile or webbrowser
                                import webbrowser
                                webbrowser.get("chrome").open(safe_url)
                            time.sleep(3)
                        except Exception as e:
                            logger.warning(f"Windows Chrome open failed: {e}.")
                    else:
                        # Linux fallback
                        subprocess.Popen(["google-chrome", safe_url])
                        time.sleep(3)

                    return {"status": "success", "messages": messages_out, "image_data": self._draw_and_encode_base64()}

            elif action == "click":
                import re
                from bol.modules.m2_kinematic.bezier import BezierEngine
                
                raw_target = action_data.get("target", "")
                search_word = raw_target.strip()
                target_idx = 0
                has_explicit_index = False
                
                is_direct_box = False
                if search_word.lower().startswith("box:"):
                    box_idx_str = search_word.lower().split("box:")[1].strip()
                    try:
                        box_idx = int(box_idx_str)
                        if hasattr(self, "last_candidate_blocks") and self.last_candidate_blocks and 0 <= box_idx < len(self.last_candidate_blocks):
                            target_block = self.last_candidate_blocks[box_idx]
                            target_box = target_block.bounding_box
                            bboxes = [target_box]
                            is_direct_box = True
                            
                            import re
                            clean_click_txt = re.sub(r'\[.*?\]', '', target_block.text).strip()
                            # Override the internal search_word so the logs look human
                            search_word = clean_click_txt if clean_click_txt else f"icon/element (box {box_idx})"
                            
                            logger.info(f"Direct Coordinate Click: index {box_idx} -> target box: {target_box}")
                        else:
                            msg = f"Direct click box index {box_idx} is out of bounds or expired. Please click manually and press Resume!"
                            messages_out.append(msg)
                            self.is_paused = True
                            return {"status": "success", "messages": messages_out, "is_paused": True, "image_data": self._draw_and_encode_base64()}
                    except ValueError:
                        pass
                
                if not is_direct_box:
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
                else:
                    messages_out.append(f"Agent clicking: '{search_word}'")
                
                try:
                    box = bboxes[target_idx]
                except IndexError:
                    msg = f"I found '{search_word}', but requested index {target_idx} is out of bounds. Please click it manually and press Resume!"
                    messages_out.append(msg)
                    self.is_paused = True
                    return {"status": "success", "messages": messages_out, "is_paused": True, "image_data": self._draw_and_encode_base64()}
                click_target = self.cortex._targeting.compute_click_target(box)
                final_x = click_target.click_x
                final_y = click_target.click_y
                if hasattr(self.config, "browser_window_enabled") and self.config.browser_window_enabled:
                    final_x += self.config.browser_window_x
                    final_y += self.config.browser_window_y
                final_point = Point2D(x=final_x, y=final_y)
                
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
                
                # Human hesitation delay before typing starts
                time.sleep(random.uniform(0.4, 0.8))
                
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

            elif action == "scroll":
                clicks = action_data.get("clicks", -10)
                messages_out.append(f"Agent scrolling {'down' if clicks < 0 else 'up'} by {abs(clicks)} clicks.")
                pyautogui.scroll(clicks)
                time.sleep(1.0) # Wait for momentum scroll to stop
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
