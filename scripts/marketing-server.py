#!/usr/bin/env python3
"""Local static server for public/ with clean URLs (/pricing, not only /pricing/)."""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "public"

# Paths without trailing slash -> file under public/
CLEAN_ROUTES = {
    "/": "/index.html",
    "/pricing": "/pricing/index.html",
    "/subscribe": "/subscribe/index.html",
    "/download": "/download/index.html",
    "/how-it-works": "/how-it-works/index.html",
    "/faq": "/faq/index.html",
    "/about": "/about/index.html",
    "/contact": "/contact/index.html",
    "/legal": "/legal/index.html",
}


class MarketingHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        path_only = self.path.split("?", 1)[0].rstrip("/") or "/"
        query = ""
        if "?" in self.path:
            query = "?" + self.path.split("?", 1)[1]
        target = CLEAN_ROUTES.get(path_only)
        if target:
            file_path = ROOT / target.lstrip("/")
            if file_path.is_file():
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(file_path.read_bytes())
                return
        return super().do_GET()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve AHA marketing site from public/")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), MarketingHandler)
    print(f"Marketing site: http://127.0.0.1:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
