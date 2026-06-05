"""Execute Tier-1 local flows via m9_native (deterministic, no LLM)."""

from __future__ import annotations

from typing import Any, Callable, Optional

from bol.modules.m9_local.flows import get_flow
from bol.modules.m9_local.parser import LocalTask
from bol.modules.m9_native.runner import run_native_action
from bol.utils.logging import get_logger

logger = get_logger(__name__)

ProgressFn = Callable[[int, str, str], None]


def _ssh_setup(params: dict[str, Any]) -> dict[str, Any]:
    from aha.local_registry import generate_ssh_key

    result = generate_ssh_key(overwrite=bool(params.get("overwrite")))
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "SSH key generation failed")}

    pub = result.get("public_key") or ""
    msg = result.get("message") or "SSH key ready."
    if pub:
        msg += f"\n\nPublic key (paste into GitHub/GitLab):\n{pub}"
    return {"success": True, "message": msg}


def _ssh_show(_params: dict[str, Any]) -> dict[str, Any]:
    from aha.local_registry import read_public_key, ssh_key_exists

    if not ssh_key_exists():
        return {
            "success": False,
            "error": "No SSH key yet. Say 'generate ssh key' to create one.",
        }
    pub = read_public_key()
    return {
        "success": True,
        "message": f"Your AHA SSH public key:\n{pub}",
    }


def run_local_task(
    task: LocalTask,
    progress: Optional[ProgressFn] = None,
) -> dict[str, Any]:
    """Run a parsed local task. Returns {success, message|error, ...}."""

    def _prog(step: int, desc: str, status: str) -> None:
        if progress:
            progress(step, desc, status)

    flow_id = task.flow_id
    _prog(1, task.description or flow_id, "start")

    if flow_id == "ssh_setup":
        result = _ssh_setup(task.params)
        _prog(2, "SSH key", "done" if result.get("success") else "failed")
        return result

    if flow_id == "ssh_show":
        result = _ssh_show(task.params)
        _prog(2, "SSH public key", "done" if result.get("success") else "failed")
        return result

    flow = get_flow(flow_id)
    if not flow:
        return {"success": False, "error": f"Unknown local flow: {flow_id}"}

    if flow_id == "bluetooth_connect":
        from bol.modules.m9_local.bluetooth_vision import connect_via_system_settings

        device = (task.params.get("device_name") or "").strip()
        _prog(2, flow.description, "running")
        native = connect_via_system_settings(device, progress=_prog)
        ok = bool(native.get("success"))
        _prog(5, flow.description, "done" if ok else "failed")
        if ok:
            return {"success": True, "message": native.get("message", "Done.")}
        return {
            "success": False,
            "error": native.get("message") or "Bluetooth connect failed",
        }

    if flow_id in ("git_push", "git_status", "git_commit", "create_env_local", "open_project"):
        if not task.params.get("repo_path"):
            return {
                "success": False,
                "error": (
                    "No project path found. Register a project in Settings → Local Workspace, "
                    "or include the folder path in your message."
                ),
            }

    _prog(2, flow.description, "running")
    native = run_native_action(flow.native_action, task.params)
    ok = bool(native.get("success"))
    _prog(3, flow.description, "done" if ok else "failed")

    if ok:
        return {"success": True, "message": native.get("message", "Done.")}
    return {
        "success": False,
        "error": native.get("message") or native.get("error") or "Local task failed",
    }
