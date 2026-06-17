"""
main.py — AHA Chrome Extension FastAPI backend.

Startup
-------
  python main.py
  or
  uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info

Environment variables (see .env.example):
  FIREBASE_PROJECT_ID       — GCP project ID
  FIREBASE_CREDENTIALS_PATH — Path to service-account JSON
  RAZORPAY_WEBHOOK_SECRET   — Razorpay webhook signing secret
  ALLOWED_ORIGINS           — Comma-separated list of allowed CORS origins
  BACKEND_PORT              — Port to listen on (default: 8000)
"""

from __future__ import annotations

import logging
import logging.config
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Annotated

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from google.cloud.firestore import AsyncClient

# Load .env before any module reads os.environ
load_dotenv()

from api.license import router as license_router
from api.payments import router as payments_router
from api.webhooks import router as webhooks_router
from core.firebase import get_firestore, initialise_firebase, shutdown_firebase
from ws.handler import handle_agent_session

# ── Logging configuration ─────────────────────────────────────────────────────

LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
    "loggers": {
        "uvicorn": {"propagate": True},
        "uvicorn.error": {"propagate": True},
        "uvicorn.access": {"propagate": True},
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


# ── CORS origins ──────────────────────────────────────────────────────────────

def _get_allowed_origins() -> list[str]:
    """
    Parse ALLOWED_ORIGINS from environment.

    Must be a comma-separated list of full origins, e.g.:
      https://app.aha.ai,https://dashboard.aha.ai

    Chrome extensions use chrome-extension://<id> as their origin.
    Add those to the list as needed.
    """
    raw = os.environ.get("ALLOWED_ORIGINS", "*")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not origins:
        logger.warning(
            "ALLOWED_ORIGINS is not set. "
            "CORS will reject all cross-origin requests."
        )
    return origins


# ── Application lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage startup and shutdown tasks.

    Startup:  Initialise Firebase Admin SDK
    Shutdown: Cleanly close Firebase connections
    """
    logger.info("═══ AHA Backend starting up ═══")
    try:
        initialise_firebase()
    except RuntimeError as exc:
        logger.critical("Firebase initialisation failed: %s", exc)
        raise

    yield  # Application runs here

    logger.info("═══ AHA Backend shutting down ═══")
    shutdown_firebase()


# ── FastAPI application ───────────────────────────────────────────────────────

app = FastAPI(
    title="AHA Chrome Extension Backend",
    description=(
        "Human-like social media agent backend. "
        "Generates Bezier mouse trajectories, keystroke sequences, "
        "and validates Razorpay subscription licenses via Firebase."
    ),
    version="1.0.0",
    lifespan=lifespan,
    # Disable docs in production by setting docs_url=None here if needed
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ───────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),   # Never allow_origins=["*"] in production
    allow_origin_regex=r"^chrome-extension://.*$",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-Razorpay-Signature"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(webhooks_router)
app.include_router(payments_router)


# ── Static Frontend Mount ─────────────────────────────────────────────────────

# Serve static files from the frontend 'web' folder
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
if os.path.isdir(WEB_DIR):
    # API endpoints must be matched before static files catch-all
    @app.get("/")
    async def serve_landing():
        return FileResponse(os.path.join(WEB_DIR, "landing.html"))
        
    @app.get("/success")
    async def serve_success():
        return FileResponse(os.path.join(WEB_DIR, "success.html"))
        
    @app.get("/companion")
    async def serve_companion():
        return FileResponse(os.path.join(WEB_DIR, "companion.html"))
        
    @app.get("/legal")
    async def serve_legal():
        return FileResponse(os.path.join(WEB_DIR, "legal.html"))

    @app.get("/AHA-extension.zip")
    async def download_extension():
        zip_path = os.path.join(WEB_DIR, "AHA-extension.zip")
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename="AHA-extension.zip"
        )

    @app.get("/AHA-Storage-Vault.zip")
    async def download_vault_template():
        zip_path = os.path.join(WEB_DIR, "AHA-Storage-Vault.zip")
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename="AHA-Storage-Vault.zip"
        )

    app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"], status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    """Liveness probe endpoint."""
    return JSONResponse(content={"status": "healthy", "service": "aha-backend"})


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws/agent")
async def ws_agent_endpoint(
    websocket: WebSocket,
    db: AsyncClient = Depends(get_firestore),
) -> None:
    """
    WebSocket endpoint for the AHA Chrome Extension agent.
    Runs the posting flow, streaming mouse/keyboard commands back to the extension.
    """
    await handle_agent_session(
        ws=websocket,
        db=db,
    )


# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s: %s", request.method, request.url, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal error occurred."},
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("BACKEND_PORT", "8000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_config=LOGGING_CONFIG,
        reload=False,   # Set to True for development; never in production
        access_log=True,
    )
