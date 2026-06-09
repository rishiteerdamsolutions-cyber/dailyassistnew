"""
AHA Companion App – FastAPI routes for license & API-key management.

Usage in the main server::

    from aha.api_routes import router as api_router
    app.include_router(api_router)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
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


class RedeemCouponBody(BaseModel):
    coupon_code: str = Field(..., description="Promo code, e.g. COUPON100")
    plan_id: str = Field(default="core_monthly")


class SetApiKeyRequest(BaseModel):
    provider: str = Field(..., description="Provider name (e.g. 'google', 'openai')")
    api_key: str = Field(..., description="Raw API key value")


class DeleteApiKeyRequest(BaseModel):
    provider: str = Field(..., description="Provider whose key should be removed")


class AddProjectRequest(BaseModel):
    name: str = Field(..., description="Short project name, e.g. dailyassist")
    path: str = Field(..., description="Absolute or ~ path to project folder")
    branch: str = Field(default="main", description="Default git branch")
    remote: str = Field(default="origin", description="Git remote name")


class RemoveProjectRequest(BaseModel):
    name: str = Field(..., description="Registered project name to remove")


class GenerateSshKeyRequest(BaseModel):
    overwrite: bool = Field(default=False, description="Replace existing AHA SSH key")


# ---------------------------------------------------------------------------
# License endpoints
# ---------------------------------------------------------------------------


@router.post("/license/validate")
async def license_validate(body: LicenseKeyRequest) -> dict:
    """Validate a license key without activating it."""
    return validate_license(body.license_key)


def _use_cloud_license_api() -> bool:
    from aha.supabase_client import SUPABASE_SERVICE_KEY, SUPABASE_URL

    return not (SUPABASE_URL and SUPABASE_SERVICE_KEY)


@router.post("/license/activate")
async def license_activate(body: LicenseKeyRequest) -> dict:
    """Validate *and* persist a license key."""
    if _use_cloud_license_api():
        from aha.cloud_client import cloud_license_activate
        from aha.license import save_license

        try:
            result = cloud_license_activate(body.license_key)
            if result.get("valid"):
                save_license(
                    {
                        **result,
                        "license_key": body.license_key,
                        "source": "cloud",
                    }
                )
            return result
        except RuntimeError as exc:
            return {"valid": False, "reason": "sync_failed", "message": str(exc)}
    return activate_license(body.license_key)


class OpenSettingsBody(BaseModel):
    pane: str = Field(..., description="accessibility | screen")


@router.post("/system/open-settings")
async def system_open_settings(body: OpenSettingsBody) -> dict:
    """Open macOS Privacy settings (pywebview blocks window.open for x-apple:// URLs)."""
    from aha.system_settings import open_privacy_pane

    pane = (body.pane or "").strip().lower()
    if open_privacy_pane(pane):
        return {"ok": True, "pane": pane}
    return {"ok": False, "pane": pane, "message": "Could not open System Settings on this OS."}


@router.get("/auth/check")
async def auth_check() -> dict:
    """Poll after system-browser sign-in from the desktop companion."""
    from aha.firebase_session import load_firebase_id_token

    token = load_firebase_id_token()
    if not token:
        return {"authenticated": False, "license_valid": False}
    status = check_license_status()
    return {
        "authenticated": True,
        "license_valid": bool(status.get("valid")),
        "license": status,
    }


@router.get("/license/status")
async def license_status() -> dict:
    """Return the current license status (cached or re-validated)."""
    try:
        return check_license_status()
    except Exception as exc:
        return {"valid": False, "reason": "license_check_failed", "message": str(exc)}


@router.post("/license/sync")
async def license_sync_cloud(body: FirebaseTokenBody) -> dict:
    """After Firebase sign-in, pull paid subscription from Supabase to this device."""
    if _use_cloud_license_api():
        from aha.cloud_client import cloud_license_sync
        from aha.license import save_license_from_cloud

        try:
            result = cloud_license_sync(body.id_token)
            if result.get("valid") and result.get("license_key"):
                save_license_from_cloud(
                    result["license_key"],
                    result.get("plan", "core"),
                    result.get("expires"),
                )
            return result
        except RuntimeError as exc:
            return {"valid": False, "reason": "sync_failed", "message": str(exc)}

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


@router.get("/billing/ready")
async def billing_ready() -> dict:
    """Diagnostics for deploy — which server env vars are present (no secrets)."""
    from aha.billing import razorpay_configured, razorpay_env_diagnostics
    from aha.firebase_auth import firebase_env_diagnostics
    from aha.supabase_client import SUPABASE_SERVICE_KEY, SUPABASE_URL

    from aha.download_auth import package_available

    fb = firebase_env_diagnostics()

    return {
        "razorpay_configured": razorpay_configured(),
        "razorpay": razorpay_env_diagnostics(),
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_SERVICE_KEY),
        "firebase_configured": bool(fb.get("json_valid")),
        "firebase": fb,
        "downloads": {
            "mac": package_available("mac"),
            "win": package_available("win"),
        },
    }


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
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not create Razorpay order: {exc}",
        ) from exc


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


@router.get("/download/eligibility")
async def download_eligibility(user: dict = Depends(get_current_user)) -> dict:
    from aha.download_auth import eligibility_for_uid

    return await eligibility_for_uid(user["uid"])


@router.get("/download/{platform}")
async def download_package(platform: str, user: dict = Depends(get_current_user)):
    from fastapi.responses import RedirectResponse

    from aha.download_auth import resolve_download

    resolved = await resolve_download(user["uid"], platform)
    if not resolved.get("ok"):
        raise HTTPException(
            status_code=403 if resolved.get("reason") != "package_missing" else 404,
            detail=resolved.get("message") or resolved.get("reason", "download_denied"),
        )
    if resolved.get("kind") == "url":
        return RedirectResponse(url=resolved["url"], status_code=302)
    return FileResponse(
        resolved["path"],
        filename=resolved["filename"],
        media_type="application/zip",
    )


@router.post("/billing/validate_coupon")
async def billing_validate_coupon(
    body: RedeemCouponBody,
    user: dict = Depends(get_current_user),
) -> dict:
    """Check coupon discount before checkout (no redemption)."""
    from aha.coupons import validate_coupon

    try:
        return validate_coupon(body.coupon_code, body.plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/billing/redeem_coupon")
async def billing_redeem_coupon(
    body: RedeemCouponBody,
    user: dict = Depends(get_current_user),
) -> dict:
    """Redeem a 100% coupon (e.g. COUPON100) — no Razorpay payment."""
    from aha.coupons import redeem_coupon

    try:
        result = redeem_coupon(
            user["uid"],
            user.get("email", ""),
            body.plan_id,
            body.coupon_code,
        )
        return {"status": "ok", **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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


@router.get("/config/product_mode")
async def config_product_mode() -> dict:
    """Companion UI: Tier-1-only launch vs full assistant."""
    from aha.product_mode import product_mode_payload

    return product_mode_payload()


@router.post("/config/set_api_key")
async def config_set_api_key(body: SetApiKeyRequest) -> dict:
    """Store an API key for *provider*."""
    from aha.product_mode import tier1_only_mode

    if tier1_only_mode():
        raise HTTPException(
            status_code=403,
            detail="API keys are not used in Tier-1 mode. General AI assistance ships in a future update.",
        )
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
    from aha.product_mode import tier1_only_mode

    if tier1_only_mode():
        raise HTTPException(
            status_code=403,
            detail="API keys are not used in Tier-1 mode.",
        )
    result = delete_api_key(body.provider)
    if result.get("success"):
        from aha.agent_runtime import reset_agent

        reset_agent()
    return result


# ---------------------------------------------------------------------------
# Tier-1 local workspace (projects, SSH)
# ---------------------------------------------------------------------------


@router.get("/local/projects")
async def local_list_projects() -> dict:
    from aha.local_registry import list_projects

    return {"projects": list_projects()}


@router.post("/local/projects")
async def local_add_project(body: AddProjectRequest) -> dict:
    from aha.local_registry import add_project

    return add_project(body.name, body.path, branch=body.branch, remote=body.remote)


@router.delete("/local/projects")
async def local_remove_project(body: RemoveProjectRequest) -> dict:
    from aha.local_registry import remove_project

    return remove_project(body.name)


@router.get("/local/ssh")
async def local_ssh_status() -> dict:
    from aha.local_registry import read_public_key, ssh_key_exists, ssh_public_key_path

    return {
        "exists": ssh_key_exists(),
        "public_key": read_public_key(),
        "public_key_path": str(ssh_public_key_path()),
    }


@router.post("/local/ssh/generate")
async def local_ssh_generate(body: GenerateSshKeyRequest) -> dict:
    from aha.local_registry import generate_ssh_key

    return generate_ssh_key(overwrite=body.overwrite)
