"""Unified Tier-1 routing — local precision + social flows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class Tier1Domain(str, Enum):
    LOCAL = "local"
    SOCIAL = "social"


@dataclass
class Tier1Match:
    domain: Tier1Domain
    flow_id: str
    params: dict[str, Any]
    description: str = ""
    social_flow: Any = None  # SocialFlow when domain is SOCIAL
    local_task: Any = None  # LocalTask when domain is LOCAL


def detect_tier1(user_text: str) -> Optional[Tier1Match]:
    """
    Detect any Tier-1 task from user message.

    Local tasks are checked before social so dev phrases don't misfire.
    """
    from bol.modules.m9_local.parser import detect_local_task

    local = detect_local_task(user_text)
    if local:
        return Tier1Match(
            domain=Tier1Domain.LOCAL,
            flow_id=local.flow_id,
            params=dict(local.params),
            description=local.description,
            local_task=local,
        )

    from bol.modules.m9_social.flows import detect_flow

    social = detect_flow(user_text)
    if social:
        return Tier1Match(
            domain=Tier1Domain.SOCIAL,
            flow_id=social.task_id,
            params={},
            description=social.description,
            social_flow=social,
        )

    return None
