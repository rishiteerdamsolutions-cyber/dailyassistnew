"""
api/payments.py — Razorpay order creation and payment verification.

Endpoints
---------
POST /api/create-order
    Creates a Razorpay order and returns the order_id to the frontend.
    The frontend passes this to the Razorpay Checkout SDK.

POST /api/verify-payment
    Verifies the Razorpay HMAC-SHA256 payment signature.
    On success, generates a license key and writes it to Firestore.
    Returns the license key to the success page.
"""

import hashlib
import hmac
import os
import secrets
import string
import time

import razorpay
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.firebase import get_firestore

router = APIRouter()

# ── Razorpay client (initialised lazily so tests can import without env vars)
def _get_razorpay_client() -> razorpay.Client:
    key_id     = os.environ["RAZORPAY_KEY_ID"]
    key_secret = os.environ["RAZORPAY_KEY_SECRET"]
    return razorpay.Client(auth=(key_id, key_secret))


# ── Pydantic models ────────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    amount:   int    # paise (₹3000 = 300000)
    currency: str = "INR"


class VerifyPaymentRequest(BaseModel):
    payment_id: str
    order_id:   str
    signature:  str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _generate_license_key() -> str:
    """Generate a cryptographically random AHA-XXXX-XXXX-XXXX license key."""
    alphabet = string.ascii_uppercase + string.digits
    segments = [
        "".join(secrets.choice(alphabet) for _ in range(4))
        for _ in range(4)
    ]
    return "AHA-" + "-".join(segments)


def _verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """
    Razorpay signature verification.
    Expected message: "{order_id}|{payment_id}"
    Expected digest:  HMAC-SHA256 with key_secret, hex-encoded.
    Uses hmac.compare_digest for constant-time comparison.
    """
    key_secret = os.environ["RAZORPAY_KEY_SECRET"].encode("utf-8")
    message    = f"{order_id}|{payment_id}".encode("utf-8")
    expected   = hmac.new(key_secret, message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/api/create-order")
async def create_order(body: CreateOrderRequest):
    """
    Create a Razorpay order.  Returns order_id + amount + currency.
    The frontend passes these to Razorpay.Checkout.open().
    """
    client = _get_razorpay_client()

    try:
        order = client.order.create({
            "amount":   body.amount,
            "currency": body.currency,
            "receipt":  f"aha_{int(time.time())}",
            "notes": {
                "product": "AHA AI Pro Monthly Subscription"
            }
        })
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Razorpay order creation failed: {exc}") from exc

    return {
        "order_id": order["id"],
        "amount":   order["amount"],
        "currency": order["currency"]
    }


@router.post("/api/verify-payment")
async def verify_payment(body: VerifyPaymentRequest):
    """
    1. Verify the Razorpay payment signature.
    2. Generate a license key.
    3. Store the license in Firestore under 'licenses/{license_key}'.
    4. Return the license key to the success page.
    """
    # Step 1 — signature check
    if not _verify_razorpay_signature(body.order_id, body.payment_id, body.signature):
        raise HTTPException(status_code=400, detail="Payment signature verification failed.")

    # Step 2 — generate license key
    license_key = _generate_license_key()

    # Step 3 — persist to Firestore
    try:
        db = await get_firestore()
        await db.collection("licenses").document(license_key).set({
            "license_key":  license_key,
            "payment_id":   body.payment_id,
            "order_id":     body.order_id,
            "plan":         "ai_pro",
            "status":       "active",
            "created_at":   int(time.time()),
            "chrome_profile_id": None,   # set on first extension connect
        })
    except Exception as exc:
        # Do NOT return a 500 — the payment already went through.
        # Log the error and still return the license key; manual recovery possible.
        import logging
        logging.error("Firestore write failed for license %s: %s", license_key, exc)

    # Step 4 — return license key
    return {"license_key": license_key}
