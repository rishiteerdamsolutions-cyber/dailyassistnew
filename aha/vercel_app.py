"""
Minimal FastAPI for Vercel — /api/* only.

Static pages (subscribe, download, legal) live in public/ and are served by Vercel CDN.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

_origins = [
    "https://dailyassist.xyz",
    "https://www.dailyassist.xyz",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "https://dailyassist.vercel.app",
]
_vercel = os.environ.get("VERCEL_URL", "").strip()
if _vercel:
    _origins.append(f"https://{_vercel}")

app = FastAPI(title="AHA API — dailyassist.xyz")


@app.exception_handler(Exception)
async def unhandled_exception(_request: Request, exc: Exception) -> JSONResponse:
    """Always return JSON — avoids 'Unexpected token I' when the client parses HTML errors."""
    if isinstance(exc, HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})
    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

from aha.admin_routes import router as admin_router
from aha.api_routes import router as aha_router

app.include_router(aha_router)
app.include_router(admin_router)


from pydantic import BaseModel


class _FirebaseSigninRequest(BaseModel):
    id_token: str


@app.post("/api/auth/firebase_signin")
async def firebase_signin(req: _FirebaseSigninRequest):
    try:
        from aha.firebase_auth import verify_firebase_token
        from aha.supabase_client import upsert_user

        claims = verify_firebase_token(req.id_token)
        uid = claims["uid"]
        email = claims.get("email", "")
        name = claims.get("name") or claims.get("display_name", "")
        upsert_user(uid, email, name)
        return {"status": "ok", "uid": uid, "email": email}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "aha-api"}
