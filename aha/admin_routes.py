"""Admin API — analytics, customers, coupons (protected)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from aha.admin_auth import require_admin
from aha.admin_service import get_analytics, list_customers
from aha.coupons import list_coupons, upsert_coupon, validate_coupon

router = APIRouter(prefix="/api/admin", tags=["admin"])


class CreateCouponBody(BaseModel):
    code: str = Field(..., min_length=3, max_length=32)
    discount_percent: int = Field(..., ge=1, le=100)
    plan_id: str | None = None
    max_uses: int | None = None
    note: str | None = None
    is_active: bool = True


class ToggleCouponBody(BaseModel):
    code: str
    is_active: bool


@router.get("/analytics")
async def admin_analytics(_admin: dict = Depends(require_admin)) -> dict:
    return get_analytics()


@router.get("/customers")
async def admin_customers(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_admin),
) -> dict:
    return list_customers(limit=limit, offset=offset)


@router.get("/coupons")
async def admin_coupons(_admin: dict = Depends(require_admin)) -> dict:
    return {"coupons": list_coupons()}


@router.post("/coupons")
async def admin_create_coupon(
    body: CreateCouponBody,
    _admin: dict = Depends(require_admin),
) -> dict:
    try:
        row = upsert_coupon(
            body.code,
            body.discount_percent,
            plan_id=body.plan_id,
            max_uses=body.max_uses,
            note=body.note,
            is_active=body.is_active,
        )
        return {"status": "ok", "coupon": row}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/coupons/toggle")
async def admin_toggle_coupon(
    body: ToggleCouponBody,
    _admin: dict = Depends(require_admin),
) -> dict:
    from aha.coupons import _normalize_code
    from aha.supabase_client import get_supabase_admin

    admin = get_supabase_admin()
    result = (
        admin.table("aha_coupons")
        .update({"is_active": body.is_active})
        .eq("code", _normalize_code(body.code))
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Coupon not found")
    return {"status": "ok", "coupon": result.data[0]}


@router.get("/coupons/preview")
async def admin_preview_coupon(
    code: str,
    plan_id: str = "core_monthly",
    _admin: dict = Depends(require_admin),
) -> dict:
    try:
        return validate_coupon(code, plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
