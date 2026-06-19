"""
ws/handler.py — WebSocket session handler for AHA Chrome Extension.

Connection URL:
  ws://<host>/ws/agent

Message protocol (Extension → Backend):
  {
    "type":         "execute",
    "platform":     "linkedin" | "instagram" | "facebook" | "x" | "whatsapp",
    "slots":        {"text": str, "image": bool, "video": bool},
    "day":          int,           // Day number (for scheduling logic)
    "elements":     [              // Page element snapshot
                      {
                        "text": str,
                        "x": float, "y": float,
                        "width": float, "height": float,
                        "tag": str,    // optional
                        "role": str,   // optional
                      },
                      ...
                    ],
    "viewport":     {"width": int, "height": int},
    "currentMouse": {"x": float, "y": float}
  }

Message protocol (Backend → Extension):
  {action: "move_mouse",    path: [[x,y],...], duration_ms: float}
  {action: "click",         x: float, y: float}
  {action: "type_text",     keystrokes: [{key,text,delay_before_ms,shift},...]}
  {action: "upload_file"}                        // trigger OS file picker
  {action: "wait",          duration_ms: float}  // explicit pause
  {action: "done",          success: bool, message: str}
  {action: "error",         message: str}

License enforcement:
  - REMOVED.
"""

from __future__ import annotations

import json
import logging
import os


from fastapi import WebSocket, WebSocketDisconnect
from google.cloud.firestore import AsyncClient

from agents.kinematic import generate_mouse_path, generate_scroll_profile
from agents.linguistic import generate_keystrokes
from agents.policy import select_personality, PersonalityVector
from flows.base import SocialFlow
from flows.linkedin import LinkedInFlow
from flows.instagram import InstagramFlow
from flows.facebook import FacebookFlow
from flows.whatsapp import WhatsAppFlow
from flows.x import XFlow

logger = logging.getLogger(__name__)

_LICENSES_COLLECTION = "licenses"


# ── Flow registry ─────────────────────────────────────────────────────────────

def _get_flow(platform: str, slots: dict) -> SocialFlow | None:
    registry: dict[str, type[SocialFlow]] = {
        "linkedin":  LinkedInFlow,
        "instagram": InstagramFlow,
        "facebook":  FacebookFlow,
        "whatsapp":  WhatsAppFlow,
        "x":         XFlow,
        "twitter":   XFlow,
    }
    cls = registry.get(platform.lower())
    if cls is None:
        return None
    return cls(slots)


# ── Command senders ───────────────────────────────────────────────────────────

async def _send(ws: WebSocket, payload: dict) -> None:
    """JSON-encode and send a command frame to the extension."""
    await ws.send_text(json.dumps(payload))


async def _send_mouse_move(
    ws: WebSocket,
    path: list[tuple[float, float]],
    duration_ms: float,
) -> None:
    await _send(ws, {
        "action": "move_mouse",
        "path": [[round(x, 2), round(y, 2)] for x, y in path],
        "duration_ms": round(duration_ms, 2),
    })


async def _send_click(ws: WebSocket, x: float, y: float) -> None:
    await _send(ws, {"action": "click", "x": round(x, 2), "y": round(y, 2)})


async def _send_type(ws: WebSocket, keystrokes: list) -> None:
    await _send(ws, {
        "action": "type_text",
        "keystrokes": [
            {
                "key":             ks.key,
                "text":            ks.text,
                "delay_before_ms": round(ks.delay_before_ms, 2),
                "shift":           ks.shift,
            }
            for ks in keystrokes
        ],
    })


async def _send_upload_signal(ws: WebSocket) -> None:
    await _send(ws, {"action": "upload_file"})


async def _send_done(ws: WebSocket, success: bool, message: str) -> None:
    await _send(ws, {"action": "done", "success": success, "message": message})


async def _send_error(ws: WebSocket, message: str) -> None:
    await _send(ws, {"action": "error", "message": message})


async def _send_rescan(ws: WebSocket) -> list[dict]:
    await _send(ws, {"action": "scan_screen"})
    msg_str = await ws.receive_text()
    msg = json.loads(msg_str)
    return msg.get("elements", [])


# ── Main handler ──────────────────────────────────────────────────────────────

async def handle_agent_session(
    ws: WebSocket,
    db: AsyncClient,
) -> None:
    """
    Full lifecycle of a single AHA agent WebSocket session.

    Accepts the WebSocket, then processes incoming
    'execute' messages until the client disconnects or an error occurs.
    """
    await ws.accept()
    logger.info("WS connected")

    # ── Session loop ──────────────────────────────────────────────────────────
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg: dict = json.loads(raw)
            except json.JSONDecodeError:
                await _send_error(ws, "Invalid JSON message.")
                continue

            msg_type = msg.get("type", "")

            if msg_type != "execute":
                await _send_error(ws, f"Unknown message type: '{msg_type}'.")
                continue

            await _process_execute(ws, msg)

    except WebSocketDisconnect:
        logger.info("WS disconnected gracefully")
    except Exception as exc:
        logger.exception("Unhandled error in WS session: %s", exc)
        try:
            await _send_error(ws, "Internal server error.")
        except Exception:
            pass


async def _process_execute(ws: WebSocket, msg: dict) -> None:
    """Process a single 'execute' message and stream commands back."""
    import asyncio
    
    platform: str = msg.get("platform", "").lower()
    slots: dict = msg.get("slots", {})
    elements: list[dict] = msg.get("elements", [])
    logger.info("=== Visual Elements Received ===\n%s", json.dumps(elements, indent=2))
    viewport: dict = msg.get("viewport", {"width": 1280, "height": 800})
    current_mouse: dict = msg.get("currentMouse", {"x": 0.0, "y": 0.0})

    # Validate platform
    flow = _get_flow(platform, slots)
    if flow is None:
        await _send_error(ws, f"Unsupported platform: '{platform}'.")
        return

    # Select personality for this execution
    personality: PersonalityVector = select_personality()
    logger.info(
        "Executing %s flow — personality: %s",
        platform, personality.name,
    )

    cursor_x: float = float(current_mouse.get("x", 0.0))
    cursor_y: float = float(current_mouse.get("y", 0.0))

    steps = flow.get_steps()
    logger.info("Flow steps: %s", steps)

    for step in steps:
        logger.debug("Step: %s", step)

        # ── upload_signal: special action, no mouse movement needed ──────────
        if step == "upload_signal":
            await asyncio.sleep(1.0) # Wait for file picker
            await _send_upload_signal(ws)
            logger.info("Upload signal sent. Waiting 12 seconds for media to upload and UI to update...")
            await asyncio.sleep(12.0) # Wait for large video files to actually attach and enable the Post button
            continue

        # ── Sleep briefly to mimic human reaction time and allow UI animations 
        # SPAs like Facebook can take 2-4 seconds to fully render a modal popup
        await asyncio.sleep(3.0)

        # ── Re-scan the screen dynamically to see new modals or buttons ──────
        elements = await _send_rescan(ws)

        # ── Find the target element for this step ─────────────────────────────
        target = flow.find_target(elements, step)
        if target is None:
            logger.warning("Step '%s' — target not found in element list.", step)
            await _send_done(
                ws, False,
                f"Could not find target element for step '{step}' on {platform}.",
            )
            return

        tx, ty, tw, th = target

        # ── Generate and send mouse trajectory ────────────────────────────────
        traj = generate_mouse_path(cursor_x, cursor_y, tx, ty, tw, th)
        await _send_mouse_move(ws, traj.path, traj.total_duration_ms)

        # Update cursor to where we actually ended up (last path point)
        if traj.path:
            cursor_x, cursor_y = traj.path[-1]

        # Human micro-pause before clicking (150ms - 400ms)
        import random
        await asyncio.sleep(0.15 + random.random() * 0.25)

        # ── Click ─────────────────────────────────────────────────────────────
        await _send_click(ws, cursor_x, cursor_y)

        # ── If this is a text-entry step, also generate keystrokes ────────────
        if step == "type_text" or step == "type_caption":
            # Human pause to position hands on keyboard after clicking (800ms - 1500ms)
            await asyncio.sleep(0.8 + random.random() * 0.7)
            
            text_content: str = slots.get("text", "")
            if text_content:
                keystrokes = generate_keystrokes(text_content, personality)
                await _send_type(ws, keystrokes)

    await _send_done(ws, True, f"{platform.capitalize()} post flow completed.")
