#!/bin/bash
cd "$(dirname "$0")"
echo "Starting AHA — Artificial Human Assistant..."
.venv/bin/python app_webview.py
