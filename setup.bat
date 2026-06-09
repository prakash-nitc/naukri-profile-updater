@echo off
REM ─────────────────────────────────────────────────────────────
REM  Naukri Profile Auto-Updater — one-command setup (Windows)
REM  Creates a virtual environment, installs dependencies, and
REM  downloads the Chromium browser Playwright needs.
REM ─────────────────────────────────────────────────────────────

echo.
echo === Naukri Updater setup ===
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed or not on PATH.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    exit /b 1
)

echo [1/4] Creating virtual environment (.venv)...
python -m venv .venv
if errorlevel 1 exit /b 1

echo [2/4] Installing Python dependencies...
call .venv\Scripts\python -m pip install --upgrade pip
call .venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo [3/4] Installing Chromium browser for Playwright...
call .venv\Scripts\python -m playwright install chromium
if errorlevel 1 exit /b 1

echo [4/4] Done!
echo.
echo Next steps:
echo   1. Activate the environment:  .venv\Scripts\activate
echo   2. Launch the dashboard:       python dashboard.py
echo   3. Open http://localhost:5000 and enter your details.
echo.
