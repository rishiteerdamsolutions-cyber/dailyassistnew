"""
Tier-1 local flow registry — maps flow_id → native action(s).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LocalFlow:
    flow_id: str
    description: str
    native_action: str  # m9_native action name


LOCAL_FLOWS: dict[str, LocalFlow] = {
    "git_push": LocalFlow("git_push", "Push committed changes to git remote", "git_push"),
    "git_status": LocalFlow("git_status", "Show git working tree status", "git_status"),
    "git_commit": LocalFlow("git_commit", "Commit all tracked changes", "git_commit"),
    "create_env_local": LocalFlow(
        "create_env_local",
        "Scaffold .env.local from .env.example",
        "create_env_local",
    ),
    "open_project": LocalFlow("open_project", "Open project folder in Finder/Explorer", "open_project"),
    "bluetooth_connect": LocalFlow(
        "bluetooth_connect",
        "Connect a paired Bluetooth device",
        "bluetooth_connect",
    ),
    "open_bluetooth_settings": LocalFlow(
        "open_bluetooth_settings",
        "Open system Bluetooth settings",
        "open_bluetooth_settings",
    ),
}


def get_flow(flow_id: str) -> LocalFlow | None:
    return LOCAL_FLOWS.get(flow_id)
