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
    try:
        doc_ref = db.collection(_LICENSES_COLLECTION).document(body.license_key)
        snapshot = await doc_ref.get()
    except Exception as exc:
        logger.exception("Firestore error during license validation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="License database temporarily unavailable.",
        )

    if not snapshot.exists:
        return ValidateLicenseResponse(
            is_valid=False,
            reason="License key not found.",
            plan="",
        )

    data: dict = snapshot.to_dict() or {}
    lic_status: str = data.get("status", "unknown")
    plan: str = data.get("plan", "")

    if lic_status == "active":
        return ValidateLicenseResponse(
            is_valid=True,
            reason="License is active.",
            plan=plan,
        )

    reason_map = {
        "halted":    "Subscription payment failed. Please update your payment method.",
        "cancelled": "Subscription has been cancelled.",
        "expired":   "License has expired. Please renew your subscription.",
    }
    reason = reason_map.get(lic_status, f"License status is '{lic_status}'.")
    return ValidateLicenseResponse(is_valid=False, reason=reason, plan=plan)
