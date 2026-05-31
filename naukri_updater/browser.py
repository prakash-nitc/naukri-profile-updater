"""
Browser management for Naukri Updater.

Handles Chromium launch in off-screen mode, virtual display (Xvfb) for
Linux servers, and platform-specific focus guards so the browser doesn't
steal your active window.
"""

import os
import shutil
import subprocess
import sys
import threading
import time
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, Playwright

from naukri_updater.logger import get_logger

logger = get_logger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Platform-specific focus management
# ═════════════════════════════════════════════════════════════════════════════


def get_active_app_macos() -> str:
    """Return the name of the currently frontmost app on macOS."""
    if sys.platform != "darwin":
        return ""
    try:
        result = subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "System Events" to get name of first '
                'application process whose frontmost is true',
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def restore_focus_macos(app_name: str) -> None:
    """Bring the given app back to focus on macOS."""
    if sys.platform != "darwin" or not app_name:
        return
    try:
        subprocess.run(
            ["osascript", "-e", f'tell application "{app_name}" to activate'],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def restore_focus_windows() -> None:
    """
    Restore focus to the previously active window on Windows.

    Uses ctypes to call SetForegroundWindow on the current foreground
    window's handle captured before the browser launched.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def _get_foreground_hwnd_windows() -> Optional[int]:
    """Capture the current foreground window handle on Windows."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        return ctypes.windll.user32.GetForegroundWindow()  # type: ignore[attr-defined]
    except Exception:
        return None


def _restore_hwnd_windows(hwnd: int) -> None:
    """Restore a specific window handle to foreground on Windows."""
    if sys.platform != "win32" or not hwnd:
        return
    try:
        import ctypes

        ctypes.windll.user32.SetForegroundWindow(hwnd)  # type: ignore[attr-defined]
    except Exception:
        pass


def _focus_guard_loop(
    app_name: str = "",
    hwnd: Optional[int] = None,
    duration: float = 5.0,
) -> None:
    """
    Repeatedly restore focus to the user's app for ``duration`` seconds.
    Runs in a background daemon thread to beat the browser's focus-steal.
    """
    end_time = time.time() + duration
    while time.time() < end_time:
        if sys.platform == "darwin" and app_name:
            restore_focus_macos(app_name)
        elif sys.platform == "win32" and hwnd:
            _restore_hwnd_windows(hwnd)
        time.sleep(0.15)


def start_focus_guard(
    app_name: str = "",
    hwnd: Optional[int] = None,
    duration: float = 5.0,
) -> None:
    """Kick off the focus guard in a daemon thread (fire and forget)."""
    if sys.platform == "darwin" and not app_name:
        return
    if sys.platform == "win32" and not hwnd:
        return
    t = threading.Thread(
        target=_focus_guard_loop,
        args=(app_name, hwnd, duration),
        daemon=True,
    )
    t.start()


def hide_browser_on_macos() -> None:
    """Best-effort hide for visible Chromium/Chrome windows on macOS."""
    if sys.platform != "darwin":
        return
    script = """\
    tell application "System Events"
        repeat with procName in {"Chromium", "Google Chrome", "Chrome"}
            try
                if exists process procName then
                    set visible of process procName to false
                end if
            end try
        end repeat
    end tell
    """
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


# ═════════════════════════════════════════════════════════════════════════════
# Xvfb virtual display for headless Linux servers
# ═════════════════════════════════════════════════════════════════════════════


class XvfbDisplay:
    """
    Manages a virtual X display (Xvfb) for headless Linux servers.
    Acts as a context manager: starts Xvfb on enter, kills it on exit.
    """

    def __init__(self, display: str = ":99") -> None:
        self.display = display
        self._proc: Optional[subprocess.Popen] = None

    def start(self) -> bool:
        if sys.platform != "linux":
            return False
        if not shutil.which("Xvfb"):
            logger.warning(
                "Xvfb not found. Install with: sudo apt-get install xvfb"
            )
            return False

        env = os.environ.copy()
        env["DISPLAY"] = self.display
        self._proc = subprocess.Popen(
            ["Xvfb", self.display, "-screen", "0", "1280x900x24"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.environ["DISPLAY"] = self.display
        time.sleep(0.8)
        logger.info("Xvfb virtual display started on %s", self.display)
        return True

    def stop(self) -> None:
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None
            logger.info("Xvfb virtual display stopped.")

    def __enter__(self) -> "XvfbDisplay":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()


# ═════════════════════════════════════════════════════════════════════════════
# Browser launch
# ═════════════════════════════════════════════════════════════════════════════


def _offscreen_launch_args() -> list[str]:
    """Chrome flags that push the window completely off all screens."""
    args = [
        "--window-position=-32000,-32000",
        "--window-size=1280,900",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-infobars",
        "--disable-extensions",
        "--start-minimized",
    ]
    if sys.platform == "linux":
        args += [
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ]
    return args


def launch_browser(
    playwright: Playwright,
    session_file: Optional[str] = None,
) -> tuple[Browser, BrowserContext, Page]:
    """
    Launch an off-screen Chromium browser that won't steal focus.

    Naukri blocks true headless mode, so we launch a real browser
    positioned far off-screen. A focus-guard thread keeps your
    active application in the foreground.

    Args:
        playwright: A Playwright instance.
        session_file: Optional path to a saved session state file.

    Returns:
        A (browser, context, page) tuple.
    """
    # Capture current focus before launching.
    previous_app = get_active_app_macos()
    previous_hwnd = _get_foreground_hwnd_windows()

    # Start focus guard BEFORE launch to beat the browser's focus-steal.
    start_focus_guard(
        app_name=previous_app,
        hwnd=previous_hwnd,
        duration=5.0,
    )

    args = _offscreen_launch_args()
    browser = playwright.chromium.launch(headless=False, args=args)

    # Secondary attempt to hide the browser window.
    time.sleep(0.5)
    hide_browser_on_macos()

    ctx_kwargs: dict = {}
    if session_file and os.path.exists(session_file):
        ctx_kwargs["storage_state"] = session_file

    context = browser.new_context(**ctx_kwargs)
    page = context.new_page()

    logger.debug("Browser launched (off-screen, non-headless).")
    return browser, context, page
