"""
AHA — Artificial Human Assistant
pywebview desktop entry point.

Starts the FastAPI server in a background daemon thread,
then opens the companion UI in a native webview window.
"""

from __future__ import annotations

import os
import socket
import sys


def _bootstrap_retail_build() -> None:
    """Nuitka / PyInstaller: mark retail + Tier-1 before other imports."""
    frozen = getattr(sys, "frozen", False)
    main = sys.modules.get("__main__")
    if main and getattr(main, "__compiled__", False):
        frozen = True
    if not frozen:
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        if os.path.isdir(os.path.join(exe_dir, "web")):
            frozen = True
    if frozen:
        os.environ.setdefault("AHA_RETAIL_BUILD", "1")
        os.environ.setdefault("AHA_TIER1_ONLY", "1")


_bootstrap_retail_build()
import threading
import time
import urllib.error
import urllib.request

import uvicorn
import webview

from aha.env_loader import load_dotenv

load_dotenv()

from aha.runtime_paths import install_bundle_paths
from aha.tesseract_runtime import ensure_tesseract_configured

install_bundle_paths()
ensure_tesseract_configured()

from server import app  # noqa: E402

# ── Configuration ────────────────────────────────────────────────────
HOST = "127.0.0.1"
DEFAULT_PORT = 8000
SERVER_POLL_INTERVAL = 0.15
SERVER_POLL_TIMEOUT = 20.0


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((HOST, port))
            return True
        except OSError:
            return False


def _server_responds(port: int) -> bool:
    try:
        urllib.request.urlopen(f"http://{HOST}:{port}/companion", timeout=2)
        return True
    except (urllib.error.URLError, ConnectionError, OSError, TimeoutError):
        return False


def _resolve_port() -> tuple[int, bool]:
    """
    Return (port, start_new_server).

    Reuse an existing companion on DEFAULT_PORT if present; otherwise bind
    DEFAULT_PORT or the next free port in 8000–8009.
    """
    if _server_responds(DEFAULT_PORT):
        print(f"[AHA] Reusing existing server on http://{HOST}:{DEFAULT_PORT}/companion")
        return DEFAULT_PORT, False

    if _port_is_free(DEFAULT_PORT):
        return DEFAULT_PORT, True

    for port in range(DEFAULT_PORT + 1, DEFAULT_PORT + 10):
        if _port_is_free(port):
            print(f"[AHA] Port {DEFAULT_PORT} busy — using {port}")
            return port, True

    raise RuntimeError(
        f"No free port in {DEFAULT_PORT}–{DEFAULT_PORT + 9}. "
        "Stop other AHA/uvicorn processes and try again."
    )


def _run_server(port: int) -> None:
    uvicorn.run(app, host=HOST, port=port, log_level="warning")


def _wait_for_server(port: int) -> None:
    url = f"http://{HOST}:{port}/"
    deadline = time.monotonic() + SERVER_POLL_TIMEOUT
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(SERVER_POLL_INTERVAL)
    raise RuntimeError(f"Server did not become ready within {SERVER_POLL_TIMEOUT}s on port {port}")


class Api:
    """Python API that pywebview exposes to the JavaScript context."""

    def __init__(self) -> None:
        self._browser_window: webview.Window | None = None

    def open_browser(self, url: str) -> None:
        if self._browser_window is not None:
            try:
                self._browser_window.load_url(url)
                return
            except Exception:
                self._browser_window = None

        self._browser_window = webview.create_window(
            "AHA — Browser",
            url=url,
            width=1200,
            height=850,
        )

    def close_browser(self) -> None:
        if self._browser_window is not None:
            try:
                self._browser_window.destroy()
            except Exception:
                pass
            finally:
                self._browser_window = None


def _macos_request_accessibility_prompt() -> None:
    """Trigger the macOS Accessibility prompt so AHA appears in System Settings."""
    if sys.platform != "darwin":
        return

    def _poke() -> None:
        time.sleep(2.5)
        try:
            import pyautogui

            pyautogui.position()
        except Exception:
            pass

    threading.Thread(target=_poke, daemon=True).start()


def main() -> None:
    port, start_server = _resolve_port()
    companion_url = f"http://{HOST}:{port}/companion"

    if start_server:
        server_thread = threading.Thread(target=_run_server, args=(port,), daemon=True)
        server_thread.start()
        _wait_for_server(port)
    elif not _server_responds(port):
        raise RuntimeError(f"Port {port} is in use but not serving AHA companion.")

    api = Api()
    webview.create_window(
        title="AHA — Artificial Human Assistant",
        url=companion_url,
        width=1300,
        height=900,
        min_size=(900, 600),
        js_api=api,
    )

    _macos_request_accessibility_prompt()

    debug = os.environ.get("AHA_WEBVIEW_DEBUG", "").strip().lower() in ("1", "true", "yes")
    if debug:
        print(f"[AHA] Webview debug ON — {companion_url}")
    webview.start(debug=debug)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[AHA] Failed to start: {exc}", file=sys.stderr)
        sys.exit(1)
