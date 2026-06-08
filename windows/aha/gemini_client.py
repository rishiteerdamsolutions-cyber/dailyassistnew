"""
Gemini client — routes through Vercel proxy when cloud_proxy_enabled().
"""

from __future__ import annotations

import base64
import io
from typing import Any

from PIL import Image

from aha.byok import resolve_gemini_api_key
from aha.cloud_client import cloud_proxy_enabled, current_license_key, _post
from bol.config import BOLConfig

try:
    import google.generativeai as genai
except ImportError:
    genai = None


def _pil_to_inline_part(img: Image.Image) -> dict[str, Any]:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"inlineData": {"mimeType": "image/png", "data": b64}}


def _history_to_contents(history: list) -> list[dict[str, Any]]:
    """Convert google.generativeai chat history to REST contents."""
    out: list[dict[str, Any]] = []
    for item in history or []:
        role = getattr(item, "role", None) or (item.get("role") if isinstance(item, dict) else "user")
        if role == "model":
            role = "model"
        else:
            role = "user"
        parts_raw = getattr(item, "parts", None)
        if parts_raw is None and isinstance(item, dict):
            parts_raw = item.get("parts", [])
        parts: list[dict[str, Any]] = []
        for part in parts_raw or []:
            text = getattr(part, "text", None)
            if text is None and isinstance(part, dict):
                text = part.get("text")
            if text:
                parts.append({"text": text})
        if parts:
            out.append({"role": role, "parts": parts})
    return out


def generate_via_proxy(
    *,
    config: BOLConfig,
    model: str,
    prompt: str,
    image: Image.Image | None = None,
    system_instruction: str | None = None,
    history: list | None = None,
) -> str:
    license_key = current_license_key()
    byok = resolve_gemini_api_key(config)

    contents = _history_to_contents(history or [])
    user_parts: list[dict[str, Any]] = [{"text": prompt}]
    if image is not None:
        user_parts.append(_pil_to_inline_part(image))
    contents.append({"role": "user", "parts": user_parts})

    result = _post(
        "/api/proxy/gemini/generate",
        {
            "license_key": license_key,
            "byok_key": byok,
            "model": model,
            "contents": contents,
            "system_instruction": system_instruction,
            "generation_config": {"responseMimeType": "application/json"},
        },
        timeout=90.0,
    )
    return (result.get("text") or "").strip()


def generate_local(
    *,
    config: BOLConfig,
    model: str,
    prompt: str,
    image: Image.Image | None = None,
    system_instruction: str | None = None,
    history: list | None = None,
) -> tuple[str, list]:
    if genai is None:
        raise RuntimeError("google-generativeai is not installed.")

    api_key = resolve_gemini_api_key(config)
    if not api_key:
        raise RuntimeError("Gemini API key missing.")

    genai.configure(api_key=api_key)
    try:
        model_obj = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_instruction,
        )
    except Exception:
        model_obj = genai.GenerativeModel(model_name=model)

    chat = model_obj.start_chat(history=history or [])
    if image is not None:
        response = chat.send_message([prompt, image])
    else:
        response = chat.send_message(prompt)
    return response.text.strip(), chat.history


def generate_gemini(
    *,
    config: BOLConfig,
    model: str,
    prompt: str,
    image: Image.Image | None = None,
    system_instruction: str | None = None,
    history: list | None = None,
) -> tuple[str, list]:
    """
    Generate text via cloud proxy (retail) or direct SDK (dev).

    Returns (text, updated_history).
    """
    if cloud_proxy_enabled():
        text = generate_via_proxy(
            config=config,
            model=model,
            prompt=prompt,
            image=image,
            system_instruction=system_instruction,
            history=history,
        )
        updated = list(history or [])
        updated.append({"role": "user", "parts": [{"text": prompt}]})
        updated.append({"role": "model", "parts": [{"text": text}]})
        return text, updated

    text, updated = generate_local(
        config=config,
        model=model,
        prompt=prompt,
        image=image,
        system_instruction=system_instruction,
        history=history,
    )
    return text, updated
