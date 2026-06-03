#!/bin/bash

echo "=========================================="
echo "Starting Biological Agent Companion App..."
echo "=========================================="

# Change to the directory where this script is located
cd "$(dirname "$0")"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 is not installed. Please install Python 3."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install requirements
echo "[INFO] Installing dependencies..."
pip install -r requirements.txt
pip install -e .

# Start the server in the background
echo "[INFO] Starting Backend Server..."
uvicorn server:app --port 8000 &
SERVER_PID=$!

# Wait 2 seconds for server to boot
sleep 2

# Open the sandbox in Safari to keep Chrome free for the Agent (prevents infinite mirrors)
echo "[INFO] Opening Companion App UI in Safari..."
open -a Safari web/companion.html

echo "[INFO] System is running! Press Ctrl+C to stop the server."
wait $SERVER_PID
