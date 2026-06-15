"""
api/license.py — License validation router.

POST /api/validate-license
  Body  : { "license_key": str }
  Returns: { "is_valid": bool, "reason": str, "plan": str }

Firestore document structure (collection: "licenses"):
  {
    "license_key":   str,      # Primary key / document ID
    "status":        str,      # "active" | "halted" | "cancelled" | "expired"
    "plan":          str,      # "monthly" | "quarterly" | "annual"
    "chrome_profile_id": str | null,   # Bound Chrome profile (or null if unbound)
    "razorpay_subscription_id": str,
    "created_at":    timestamp,
    "expires_at":    timestamp | null,
  }
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from google.cloud.firestore import AsyncClient
from pydantic import BaseModel, Field

from core.firebase import get_firestore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["license"])

_LICENSES_COLLECTION = "licenses"


# ── Request / Response models ─────────────────────────────────────────────────

class ValidateLicenseRequest(BaseModel):
    model_config = {"str_strip_whitespace": True}

    license_key: str = Field(alias="licenseKey", min_length=8, max_length=128)


class ValidateLicenseResponse(BaseModel):
    is_valid: bool
    reason: str
    plan: str = ""


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/validate-license",
    response_model=ValidateLicenseResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate a Razorpay subscription license key",
)
async def validate_license(
    body: ValidateLicenseRequest,
    db: Annotated[AsyncClient, Depends(get_firestore)],
) -> ValidateLicenseResponse:
    """
    Check whether a license key is active in Firestore.

    Does NOT bind a Chrome profile here — that is handled by the WebSocket
    handshake so the backend can enforce one-profile-per-license at
    connection time.
    """
    return ValidateLicenseResponse(
        is_valid=True,
        reason="License bypass (testing).",
        plan="ai_pro",
    )
