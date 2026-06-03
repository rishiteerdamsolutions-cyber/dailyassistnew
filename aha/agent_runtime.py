"""
Shared agent singleton for FastAPI — reset when BYOK keys change.

A threading lock serializes AutonomousCompanion.step() so concurrent
chat/resume requests cannot corrupt chat_history or plan state.
"""

from __future__ import annotations

import threading
from typing import Any

from bol.config import get_config
from bol.modules.m8_orchestrator.agent import AutonomousCompanion

from aha.byok import apply_byok_to_config

_agent_instance: AutonomousCompanion | None = None
_agent_lock = threading.Lock()


def get_agent() -> AutonomousCompanion:
    global _agent_instance
    if _agent_instance is None:
        config = get_config()
        apply_byok_to_config(config)
        _agent_instance = AutonomousCompanion(config)
    return _agent_instance


def reset_agent() -> None:
    """Drop cached agent so the next request picks up new BYOK / config."""
    global _agent_instance
    with _agent_lock:
        _agent_instance = None


def agent_step(
    agent: AutonomousCompanion,
    *,
    user_message: str | None = None,
    is_native_app: bool = False,
) -> dict[str, Any]:
    """Run one agent step under the process-wide lock."""
    with _agent_lock:
        return agent.step(user_message=user_message, is_native_app=is_native_app)


def agent_clear_session(agent: AutonomousCompanion) -> None:
    """Reset agent chat state under the lock."""
    with _agent_lock:
        agent.chat_history = []
        agent.current_plan = None
        agent.current_plan_step = 0
