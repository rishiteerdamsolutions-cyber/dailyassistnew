"""
Razorpay billing — create orders, verify payments, issue licenses.

Environment:
    RAZORPAY_KEY_ID       Public key (rzp_test_... or rzp_live_...)
    RAZORPAY_KEY_SECRET   Secret key (server only)
    RAZORPAY_WEBHOOK_SECRET  Optional, for /api/billing/webhook
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from aha.supabase_client import get_supabase_admin, upsert_user

# Plan catalog (amounts in paise — 100 paise = ₹1)
PLANS: dict[str, dict[str, Any]] = {
    "core_monthly": {
        "label": "AHA Core — Monthly",
        "plan": "core",
        "amount_paise": int(os.environ.get("AHA_PLAN_CORE_MONTHLY_PAISE", "99900")),
        "currency": "INR",
        "duration_days": 30,
    },
    "core_yearly": {
        "label": "AHA Core — Yearly",
        "plan": "core",
        "amount_paise": int(os.environ.get("AHA_PLAN_CORE_YEARLY_PAISE", "999900")),
        "currency": "INR",
        "duration_days": 365,
    },
}


def razorpay_key_id() -> str:
    return os.environ.get("RAZORPAY_KEY_ID", "").strip().strip('"').strip("'")


def razorpay_key_secret() -> str:
    return os.environ.get("RAZORPAY_KEY_SECRET", "").strip().strip('"').strip("'")


def razorpay_configured() -> bool:
    return bool(razorpay_key_id() and razorpay_key_secret())


def razorpay_env_diagnostics() -> dict:
    """Safe Razorpay deploy check — never returns secrets."""
    key = razorpay_key_id()
    mode = "unknown"
    if key.startswith("rzp_test_"):
        mode = "test"
    elif key.startswith("rzp_live_"):
        mode = "live"
    return {
        "configured": razorpay_configured(),
        "mode": mode,
        "key_id_suffix": key[-6:] if len(key) >= 6 else "",
        "secret_length": len(razorpay_key_secret()),
    }


def _client():
    if not razorpay_configured():
        raise RuntimeError(
            "Razorpay is not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env"
        )
    import razorpay

    return razorpay.Client(auth=(razorpay_key_id(), razorpay_key_secret()))


def public_billing_config() -> dict:
    """Safe for the browser — key id and plan labels only."""
    return {
        "razorpay_configured": razorpay_configured(),
        "key_id": razorpay_key_id() or None,
        "plans": {
            pid: {
                "label": p["label"],
                "amount_paise": p["amount_paise"],
                "currency": p["currency"],
                "amount_display": f"₹{p['amount_paise'] / 100:.0f}",
            }
            for pid, p in PLANS.items()
        },
    }


def generate_license_key() -> str:
    """Format: AHA-XXXX-XXXX-XXXX (18 characters)."""
    parts = [secrets.token_hex(2).upper()[:4] for _ in range(3)]
    return "AHA-" + "-".join(parts)


def create_order(uid: str, email: str, plan_id: str) -> dict:
    if plan_id not in PLANS:
        raise ValueError(f"Unknown plan: {plan_id}")

    plan = PLANS[plan_id]
    try:
        upsert_user(uid, email)
    except Exception:
        pass  # checkout can proceed if Supabase is briefly unavailable

    client = _client()
    receipt = f"aha_{uid[:8]}_{secrets.token_hex(4)}"
    order = client.order.create(
        {
            "amount": plan["amount_paise"],
            "currency": plan["currency"],
            "receipt": receipt,
            "notes": {"uid": uid, "plan_id": plan_id, "plan": plan["plan"]},
        }
    )

    admin = get_supabase_admin()
    try:
        admin.table("aha_payments").insert(
            {
                "uid": uid,
                "razorpay_order_id": order["id"],
                "amount_paise": plan["amount_paise"],
                "currency": plan["currency"],
                "plan": plan["plan"],
                "status": "created",
            }
        ).execute()
    except Exception:
        pass  # table may not exist until migration runs

    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "key_id": razorpay_key_id(),
        "plan_id": plan_id,
        "plan_label": plan["label"],
    }


def _expires_at(plan_id: str) -> str | None:
    days = PLANS.get(plan_id, {}).get("duration_days")
    if not days:
        return None
    exp = datetime.now(timezone.utc) + timedelta(days=int(days))
    return exp.isoformat()


def fulfill_payment(
    uid: str,
    order_id: str,
    payment_id: str,
    plan_id: str | None = None,
) -> dict:
    """Mark payment paid and issue a license for the user."""
    license_key = generate_license_key()
    plan_row = PLANS.get(plan_id or "core_monthly", PLANS["core_monthly"])
    plan_name = plan_row["plan"]
    expires = _expires_at(plan_id or "core_monthly")

    admin = get_supabase_admin()
    try:
        admin.table("aha_payments").update(
            {
                "razorpay_payment_id": payment_id,
                "status": "paid",
                "license_key": license_key,
                "paid_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("razorpay_order_id", order_id).execute()
    except Exception:
        pass

    admin.table("aha_licenses").upsert(
        {
            "uid": uid,
            "license_key": license_key,
            "plan": plan_name,
            "is_active": True,
            "expires_at": expires,
        },
        on_conflict="license_key",
    ).execute()

    admin.table("aha_users").update({"plan": plan_name}).eq("uid", uid).execute()

    from aha.license import save_license_from_cloud

    save_license_from_cloud(license_key, plan_name, expires)

    return {
        "valid": True,
        "license_key": license_key,
        "plan": plan_name,
        "expires": expires,
    }


def verify_checkout_signature(
    order_id: str,
    payment_id: str,
    signature: str,
) -> dict:
    client = _client()
    client.utility.verify_payment_signature(
        {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        }
    )
    admin = get_supabase_admin()
    row = (
        admin.table("aha_payments")
        .select("uid, plan, status")
        .eq("razorpay_order_id", order_id)
        .limit(1)
        .execute()
    )
    if not row.data:
        raise ValueError("Order not found in database.")
    rec = row.data[0]
    if rec.get("status") == "paid":
        lic = (
            admin.table("aha_licenses")
            .select("license_key, plan, expires_at")
            .eq("uid", rec["uid"])
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if lic.data:
            return {
                "valid": True,
                "license_key": lic.data[0]["license_key"],
                "plan": lic.data[0]["plan"],
                "expires": lic.data[0].get("expires_at"),
            }

    order = client.order.fetch(order_id)
    notes = order.get("notes") or {}
    uid = notes.get("uid") or rec["uid"]
    plan_id = notes.get("plan_id", "core_monthly")
    return fulfill_payment(uid, order_id, payment_id, plan_id)


def handle_razorpay_webhook(body: bytes, signature: str) -> dict:
    """Process Razorpay webhook events (optional RAZORPAY_WEBHOOK_SECRET)."""
    import json

    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "").strip()
    if secret:
        import hmac
        import hashlib

        expected = hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()
        if not signature or not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid webhook signature")

    payload = json.loads(body.decode("utf-8"))
    event = payload.get("event", "")
    if event != "payment.captured":
        return {"status": "ignored", "event": event}

    ent = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = ent.get("order_id")
    payment_id = ent.get("id")
    notes = ent.get("notes") or {}
    uid = notes.get("uid")
    plan_id = notes.get("plan_id", "core_monthly")
    if not order_id or not payment_id or not uid:
        raise ValueError("Webhook missing order_id, payment_id, or uid")

    return {"status": "ok", **fulfill_payment(uid, order_id, payment_id, plan_id)}
