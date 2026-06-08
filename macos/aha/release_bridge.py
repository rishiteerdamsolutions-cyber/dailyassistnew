"""
Server-side wrapper around the agent — cloud limits + vault ticks.

Does NOT modify bol agents, flows, or executor. Hooks only in server.py.
"""

from __future__ import annotations

from typing import Any, Optional

from bol.utils.logging import get_logger

logger = get_logger(__name__)


def _detect_flow(user_text: str):
    from bol.modules.m9_social.flows import detect_flow

    return detect_flow(user_text)


def pre_agent_chat(user_text: str) -> tuple[Optional[dict[str, Any]], Any]:
    """
    Before agent.step(): block if daily platform limit already used.

    Returns (block_response, flow). When block_response is set, return it to the UI.
    """
    flow = _detect_flow(user_text or "")
    if not flow:
        return None, None

    from aha.cloud_client import LIMIT_MESSAGE, check_platform_limit

    limit = check_platform_limit(flow.platform)
    if limit.get("allowed"):
        return None, flow

    msg = limit.get("message") or LIMIT_MESSAGE
    logger.warning("Cloud limit blocked %s: %s", flow.platform, msg)
    return {
        "status": "error",
        "messages": [msg],
        "is_done": True,
    }, None


def post_agent_chat(
    user_text: str,
    result: dict[str, Any],
    flow: Any,
) -> dict[str, Any]:
    """
    After agent.step(): on successful social post, vault tick + cloud confirm.

    Uses agent message text (✅ Done) — no executor changes required.
    """
    if not flow:
        return result

    messages = list(result.get("messages") or [])
    posted_ok = any("✅ Done" in str(m) for m in messages)
    out = dict(result)

    if posted_ok:
        try:
            from aha.post_completion import complete_verified_post

            complete_verified_post(flow.platform, flow.task_id, {})
            messages.append(
                f"✓ {flow.platform.capitalize()} marked posted in your vault for today."
            )
            out["status"] = "success"
        except Exception as exc:
            logger.error("Post completion hook failed: %s", exc)
    elif any("❌" in str(m) for m in messages):
        messages.append("Your daily limit was not used — you can try again.")
        out["status"] = "error"

    out["messages"] = messages
    return out
