"""Admin analytics and customer listings (service-role Supabase only)."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from aha.subscription import license_row_is_active
from aha.supabase_client import get_supabase_admin


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_all_users() -> list[dict]:
    admin = get_supabase_admin()
    try:
        result = admin.table("aha_users").select("*").order("created_at", desc=True).execute()
        return result.data or []
    except Exception:
        return []


def fetch_payments(limit: int = 500) -> list[dict]:
    admin = get_supabase_admin()
    try:
        result = (
            admin.table("aha_payments")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def fetch_licenses() -> list[dict]:
    admin = get_supabase_admin()
    try:
        result = admin.table("aha_licenses").select("*").execute()
        return result.data or []
    except Exception:
        return []


def get_analytics() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    users = fetch_all_users()
    payments = fetch_payments()
    licenses = fetch_licenses()

    plan_counts: Counter[str] = Counter()
    signups_7d = 0
    signups_30d = 0
    for u in users:
        plan_counts[u.get("plan") or "free"] += 1
        created = _parse_ts(u.get("created_at"))
        if created:
            if created >= week_ago:
                signups_7d += 1
            if created >= month_ago:
                signups_30d += 1

    paid_rows = [p for p in payments if p.get("status") == "paid"]
    revenue_paise = sum(int(p.get("amount_paise") or 0) for p in paid_rows)
    coupon_paid = sum(
        1 for p in paid_rows if str(p.get("razorpay_payment_id", "")).startswith("coupon_")
    )

    active_licenses = sum(1 for lic in licenses if license_row_is_active(lic))

    return {
        "totals": {
            "users": len(users),
            "active_licenses": active_licenses,
            "paid_orders": len(paid_rows),
            "revenue_paise": revenue_paise,
            "revenue_display": f"₹{revenue_paise / 100:,.2f}",
            "coupon_checkouts": coupon_paid,
            "pending_orders": sum(1 for p in payments if p.get("status") == "created"),
        },
        "signups": {"last_7_days": signups_7d, "last_30_days": signups_30d},
        "plans": dict(plan_counts),
        "generated_at": now.isoformat(),
    }


def list_customers(limit: int = 200, offset: int = 0) -> dict[str, Any]:
    users = fetch_all_users()
    payments = fetch_payments()
    licenses = fetch_licenses()

    pay_by_uid: dict[str, list[dict]] = {}
    for p in payments:
        pay_by_uid.setdefault(p.get("uid", ""), []).append(p)

    lic_by_uid: dict[str, dict] = {}
    for lic in licenses:
        uid = lic.get("uid", "")
        prev = lic_by_uid.get(uid)
        if not prev or (lic.get("activated_at") or "") > (prev.get("activated_at") or ""):
            lic_by_uid[uid] = lic

    rows: list[dict] = []
    for u in users:
        uid = u.get("uid", "")
        lic = lic_by_uid.get(uid)
        user_pays = pay_by_uid.get(uid, [])
        last_paid = next((p for p in user_pays if p.get("status") == "paid"), None)
        rows.append(
            {
                "uid": uid,
                "email": u.get("email"),
                "display_name": u.get("display_name"),
                "plan": u.get("plan"),
                "created_at": u.get("created_at"),
                "license_active": license_row_is_active(lic) if lic else False,
                "license_key": (lic or {}).get("license_key"),
                "license_expires": (lic or {}).get("expires_at"),
                "last_payment_status": (last_paid or {}).get("status"),
                "last_payment_at": (last_paid or {}).get("paid_at"),
                "last_amount_paise": (last_paid or {}).get("amount_paise"),
            }
        )

    total = len(rows)
    page = rows[offset : offset + limit]
    return {"total": total, "offset": offset, "limit": limit, "customers": page}
