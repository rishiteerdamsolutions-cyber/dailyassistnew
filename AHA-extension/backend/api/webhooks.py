"""
api/webhooks.py — Razorpay webhook router.

POST /api/webhooks/razorpay
  Verifies HMAC-SHA256 signature, then handles:
    subscription.charged   → set license status = "active"
    subscription.halted    → set license status = "halted"
    subscription.cancelled → set license status = "cancelled"

Signature verification per official Razorpay docs:
  expected = HMAC-SHA256(webhook_body_bytes, RAZORPAY_WEBHOOK_SECRET)
  compare  X-Razorpay-Signature header against expected (constant-time)

Firestore update touches only: status, updated_at fields.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from google.cloud.firestore import AsyncClient

from core.firebase import get_firestore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

_LICENSES_COLLECTION = "licenses"


# ── Signature verification ─────────────────────────────────────────────────────

def _verify_razorpay_signature(body: bytes, signature: str) -> bool:
    """
    HMAC-SHA256 verification per Razorpay webhook documentation.

    Uses hmac.compare_digest to prevent timing attacks.
    Returns False (not raises) if the secret is unconfigured — all webhook
    events will then be rejected with 401.
    """
    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
    if not secret:
        logger.error("RAZORPAY_WEBHOOK_SECRET is not configured.")
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


# ── Firestore helpers ─────────────────────────────────────────────────────────

async def _find_license_by_subscription(
    db: AsyncClient,
    subscription_id: str,
) -> tuple[str | None, dict]:
    """
    Locate a license document by razorpay_subscription_id.

    Returns (document_id, data_dict) or (None, {}) if not found.
    """
    query = (
        db.collection(_LICENSES_COLLECTION)
        .where("razorpay_subscription_id", "==", subscription_id)
        .limit(1)
    )
    docs = query.stream()
    async for doc in docs:
        return doc.id, doc.to_dict() or {}
    return None, {}


async def _update_license_status(
    db: AsyncClient,
    doc_id: str,
    new_status: str,
) -> None:
    """Update the status and updated_at fields on a license document."""
    doc_ref = db.collection(_LICENSES_COLLECTION).document(doc_id)
    await doc_ref.update({
        "status": new_status,
        "updated_at": datetime.now(tz=timezone.utc),
    })
    logger.info("License %s → status=%s", doc_id, new_status)


# ── Event handler dispatch ────────────────────────────────────────────────────

_EVENT_TO_STATUS: dict[str, str] = {
    "subscription.charged":   "active",
    "subscription.halted":    "halted",
    "subscription.cancelled": "cancelled",
}


async def _handle_subscription_event(
    db: AsyncClient,
    event: str,
    payload: dict,
) -> None:
    """Process a subscription lifecycle event and update Firestore."""
    new_status = _EVENT_TO_STATUS[event]

    # Razorpay subscription event payload structure:
    # { "payload": { "subscription": { "entity": { "id": "sub_xxx", ... } } } }
    try:
        subscription_id: str = (
            payload["payload"]["subscription"]["entity"]["id"]
        )
    except (KeyError, TypeError) as exc:
        logger.error("Malformed Razorpay payload for event %s: %s", event, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Malformed Razorpay event payload.",
        )

    doc_id, _ = await _find_license_by_subscription(db, subscription_id)
    if doc_id is None:
        # Not necessarily an error — could be a test subscription
        logger.warning(
            "No license found for subscription %s (event: %s)",
            subscription_id, event,
        )
        return

    await _update_license_status(db, doc_id, new_status)


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/razorpay",
    status_code=status.HTTP_200_OK,
    summary="Razorpay webhook receiver",
)
async def razorpay_webhook(
    request: Request,
    db: Annotated[AsyncClient, Depends(get_firestore)],
    x_razorpay_signature: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    """
    Receive and process Razorpay subscription webhook events.

    Security: Rejects any request whose X-Razorpay-Signature header does
    not match the HMAC-SHA256 of the raw request body with the configured
    webhook secret.
    """
    # ── 1. Read raw body BEFORE parsing — signature is over the raw bytes
    body: bytes = await request.body()

    # ── 2. Verify signature
    if not x_razorpay_signature:
        logger.warning("Razorpay webhook received with no signature header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Razorpay-Signature header.",
        )

    if not _verify_razorpay_signature(body, x_razorpay_signature):
        logger.warning("Razorpay webhook signature mismatch — request rejected.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature.",
        )

    # ── 3. Parse JSON payload
    try:
        import json
        payload: dict = json.loads(body)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body is not valid JSON.",
        )

    event: str = payload.get("event", "")
    logger.info("Razorpay webhook event received: %s", event)

    # ── 4. Handle known subscription lifecycle events
    if event in _EVENT_TO_STATUS:
        try:
            await _handle_subscription_event(db, event, payload)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error processing webhook event %s: %s", event, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal error processing webhook.",
            )
    else:
        # Unknown / unhandled events — acknowledge silently (Razorpay retries on non-200)
        logger.debug("Unhandled Razorpay event '%s' — acknowledged.", event)

    return JSONResponse(content={"status": "ok"})
