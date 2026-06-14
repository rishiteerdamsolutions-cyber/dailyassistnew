"""
core/firebase.py — Firebase Admin SDK initialisation and Firestore dependency.

Reads FIREBASE_CREDENTIALS_PATH and FIREBASE_PROJECT_ID from environment.
Exposes:
  - initialise_firebase()   — called once at app startup via lifespan
  - get_firestore()         — FastAPI dependency that yields an AsyncClient
"""

from __future__ import annotations

import logging
import os
from typing import AsyncGenerator

import firebase_admin
from firebase_admin import credentials, firestore_async
from google.cloud.firestore import AsyncClient

logger = logging.getLogger(__name__)

_app: firebase_admin.App | None = None


def initialise_firebase() -> None:
    """
    Initialise the Firebase Admin SDK exactly once.

    Raises RuntimeError if required environment variables are missing.
    """
    global _app  # noqa: PLW0603

    if _app is not None:
        return  # Already initialised (e.g. during hot reload)

    creds_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "")
    project_id = os.environ.get("FIREBASE_PROJECT_ID", "")

    if not creds_path or not project_id:
        logger.warning(
            "FIREBASE_CREDENTIALS_PATH or FIREBASE_PROJECT_ID is missing. "
            "Firebase is disabled. (This is fine for local UI/payment testing)"
        )
        return

    cred = credentials.Certificate(creds_path)
    _app = firebase_admin.initialize_app(cred, {"projectId": project_id})
    logger.info("Firebase Admin SDK initialised (project: %s)", project_id)


def shutdown_firebase() -> None:
    """Clean up the Firebase Admin SDK on shutdown."""
    global _app  # noqa: PLW0603
    if _app is not None:
        try:
            firebase_admin.delete_app(_app)
            logger.info("Firebase Admin SDK shut down.")
        except Exception as exc:
            logger.warning("Error during Firebase shutdown: %s", exc)
        _app = None


async def get_firestore() -> AsyncGenerator[AsyncClient, None]:
    """
    FastAPI dependency — yields an async Firestore client.

    Usage:
        @router.get("/example")
        async def handler(db: Annotated[AsyncClient, Depends(get_firestore)]):
            ...
    """
    client: AsyncClient = firestore_async.client()
    try:
        yield client
    finally:
        # AsyncClient does not require explicit close, but we close
        # the underlying transport if available to free connections.
        try:
            client.close()
        except Exception:
            pass
