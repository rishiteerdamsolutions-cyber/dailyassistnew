"""Vercel serverless — billing + auth API only (no desktop server.py)."""

from aha.vercel_app import app

# Vercel Python runtime expects a module-level `app` (ASGI).
