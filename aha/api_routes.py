"""
AHA Companion App – FastAPI routes for license & API-key management.

Usage in the main server::

    from aha.api_routes import router as api_router
    app.include_router(api_router)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from aha.firebase_auth import get_current_user
from aha.license import (
    activate_license,
    check_license_status,
    delete_api_key,
    get_api_keys,
    set_api_key,
    sync_license_for_uid,
    validate_license,
)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api", tags=["license", "config"])

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class LicenseKeyRequest(BaseModel):
    license_key: str = Field(..., description="License key to validate/activate")


class FirebaseTokenBody(BaseModel):
    id_token: str = Field(..., description="Firebase ID token")


class CreateOrderBody(BaseModel):
    plan_id: str = Field(default="core_monthly", description="Plan id from /api/billing/config")


class VerifyPaymentBody(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class SetApiKeyRequest(BaseModel):
    provider: str = Field(..., description="Provider name (e.g. 'google', 'openai')")
    api_key: str = Field(..., description="Raw API key value")


class DeleteApiKeyRequest(BaseModel):
    provider: str = Field(..., description="Provider whose key should be removed")


# ---------------------------------------------------------------------------
# License endpoints
# ---------------------------------------------------------------------------


@router.post("/license/validate")
async def license_validate(body: LicenseKeyRequest) -> dict:
    """Validate a license key without activating it."""
    return validate_license(body.license_key)


@router.post("/license/activate")
async def license_activate(body: LicenseKeyRequest) -> dict:
    """Validate *and* persist a license key."""
    return activate_license(body.license_key)


@router.get("/license/status")
async def license_status() -> dict:
    """Return the current license status (cached or re-validated)."""
    return check_license_status()


@router.post("/license/sync")
async def license_sync_cloud(body: FirebaseTokenBody) -> dict:
    """After Firebase sign-in, pull paid subscription from Supabase to this device."""
    from aha.firebase_auth import verify_firebase_token

    try:
        claims = verify_firebase_token(body.id_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return sync_license_for_uid(claims["uid"])


# ---------------------------------------------------------------------------
# Billing (Razorpay)
# ---------------------------------------------------------------------------


@router.get("/billing/config")
async def billing_config() -> dict:
    """Public plan catalog + Razorpay key id (no secret)."""
    from aha.billing import public_billing_config

    return public_billing_config()


@router.post("/billing/create_order")
async def billing_create_order(
    body: CreateOrderBody,
    user: dict = Depends(get_current_user),
) -> dict:
    from aha.billing import create_order

    try:
        return create_order(
            user["uid"],
            user.get("email", ""),
            body.plan_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/billing/verify")
async def billing_verify_payment(
    body: VerifyPaymentBody,
    user: dict = Depends(get_current_user),
) -> dict:
    from aha.billing import verify_checkout_signature

    try:
        result = verify_checkout_signature(
            body.razorpay_order_id,
            body.razorpay_payment_id,
            body.razorpay_signature,
        )
        return {"status": "ok", **result}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/billing/webhook")
async def billing_webhook(request: Request) -> dict:
    """Razorpay server webhook (payment.captured)."""
    from aha.billing import handle_razorpay_webhook

    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    try:
        return handle_razorpay_webhook(body, signature)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# API-key (BYOK) endpoints
# ---------------------------------------------------------------------------


@router.post("/config/set_api_key")
async def config_set_api_key(body: SetApiKeyRequest) -> dict:
    """Store an API key for *provider*."""
    result = set_api_key(body.provider, body.api_key)
    if result.get("success"):
        from aha.agent_runtime import reset_agent

        reset_agent()
    return result


@router.get("/config/get_api_keys")
async def config_get_api_keys() -> dict:
    """Return all stored API keys with values masked."""
    return get_api_keys()


@router.delete("/config/delete_api_key")
async def config_delete_api_key(body: DeleteApiKeyRequest) -> dict:
    """Remove the stored API key for *provider*."""
    result = delete_api_key(body.provider)
    if result.get("success"):
        from aha.agent_runtime import reset_agent

        reset_agent()
    return result
