"""Tests for Tier-1 local precision (parser, registry, env scaffold)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aha.local_registry import add_project, list_projects, remove_project, resolve_project_path
from bol.modules.m9_local.parser import detect_local_task
from bol.modules.m9_native.runner import run_native_action
from bol.modules.m9_router.router import Tier1Domain, detect_tier1


def test_detect_git_push_intent():
    task = detect_local_task("push dailyassist to git")
    assert task is not None
    assert task.flow_id == "git_push"


def test_detect_env_local_intent():
    task = detect_local_task("create .env.local for my project")
    assert task is not None
    assert task.flow_id == "create_env_local"


def test_detect_bluetooth_intent():
    task = detect_local_task('connect to "Noise Buds" via bluetooth')
    assert task is not None
    assert task.flow_id == "bluetooth_connect"
    assert "Noise Buds" in task.params.get("device_name", "")


def test_detect_ssh_generate():
    task = detect_local_task("generate ssh key for github")
    assert task is not None
    assert task.flow_id == "ssh_setup"


def test_tier1_router_local_before_social():
    match = detect_tier1("create .env.local")
    assert match is not None
    assert match.domain == Tier1Domain.LOCAL


def test_tier1_router_social_still_works():
    match = detect_tier1("post this photo on instagram")
    assert match is not None
    assert match.domain == Tier1Domain.SOCIAL
    assert match.flow_id == "instagram_post"


def test_project_registry(tmp_path, monkeypatch):
    projects_file = tmp_path / "projects.json"
    monkeypatch.setattr("aha.local_registry.PROJECTS_FILE", projects_file)
    monkeypatch.setattr("aha.local_registry._path_allowed", lambda _p: True)

    repo = tmp_path / "myapp"
    repo.mkdir()
    (repo / ".git").mkdir()

    result = add_project("myapp", str(repo))
    assert result["success"] is True
    assert len(list_projects()) == 1

    resolved = resolve_project_path("myapp")
    assert resolved == repo.resolve()

    remove_project("myapp")
    assert list_projects() == []


def test_create_env_local_from_example(tmp_path):
    repo = tmp_path / "proj"
    repo.mkdir()
    (repo / ".env.example").write_text("API_KEY=\nSECRET=\n", encoding="utf-8")

    result = run_native_action(
        "create_env_local",
        {"repo_path": str(repo), "overwrite": False},
    )
    assert result["success"] is True
    target = repo / ".env.local"
    assert target.is_file()
    text = target.read_text(encoding="utf-8")
    assert "API_KEY=" in text
    assert "SECRET=" in text


def test_find_connect_same_row_only():
    from bol.modules.m9_local.bluetooth_vision import (
        TextBox,
        _find_connect_on_device_row,
        _find_device_box,
    )

    screen_w, screen_h = 1200, 900
    device = TextBox(x=500, y=400, w=120, h=24, text="Noise Buds", conf=90)
    boxes = [
        TextBox(x=500, y=120, w=200, h=30, text="Bluetooth", conf=95),  # page title — skip
        device,
        TextBox(x=100, y=80, w=60, h=20, text="Connect", conf=88),
        TextBox(x=700, y=180, w=70, h=22, text="Connect", conf=88),
        TextBox(x=680, y=402, w=72, h=22, text="Connect", conf=92),
    ]
    found = _find_device_box(boxes, "Noise Buds", screen_w, screen_h)
    assert found is not None
    assert found.text == "Noise Buds"
    connect = _find_connect_on_device_row(boxes, found, screen_w, screen_h)
    assert connect is not None
    assert connect.x == 680


def test_device_name_fuzzy_match():
    from bol.modules.m9_local.bluetooth_vision import _names_match

    assert _names_match("Noise Buds", "Noise Buds VS104")
    assert _names_match("noise buds", "Noise Buds VS104")
    assert not _names_match("AirPods", "Noise Buds VS104")


def test_create_env_local_refuses_overwrite(tmp_path):
    repo = tmp_path / "proj2"
    repo.mkdir()
    (repo / ".env.local").write_text("OLD=1\n", encoding="utf-8")

    result = run_native_action(
        "create_env_local",
        {"repo_path": str(repo), "overwrite": False},
    )
    assert result["success"] is False
    assert "already exists" in result["message"].lower()
