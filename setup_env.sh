#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# BOL Environment Bootstrap Script (macOS)
# Installs system dependencies, creates a virtual environment,
# and installs all Python packages.
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"

echo "═══════════════════════════════════════════════════════════"
echo "  BOL — Behavioral Operating Layer — Environment Setup"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ── 1. Check macOS ──────────────────────────────────────────────────
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "⚠  This bootstrap script targets macOS. Detected: $(uname -s)"
    echo "   Adjust system dependency installation for your platform."
    exit 1
fi

# ── 2. Check/Install Homebrew ───────────────────────────────────────
if ! command -v brew &>/dev/null; then
    echo "▸ Homebrew not found. Installing…"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "✓ Homebrew detected at $(command -v brew)"
fi

# ── 3. Install Tesseract OCR Engine ─────────────────────────────────
if ! command -v tesseract &>/dev/null; then
    echo "▸ Installing Tesseract OCR via Homebrew…"
    brew install tesseract
else
    echo "✓ Tesseract detected: $(tesseract --version 2>&1 | head -1)"
fi

# ── 4. Check Python 3.11+ ──────────────────────────────────────────
PYTHON_CMD=""
for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major=$("$candidate" -c "import sys; print(sys.version_info.major)")
        minor=$("$candidate" -c "import sys; print(sys.version_info.minor)")
        if [[ "$major" -ge 3 && "$minor" -ge 11 ]]; then
            PYTHON_CMD="$candidate"
            echo "✓ Python ${version} detected at $(command -v "$candidate")"
            break
        fi
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    echo "✗ Python 3.11+ required but not found."
    echo "  Install via: brew install python@3.12"
    exit 1
fi

# ── 5. Create Virtual Environment ──────────────────────────────────
if [[ -d "$VENV_DIR" ]]; then
    echo "✓ Virtual environment exists at ${VENV_DIR}"
else
    echo "▸ Creating virtual environment…"
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    echo "✓ Virtual environment created at ${VENV_DIR}"
fi

# ── 6. Activate and Install Dependencies ───────────────────────────
source "${VENV_DIR}/bin/activate"
echo "▸ Upgrading pip…"
pip install --upgrade pip --quiet

echo "▸ Installing BOL dependencies…"
pip install -e ".[dev]" --quiet

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✓ Environment ready."
echo ""
echo "  Activate with:  source ${VENV_DIR}/bin/activate"
echo "  Run with:        python -m bol.main"
echo "  Test with:       pytest tests/ -v"
echo ""
echo "  ⚠  IMPORTANT: Grant macOS permissions in"
echo "     System Settings → Privacy & Security:"
echo "     • Accessibility   (for pyautogui mouse/keyboard)"
echo "     • Screen Recording (for mss screen capture)"
echo "═══════════════════════════════════════════════════════════"
