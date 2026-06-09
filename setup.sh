#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  Naukri Profile Auto-Updater — one-command setup (macOS/Linux)
#  Creates a virtual environment, installs dependencies, and
#  downloads the Chromium browser Playwright needs.
# ─────────────────────────────────────────────────────────────
set -e

echo
echo "=== Naukri Updater setup ==="
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] Python 3 is not installed or not on PATH."
    echo "Install Python 3.10+ from https://www.python.org/downloads/"
    exit 1
fi

echo "[1/4] Creating virtual environment (.venv)..."
python3 -m venv .venv

echo "[2/4] Installing Python dependencies..."
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

echo "[3/4] Installing Chromium browser for Playwright..."
./.venv/bin/python -m playwright install chromium

# Linux servers also need system libs for Chromium.
if [ "$(uname)" = "Linux" ]; then
    echo "      (On a headless Linux server you may also need: "
    echo "       sudo ./.venv/bin/python -m playwright install-deps chromium  +  sudo apt-get install xvfb)"
fi

echo "[4/4] Done!"
echo
echo "Next steps:"
echo "  1. Activate the environment:  source .venv/bin/activate"
echo "  2. Launch the dashboard:       python dashboard.py"
echo "  3. Open http://localhost:5000 and enter your details."
echo
