"""
Minimal FastAPI for Vercel — /api/* only.

Static pages (subscribe, download, legal) live in public/ and are served by Vercel CDN.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_origins = [
    "https://dailyassist.xyz",
    "https://www.dailyassist.xyz",
    "https://dailyassist.vercel.app",
]
_vercel = os.environ.get("VERCEL_URL", "").strip()
if _vercel:
    _origins.append(f"https://{_vercel}")

app = FastAPI(title="AHA API — dailyassist.xyz")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

from aha.api_routes import router as aha_router

app.include_router(aha_router)


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
