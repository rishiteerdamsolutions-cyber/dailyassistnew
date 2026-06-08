"""Cloud API routes — usage limits + Gemini proxy."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from vercel_backend.cloud_auth import validate_cloud_caller
from vercel_backend.gemini_proxy import proxy_generate_content
from vercel_backend.usage import LIMIT_MESSAGE, check_available, record_completed_post

router = APIRouter(prefix="/api", tags=["cloud"])


class UsageCheckRequest(BaseModel):
    license_key: str = Field(..., min_length=8)
    platform: str = Field(..., min_length=2)
    task_type: str = Field(default="social")
    firebase_id_token: str | None = Field(default=None)


class GeminiProxyRequest(BaseModel):
    license_key: str = Field(..., min_length=8)
    byok_key: str | None = Field(default=None, description="Option 1 — user's Gemini key")
    firebase_id_token: str | None = Field(default=None)
    model: str = Field(..., min_length=3)
    contents: list[dict[str, Any]]
    system_instruction: str | None = None
    generation_config: dict[str, Any] | None = None


class UsageConfirmRequest(BaseModel):
    license_key: str = Field(..., min_length=8)
    platform: str = Field(..., min_length=2)
    task_type: str = Field(default="social")
    task_id: str | None = None
    firebase_id_token: str | None = Field(default=None)


@router.post("/usage/check")
def usage_check(body: UsageCheckRequest) -> dict:
    """Read-only: is today's slot still available? (no reservation)"""
    try:
        validate_cloud_caller(body.license_key, body.firebase_id_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        return check_available(
            body.license_key,
            body.platform,
            task_type=body.task_type,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/usage/confirm")
def usage_confirm(body: UsageConfirmRequest) -> dict:
    """Record a verified completed post (after final-button screenshot check)."""
    try:
        validate_cloud_caller(body.license_key, body.firebase_id_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        return record_completed_post(
            body.license_key,
            body.platform,
            task_type=body.task_type,
            task_id=body.task_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/usage/message")
def usage_limit_message() -> dict:
    return {"message": LIMIT_MESSAGE}


@router.post("/proxy/gemini/generate")
def gemini_proxy_generate(body: GeminiProxyRequest) -> dict:
    """Proxy Gemini generateContent — BYOK pass-through or license + master key."""
    try:
        return proxy_generate_content(
            license_key=body.license_key,
            byok_key=body.byok_key,
            firebase_id_token=body.firebase_id_token,
            model=body.model,
            contents=body.contents,
            system_instruction=body.system_instruction,
            generation_config=body.generation_config,
        )
    except ValueError as exc:
        msg = str(exc)
        status = 429 if "comeback after" in msg.lower() or "take some rest" in msg.lower() else 400
        raise HTTPException(status_code=status, detail=msg) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
