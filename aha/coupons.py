"""Promo coupon validation and redemption (server-only, Supabase admin client)."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from aha.billing import PLANS, _expires_at, generate_license_key
from aha.supabase_client import get_supabase_admin, upsert_user


def _normalize_code(code: str) -> str:
    return code.strip().upper()


def _coupon_row(code: str) -> dict | None:
    admin = get_supabase_admin()
    try:
        result = (
            admin.table("aha_coupons")
            .select("*")
            .eq("code", _normalize_code(code))
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


def validate_coupon(code: str, plan_id: str) -> dict[str, Any]:
    """Return discount details or raise ValueError."""
    if plan_id not in PLANS:
        raise ValueError(f"Unknown plan: {plan_id}")

    row = _coupon_row(code)
    if not row:
        raise ValueError("Invalid coupon code.")
    if not row.get("is_active"):
        raise ValueError("This coupon is no longer active.")
    expires = row.get("expires_at")
    if expires:
        exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        if exp_dt < datetime.now(timezone.utc):
            raise ValueError("This coupon has expired.")

    bound_plan = row.get("plan_id")
    if bound_plan and bound_plan != plan_id:
        raise ValueError(f"This coupon only applies to plan: {bound_plan}")

    max_uses = row.get("max_uses")
    uses = int(row.get("uses_count") or 0)
    if max_uses is not None and uses >= int(max_uses):
        raise ValueError("This coupon has reached its usage limit.")

    plan = PLANS[plan_id]
    discount = int(row["discount_percent"])
    amount = int(plan["amount_paise"])
    discount_paise = (amount * discount) // 100
    final_paise = max(0, amount - discount_paise)

    return {
        "code": row["code"],
        "coupon_id": row["id"],
        "discount_percent": discount,
        "original_paise": amount,
        "final_paise": final_paise,
        "free_checkout": final_paise == 0,
        "plan_id": plan_id,
        "plan_label": plan["label"],
    }


def user_already_redeemed(coupon_id: str, uid: str) -> bool:
    admin = get_supabase_admin()
    try:
        result = (
            admin.table("aha_coupon_redemptions")
            .select("id")
            .eq("coupon_id", coupon_id)
            .eq("uid", uid)
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception:
        return False


def redeem_coupon(uid: str, email: str, plan_id: str, coupon_code: str) -> dict[str, Any]:
    """Apply coupon; issue license without Razorpay when final amount is 0."""
    info = validate_coupon(coupon_code, plan_id)
    if user_already_redeemed(info["coupon_id"], uid):
        raise ValueError("You have already used this coupon.")

    if not info["free_checkout"]:
        raise ValueError(
            "Partial discounts are not supported yet. Use a 100% coupon (e.g. COUPON100)."
        )

    upsert_user(uid, email)
    plan = PLANS[plan_id]
    license_key = generate_license_key()
    expires = _expires_at(plan_id)
    order_id = f"coupon_{info['code']}_{secrets.token_hex(6)}"

    admin = get_supabase_admin()
    try:
        admin.table("aha_payments").insert(
            {
                "uid": uid,
                "razorpay_order_id": order_id,
                "razorpay_payment_id": f"coupon_{info['code']}",
                "amount_paise": 0,
                "currency": plan["currency"],
                "plan": plan["plan"],
                "status": "paid",
                "license_key": license_key,
                "paid_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
    except Exception:
        pass

    admin.table("aha_licenses").upsert(
        {
            "uid": uid,
            "license_key": license_key,
            "plan": plan["plan"],
            "is_active": True,
            "expires_at": expires,
        },
        on_conflict="license_key",
    ).execute()

    admin.table("aha_users").update({"plan": plan["plan"]}).eq("uid", uid).execute()

    row = _coupon_row(coupon_code) or {}
    admin.table("aha_coupons").update(
        {"uses_count": int(row.get("uses_count") or 0) + 1}
    ).eq("id", info["coupon_id"]).execute()

    admin.table("aha_coupon_redemptions").insert(
        {
            "coupon_id": info["coupon_id"],
            "uid": uid,
            "plan_id": plan_id,
            "license_key": license_key,
        }
    ).execute()

    from aha.license import save_license_from_cloud

    save_license_from_cloud(license_key, plan["plan"], expires)

    return {
        "valid": True,
        "license_key": license_key,
        "plan": plan["plan"],
        "expires": expires,
        "coupon": info["code"],
        "amount_paise": 0,
    }


def list_coupons() -> list[dict]:
    admin = get_supabase_admin()
    try:
        result = (
            admin.table("aha_coupons")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def upsert_coupon(
    code: str,
    discount_percent: int,
    *,
    plan_id: str | None = None,
    max_uses: int | None = None,
    note: str | None = None,
    is_active: bool = True,
) -> dict:
    admin = get_supabase_admin()
    payload = {
        "code": _normalize_code(code),
        "discount_percent": discount_percent,
        "plan_id": plan_id,
        "max_uses": max_uses,
        "note": note or "",
        "is_active": is_active,
    }
    result = admin.table("aha_coupons").upsert(payload, on_conflict="code").execute()
    return result.data[0] if result.data else payload
