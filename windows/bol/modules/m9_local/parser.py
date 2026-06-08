"""
Parse user chat into Tier-1 local tasks (no LLM).

Domains: dev (git, env, ssh), os (bluetooth, settings), files (open project).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from aha.local_registry import list_projects, resolve_project_path


@dataclass
class LocalTask:
    flow_id: str
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""


def _extract_quoted(text: str) -> Optional[str]:
    m = re.search(r'["\u201c\u201d\']([^"\u201c\u201d\']+)["\u201c\u201d\']', text)
    return m.group(1).strip() if m else None


def _extract_device_name(text: str) -> Optional[str]:
    quoted = _extract_quoted(text)
    if quoted:
        return quoted

    patterns = [
        r"(?:connect|pair|link)\s+(?:to|with)\s+(?:my\s+)?(.+?)(?:\s+via|\s+using|\s+bluetooth|$)",
        r"bluetooth\s+(?:device\s+)?(.+?)(?:\s+via|$)",
        r"(?:noise|airpods|buds|headphones|speaker)\s+[\w\s\-]+",
    ]
    lower = text.lower()
    for pat in patterns:
        m = re.search(pat, lower, re.I)
        if m:
            name = m.group(1).strip() if m.lastindex else m.group(0).strip()
            name = re.sub(r"\s+bluetooth\s*$", "", name, flags=re.I).strip()
            if name and len(name) > 1:
                return name.title() if name.islower() else name
    return None


def _extract_project_ref(text: str) -> Optional[str]:
    # Absolute / home path
    path_m = re.search(r"(~[/\\][^\s]+|/[^\s]+|[A-Za-z]:\\[^\s]+)", text)
    if path_m:
        return path_m.group(1)

    # "project dailyassist", "repo foo", "dailyassist project"
    for pat in (
        r"(?:project|repo|repository)\s+([a-zA-Z0-9_\-\.]+)",
        r"\b([a-zA-Z0-9_\-\.]+)\s+(?:project|repo|repository)\b",
        r"push\s+([a-zA-Z0-9_\-\.]+)\s+to\s+git",
        r"git\s+push\s+([a-zA-Z0-9_\-\.]+)",
        r"open\s+(?:my\s+)?(?:project\s+)?([a-zA-Z0-9_\-\.]+)",
        r"for\s+(?:project\s+)?([a-zA-Z0-9_\-\.]+)",
    ):
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1)

    # Any registered project name mentioned in the message (e.g. "for dailyassist")
    for proj in list_projects():
        name = (proj.get("name") or "").strip()
        if name and re.search(rf"\b{re.escape(name)}\b", text, re.I):
            return name

    projects = list_projects()
    if len(projects) == 1:
        return projects[0]["name"]
    return None


def _resolve_repo_params(text: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    ref = _extract_project_ref(text)
    if ref:
        path = resolve_project_path(ref)
        if path:
            params["repo_path"] = str(path)
            proj = None
            for p in list_projects():
                if p.get("path") == str(path) or p.get("name", "").lower() == ref.lower():
                    proj = p
                    break
            if proj:
                params["branch"] = proj.get("branch", "main")
                params["remote"] = proj.get("remote", "origin")
    return params


def detect_local_task(user_text: str) -> Optional[LocalTask]:
    if not user_text or not user_text.strip():
        return None

    text = user_text.strip()
    lower = text.lower()

    # ── SSH setup ─────────────────────────────────────────────────────────
    if re.search(r"\b(generate|create|setup|set up)\b.*\bssh\b", lower) or re.search(
        r"\bssh\b.*\b(key|keys)\b", lower
    ):
        overwrite = "overwrite" in lower or "regenerate" in lower
        return LocalTask(
            flow_id="ssh_setup",
            params={"overwrite": overwrite},
            description="Generate SSH key for Git",
        )

    if re.search(r"\b(show|display|get)\b.*\b(ssh|public)\s*key\b", lower):
        return LocalTask(flow_id="ssh_show", params={}, description="Show SSH public key")

    # ── .env.local ────────────────────────────────────────────────────────
    if re.search(r"\.env\.local", lower) or re.search(r"\.env\b", lower) or re.search(
        r"\b(create|make|setup|set up|scaffold)\b.*\b(env|environment)\b", lower
    ):
        params = _resolve_repo_params(text)
        params["overwrite"] = "overwrite" in lower or "replace" in lower
        return LocalTask(
            flow_id="create_env_local",
            params=params,
            description="Create .env.local from project template",
        )

    # ── Git push / status / commit ────────────────────────────────────────
    if re.search(r"\bgit\s+push\b", lower) or re.search(r"\bpush\b.*\bto\s+git\b", lower) or (
        "push" in lower and "git" in lower
    ):
        params = _resolve_repo_params(text)
        return LocalTask(flow_id="git_push", params=params, description="Push to git remote")

    if re.search(r"\bgit\s+status\b", lower) or re.search(r"\b(check|show)\b.*\bgit\b", lower):
        params = _resolve_repo_params(text)
        return LocalTask(flow_id="git_status", params=params, description="Git status")

    commit_m = re.search(
        r"(?:commit|git commit)(?:\s+with\s+(?:message\s+)?)?[\"'\u201c\u201d]([^\"'\u201c\u201d]+)[\"'\u201c\u201d]",
        text,
        re.I,
    )
    if commit_m:
        params = _resolve_repo_params(text)
        params["commit_message"] = commit_m.group(1).strip()
        return LocalTask(flow_id="git_commit", params=params, description="Git commit")

    # ── Open project ──────────────────────────────────────────────────────
    if re.search(r"\bopen\b.*\b(project|repo|folder)\b", lower) or re.search(
        r"\bopen\s+my\s+[a-z]", lower
    ):
        params = _resolve_repo_params(text)
        if "cursor" in lower:
            params["editor"] = "cursor"
        elif "vscode" in lower or "vs code" in lower or "code" in lower:
            params["editor"] = "code"
        return LocalTask(
            flow_id="open_project",
            params=params,
            description="Open registered project folder",
        )

    # ── Bluetooth ─────────────────────────────────────────────────────────
    if re.search(r"\b(bluetooth|bt)\b", lower) and re.search(
        r"\b(connect|pair|link)\b", lower
    ):
        device = _extract_device_name(text)
        if device:
            return LocalTask(
                flow_id="bluetooth_connect",
                params={"device_name": device},
                description=f"Connect Bluetooth device: {device}",
            )

    if re.search(r"\bopen\b.*\bbluetooth\b.*\bsettings\b", lower):
        return LocalTask(
            flow_id="open_bluetooth_settings",
            params={},
            description="Open Bluetooth settings",
        )

    return None
