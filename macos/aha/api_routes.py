"""
AHA Companion App – FastAPI routes for license & API-key management.

Usage in the main server::

    from aha.api_routes import router as api_router
    app.include_router(api_router)
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from aha.license import (
    activate_license,
    check_license_status,
    delete_api_key,
    get_api_keys,
    set_api_key,
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


# ---------------------------------------------------------------------------
# API-key (BYOK) endpoints
# ---------------------------------------------------------------------------


@router.post("/config/set_api_key")
async def config_set_api_key(body: SetApiKeyRequest) -> dict:
    """Store an API key for *provider*."""
    return set_api_key(body.provider, body.api_key)


@router.get("/config/get_api_keys")
async def config_get_api_keys() -> dict:
    """Return all stored API keys with values masked."""
    return get_api_keys()


@router.delete("/config/delete_api_key")
async def config_delete_api_key(body: DeleteApiKeyRequest) -> dict:
    """Remove the stored API key for *provider*."""
    return delete_api_key(body.provider)
