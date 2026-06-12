"""
AHA — Artificial Human Assistant
pywebview desktop entry point.

Starts the FastAPI server in a background daemon thread,
then opens the companion UI in a native webview window.
"""

import threading
import time
import urllib.request
import urllib.error

import uvicorn
import webview

from server import app

# ── Configuration ────────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 8000
COMPANION_URL = f"http://{HOST}:{PORT}/companion"
SERVER_POLL_INTERVAL = 0.15  # seconds between readiness checks
SERVER_POLL_TIMEOUT = 15.0   # max seconds to wait for the server


# ── Server helpers ───────────────────────────────────────────────────

def _run_server() -> None:
    """Run the FastAPI/uvicorn server (blocking)."""
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def _wait_for_server() -> None:
    """Poll the server until it responds or the timeout expires."""
    deadline = time.monotonic() + SERVER_POLL_TIMEOUT
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"http://{HOST}:{PORT}/", timeout=1)
            return
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(SERVER_POLL_INTERVAL)
    raise RuntimeError(
        f"Server did not become ready within {SERVER_POLL_TIMEOUT}s"
    )


# ── JS-exposed API ──────────────────────────────────────────────────

class Api:
    """Python API that pywebview exposes to the JavaScript context."""

    def __init__(self) -> None:
        self._browser_window: webview.Window | None = None

    def open_browser(self, url: str) -> None:
        """Open (or navigate) a secondary browser window to *url*."""
        if self._browser_window is not None:
            try:
                self._browser_window.load_url(url)
                return
            except Exception:
                # Window was probably closed by the user; create a new one.
                self._browser_window = None

        self._browser_window = webview.create_window(
            "AHA — Browser",
            url=url,
            width=1200,
            height=850,
        )

    def close_browser(self) -> None:
        """Close the secondary browser window if it exists."""
        if self._browser_window is not None:
            try:
                self._browser_window.destroy()
            except Exception:
                pass
            finally:
                self._browser_window = None


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    # 1. Start the FastAPI server in a daemon thread.
    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()

    # 2. Wait until the server is accepting connections.
    _wait_for_server()

    # 3. Create the JS-exposed API instance.
    api = Api()

    # 4. Create the main companion window.
    webview.create_window(
        title="AHA — Artificial Human Assistant",
        url=COMPANION_URL,
        width=1300,
        height=900,
        min_size=(900, 600),
        js_api=api,
    )

    # 5. Start the webview event loop (blocks until all windows close).
    webview.start(debug=False)


if __name__ == "__main__":
    main()
