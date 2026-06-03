"""
Local API security for AHA.

Threat model: the FastAPI server binds to 127.0.0.1, but any process or
malicious web page the user visits can also reach localhost. These helpers add:

* A per-process **session token** that the companion page must echo back in the
  `X-AHA-Token` header. Cross-origin pages cannot read the token (it lives in
  same-origin HTML) and cannot forge the header past a locked-down CORS policy.
* **Server-side license enforcement** on automation/premium routes, so the UI
  license gate cannot be bypassed by calling the API directly.

Pure read-only demo endpoints and the license/config/vault setup endpoints stay
open so a fresh, unlicensed user can still activate and configure the app.
"""

from __future__ import annotations

import secrets

from fastapi import Request
from fastapi.responses import JSONResponse

from aha.license import check_license_status

# ── Session token ────────────────────────────────────────────────────
# Generated once per process start. Not persisted: a new run = a new token.
SESSION_TOKEN: str = secrets.token_urlsafe(32)
TOKEN_HEADER = "x-aha-token"


def get_session_token() -> str:
    return SESSION_TOKEN


# ── Route policy ─────────────────────────────────────────────────────
# Read-only demo/math endpoints — safe to leave open (used by dashboard/sandbox).
_OPEN_EXACT = {
    "/api/billing/config",
    "/api/timing",
    "/api/kinematic",
    "/api/policy",
    "/api/linguistic",
    "/api/lifecycle",
    "/api/hardware",
    "/api/policy/personalities",
    "/api/policy/simulate_typing",
}

# Endpoints reachable before a token/license exists (activation + setup).
_OPEN_PREFIXES = (
    "/api/license",
    "/api/auth",       # Firebase sign-in — no session token yet
    "/api/config",     # BYOK key management (session token added separately)
    "/api/billing",    # Razorpay — Firebase Bearer on create/verify; webhook unsigned
)

# Routes that require a valid license (also require the token).
_LICENSE_PREFIXES = (
    "/api/agent",
    "/api/browser",
    "/api/orchestrator",
    "/api/kinematic/physical_click",
    "/api/visual",
    "/api/workflows",
    "/api/content",
    "/api/routine",
)


def _needs_token(path: str) -> bool:
    if not path.startswith("/api/"):
        return False
    if path in _OPEN_EXACT:
        return False
    for prefix in _OPEN_PREFIXES:
        if path.startswith(prefix):
            return False
    return True


def _needs_license(path: str) -> bool:
    return any(path.startswith(p) for p in _LICENSE_PREFIXES)


async def security_middleware(request: Request, call_next):
    """Enforce session token + license on sensitive routes."""
    path = request.url.path
    method = request.method.upper()

    # CORS preflight must pass through untouched.
    if method == "OPTIONS":
        return await call_next(request)

    if _needs_token(path):
        provided = request.headers.get(TOKEN_HEADER, "")
        if not provided or not secrets.compare_digest(provided, SESSION_TOKEN):
            return JSONResponse(
                status_code=401,
                content={"status": "error", "message": "Unauthorized: missing or invalid session token."},
            )

        if _needs_license(path):
            try:
                status = check_license_status()
            except Exception:
                status = {"valid": False, "reason": "license_check_failed"}
            if not status.get("valid"):
                return JSONResponse(
                    status_code=403,
                    content={
                        "status": "error",
                        "message": "A valid AHA license is required for this action.",
                        "reason": status.get("reason", "no_license"),
                    },
                )

    return await call_next(request)
