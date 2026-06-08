"""
Tier-1 native command runner — allowlisted subprocess only.

No shell=True. No arbitrary user shell strings.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from bol.utils.logging import get_logger

logger = get_logger(__name__)

_IS_MAC = sys.platform == "darwin"
_IS_WIN = sys.platform == "win32"


def _run(argv: list[str], *, cwd: Optional[Path] = None, timeout: float = 60.0) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
            "command": argv,
        }
    except FileNotFoundError:
        return {"ok": False, "error": f"Command not found: {argv[0]}", "command": argv}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Timed out after {timeout}s", "command": argv}


def _git(repo: Path, *args: str) -> dict[str, Any]:
    return _run(["git", "-C", str(repo), *args], cwd=repo)


def _open_folder(path: Path) -> dict[str, Any]:
    if _IS_MAC:
        return _run(["open", str(path)])
    if _IS_WIN:
        return _run(["explorer", str(path)])
    return _run(["xdg-open", str(path)])


def _open_in_editor(path: Path, editor: str) -> dict[str, Any]:
    editor = editor.lower()
    if editor in ("cursor", "code", "vscode"):
        bin_name = "cursor" if editor == "cursor" else "code"
        from shutil import which

        if which(bin_name):
            return _run([bin_name, str(path)])
    return {"ok": False, "error": f"Editor '{editor}' not found in PATH"}


def _open_bluetooth_settings() -> dict[str, Any]:
    if _IS_MAC:
        # Ventura+ Bluetooth pane
        r = _run(["open", "x-apple.systempreferences:com.apple.BluetoothSettings"])
        if r.get("ok"):
            return r
        return _run(["open", "-b", "com.apple.systempreferences"])
    if _IS_WIN:
        return _run(["cmd", "/c", "start", "ms-settings:bluetooth"])
    return _run(["xdg-open", "bluetooth:"])


def run_native_action(action: str, params: dict[str, Any]) -> dict[str, Any]:
    """
    Execute an allowlisted native action.

    Returns dict with at least ``success`` bool and human-readable ``message``.
    """
    action = action.strip()
    logger.info("m9_native action=%s params=%s", action, list(params.keys()))

    if action == "git_status":
        repo = Path(params["repo_path"]).resolve()
        if not (repo / ".git").exists():
            return {"success": False, "message": f"Not a git repository: {repo}"}
        r = _git(repo, "status", "--short", "--branch")
        if r.get("ok"):
            out = r.get("stdout") or "Working tree clean"
            return {"success": True, "message": f"Git status for {repo.name}:\n{out}", "output": out}
        err = r.get("stderr") or r.get("error") or "git status failed"
        return {"success": False, "message": err}

    if action == "git_push":
        repo = Path(params["repo_path"]).resolve()
        remote = params.get("remote") or "origin"
        branch = params.get("branch") or "main"
        if not (repo / ".git").exists():
            return {"success": False, "message": f"Not a git repository: {repo}"}

        status = _git(repo, "status", "--porcelain")
        if status.get("stdout"):
            return {
                "success": False,
                "message": (
                    "You have uncommitted changes. Commit first or ask me to "
                    f"'commit with message …' before pushing.\n{status['stdout']}"
                ),
            }

        from aha.local_registry import git_current_branch

        if branch == "main" and params.get("use_current_branch", True):
            branch = git_current_branch(repo)

        r = _git(repo, "push", remote, branch)
        if r.get("ok"):
            msg = r.get("stdout") or r.get("stderr") or "Push completed."
            return {
                "success": True,
                "message": f"Pushed {repo.name} → {remote}/{branch}\n{msg}".strip(),
            }
        err = r.get("stderr") or r.get("error") or "git push failed"
        return {"success": False, "message": err}

    if action == "git_commit":
        repo = Path(params["repo_path"]).resolve()
        message = (params.get("commit_message") or "").strip()
        if not message:
            return {"success": False, "message": "Commit message is required."}
        r = _git(repo, "commit", "-am", message)
        if r.get("ok"):
            out = r.get("stdout") or "Committed."
            return {"success": True, "message": f"Committed in {repo.name}: {out}"}
        err = r.get("stderr") or r.get("error") or "git commit failed"
        return {"success": False, "message": err}

    if action == "open_project":
        repo = Path(params["repo_path"]).resolve()
        r = _open_folder(repo)
        if not r.get("ok"):
            return {"success": False, "message": r.get("error") or "Could not open folder"}

        editor = (params.get("editor") or "").strip().lower()
        extra = ""
        if editor:
            er = _open_in_editor(repo, editor)
            if er.get("ok"):
                extra = f" Opened in {editor}."
            else:
                extra = f" ({er.get('error', 'editor open failed')})"
        return {"success": True, "message": f"Opened project folder: {repo}{extra}"}

    if action == "create_env_local":
        repo = Path(params["repo_path"]).resolve()
        overwrite = bool(params.get("overwrite"))
        target = repo / ".env.local"
        example = repo / ".env.example"
        env_file = repo / ".env"

        if target.exists() and not overwrite:
            return {
                "success": False,
                "message": (
                    f"{target} already exists. Say 'overwrite .env.local' if you want to replace it."
                ),
            }

        source = example if example.is_file() else (env_file if env_file.is_file() else None)
        if source:
            text = source.read_text(encoding="utf-8", errors="replace")
        else:
            text = (
                "# Created by AHA — fill in your local secrets\n"
                "NODE_ENV=development\n"
            )

        from aha.storage_vault import atomic_write_text

        atomic_write_text(target, text if text.endswith("\n") else text + "\n")
        keys = [ln.split("=", 1)[0].strip() for ln in text.splitlines() if "=" in ln and not ln.strip().startswith("#")]
        summary = ", ".join(keys[:12])
        if len(keys) > 12:
            summary += f", … (+{len(keys) - 12} more)"
        return {
            "success": True,
            "message": (
                f"Created {target}\n"
                f"Keys: {summary or '(add your variables)'}\n"
                "Tip: never commit .env.local — it should stay in .gitignore."
            ),
            "path": str(target),
            "keys": keys,
        }

    if action == "bluetooth_connect":
        device = (params.get("device_name") or "").strip()
        if not device:
            return {"success": False, "message": "Device name is required (e.g. 'Noise Buds')."}

        from bol.modules.m9_local.bluetooth_vision import connect_via_system_settings

        return connect_via_system_settings(device)

    if action == "open_bluetooth_settings":
        r = _open_bluetooth_settings()
        if r.get("ok"):
            return {"success": True, "message": "Opened Bluetooth settings."}
        return {"success": False, "message": r.get("error") or "Could not open Bluetooth settings"}

    return {"success": False, "message": f"Unknown native action: {action}"}
