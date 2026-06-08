"""
Tier-1 local workspace registry — projects, SSH keys, paths.

Stored under ~/.aha/ (never committed to git).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from aha.license import AHA_DIR, ensure_aha_dir
from aha.storage_vault import atomic_write_text

PROJECTS_FILE = AHA_DIR / "projects.json"
SSH_DIR = AHA_DIR / "keys"
DEFAULT_SSH_PRIVATE = SSH_DIR / "id_ed25519"
DEFAULT_SSH_PUBLIC = SSH_DIR / "id_ed25519.pub"

_PROJECT_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-\.]{0,127}$")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _save_json(path: Path, data: dict[str, Any]) -> None:
    ensure_aha_dir()
    atomic_write_text(path, json.dumps(data, indent=2, default=str) + "\n")


def _normalize_path(raw: str) -> Path:
    p = Path(raw.strip()).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    else:
        p = p.resolve()
    return p


def _path_allowed(path: Path) -> bool:
    """Reject paths outside the user home (except explicit registration)."""
    try:
        path.resolve().relative_to(Path.home().resolve())
        return True
    except ValueError:
        return False


def list_projects() -> list[dict[str, Any]]:
    data = _load_json(PROJECTS_FILE)
    return list(data.get("projects") or [])


def get_project(name: str) -> Optional[dict[str, Any]]:
    key = name.strip().lower()
    for proj in list_projects():
        if proj.get("name", "").lower() == key:
            return proj
    return None


def resolve_project_path(name_or_path: str) -> Optional[Path]:
    """Match registered project name or validate an absolute/home path."""
    raw = (name_or_path or "").strip()
    if not raw:
        return None

    proj = get_project(raw)
    if proj:
        p = Path(proj["path"]).expanduser().resolve()
        return p if p.is_dir() else None

    if "/" in raw or "\\" in raw or raw.startswith("~"):
        p = _normalize_path(raw)
        if p.is_dir() and _path_allowed(p):
            return p
        return None

    # Fuzzy: substring match on registered names
    key = raw.lower()
    for proj in list_projects():
        pname = proj.get("name", "").lower()
        if key in pname or pname in key:
            p = Path(proj["path"]).expanduser().resolve()
            if p.is_dir():
                return p
    return None


def add_project(name: str, path: str, *, branch: str = "main", remote: str = "origin") -> dict[str, Any]:
    name = name.strip()
    if not _PROJECT_NAME_RE.match(name):
        return {"success": False, "error": "Invalid project name (use letters, numbers, -, _, .)"}

    p = _normalize_path(path)
    if not p.is_dir():
        return {"success": False, "error": f"Folder not found: {p}"}
    if not _path_allowed(p):
        return {"success": False, "error": "Project path must be inside your home folder"}

    data = _load_json(PROJECTS_FILE)
    projects: list[dict[str, Any]] = list(data.get("projects") or [])
    entry = {
        "name": name,
        "path": str(p),
        "branch": (branch or "main").strip() or "main",
        "remote": (remote or "origin").strip() or "origin",
    }
    projects = [x for x in projects if x.get("name", "").lower() != name.lower()]
    projects.append(entry)
    data["projects"] = projects
    _save_json(PROJECTS_FILE, data)
    return {"success": True, "project": entry}


def remove_project(name: str) -> dict[str, Any]:
    data = _load_json(PROJECTS_FILE)
    before = list(data.get("projects") or [])
    after = [x for x in before if x.get("name", "").lower() != name.strip().lower()]
    if len(after) == len(before):
        return {"success": False, "error": "Project not found"}
    data["projects"] = after
    _save_json(PROJECTS_FILE, data)
    return {"success": True}


def ssh_public_key_path() -> Path:
    return DEFAULT_SSH_PUBLIC


def ssh_private_key_path() -> Path:
    return DEFAULT_SSH_PRIVATE


def ssh_key_exists() -> bool:
    return DEFAULT_SSH_PRIVATE.is_file() and DEFAULT_SSH_PUBLIC.is_file()


def read_public_key() -> Optional[str]:
    if not DEFAULT_SSH_PUBLIC.is_file():
        return None
    try:
        return DEFAULT_SSH_PUBLIC.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def generate_ssh_key(*, overwrite: bool = False) -> dict[str, Any]:
    ensure_aha_dir()
    SSH_DIR.mkdir(parents=True, exist_ok=True)

    if ssh_key_exists() and not overwrite:
        return {
            "success": True,
            "already_exists": True,
            "public_key": read_public_key(),
            "public_key_path": str(DEFAULT_SSH_PUBLIC),
            "message": "SSH key already exists. Paste the public key into GitHub/GitLab → SSH keys.",
        }

    if ssh_key_exists() and overwrite:
        for f in (DEFAULT_SSH_PRIVATE, DEFAULT_SSH_PUBLIC):
            try:
                f.unlink()
            except OSError:
                pass

    cmd = [
        "ssh-keygen",
        "-t", "ed25519",
        "-f", str(DEFAULT_SSH_PRIVATE),
        "-N", "",
        "-C", "aha@dailyassist",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return {"success": False, "error": "ssh-keygen not found. Install OpenSSH for your OS."}
    except subprocess.CalledProcessError as exc:
        return {"success": False, "error": (exc.stderr or exc.stdout or str(exc)).strip()}

    try:
        os.chmod(DEFAULT_SSH_PRIVATE, 0o600)
    except OSError:
        pass

    pub = read_public_key()
    return {
        "success": True,
        "already_exists": False,
        "public_key": pub,
        "public_key_path": str(DEFAULT_SSH_PUBLIC),
        "message": "SSH key created. Add the public key to GitHub/GitLab → Settings → SSH keys.",
    }


def find_git() -> Optional[str]:
    return shutil.which("git")


def git_current_branch(repo: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return out.stdout.strip() or "main"
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return "main"


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()
