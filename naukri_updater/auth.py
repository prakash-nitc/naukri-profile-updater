"""
Authentication and session management for Naukri Updater.

Handles login flow, session persistence, and session expiry tracking
via a sidecar metadata file.
"""

import json
import os
import time
from typing import Optional

from playwright.sync_api import BrowserContext, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from naukri_updater.browser import launch_browser
from naukri_updater.config import Config
from naukri_updater.logger import get_logger
from naukri_updater.selectors import COOKIE, LOGIN

logger = get_logger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Cookie banners
# ═════════════════════════════════════════════════════════════════════════════


def accept_cookie_if_present(page: Page) -> None:
    """Dismiss cookie consent banners if visible."""
    for selector in COOKIE.accept_buttons:
        try:
            button = page.locator(selector).first
            if button.is_visible(timeout=1500):
                button.click(timeout=1500)
                logger.debug("Cookie banner dismissed.")
                return
        except PlaywrightTimeoutError:
            continue
        except Exception:
            logger.debug("Cookie dismiss failed for selector: %s", selector)
            continue


# ═════════════════════════════════════════════════════════════════════════════
# Login
# ═════════════════════════════════════════════════════════════════════════════


def _fill_first_visible(
    page: Page,
    selectors: tuple[str, ...],
    value: str,
    field_name: str,
) -> bool:
    """Fill the first visible field matching any of the selectors."""
    for selector in selectors:
        try:
            field = page.locator(selector).first
            if field.is_visible(timeout=1500):
                field.fill(value, timeout=4000)
                return True
        except PlaywrightTimeoutError:
            continue
        except Exception:
            logger.debug("Fill failed for %s selector: %s", field_name, selector)
            continue

    logger.warning("Could not find %s field with current selectors.", field_name)
    return False


def login(page: Page, config: Config) -> None:
    """
    Log in to Naukri using email/password credentials.

    Tries the direct login URL first, then falls back to the homepage
    login flow if the direct URL has changed.

    Raises:
        RuntimeError: If login fields are not found or login fails.
    """
    logger.info("Opening Naukri login page...")
    page.goto(
        "https://www.naukri.com/nlogin/login", wait_until="domcontentloaded"
    )
    page.wait_for_load_state("networkidle", timeout=10000)
    accept_cookie_if_present(page)

    # ── Fill email ───────────────────────────────────────────────────────
    if not _fill_first_visible(page, LOGIN.email, config.email, "email"):
        logger.info("Trying homepage login flow...")
        page.goto("https://www.naukri.com/", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=10000)
        accept_cookie_if_present(page)

        # Click a login opener link/button.
        for selector in LOGIN.login_openers:
            try:
                opener = page.locator(selector).first
                if opener.is_visible(timeout=1200):
                    opener.click(timeout=3000)
                    page.wait_for_load_state("networkidle", timeout=8000)
                    break
            except Exception:
                continue

        if not _fill_first_visible(page, LOGIN.email, config.email, "email"):
            raise RuntimeError(
                "Could not find email field. Likely captcha/anti-bot or UI "
                "changed. Run with HEADLESS=false and login manually once."
            )

    # ── Fill password ────────────────────────────────────────────────────
    if not _fill_first_visible(
        page, LOGIN.password, config.password, "password"
    ):
        raise RuntimeError(
            "Could not find password field. "
            "Run with HEADLESS=false and update selectors."
        )

    # ── Click submit ─────────────────────────────────────────────────────
    clicked_submit = False
    for selector in LOGIN.submit:
        try:
            button = page.locator(selector).first
            if button.is_visible(timeout=1500):
                button.click(timeout=4000)
                clicked_submit = True
                break
        except Exception:
            continue

    if not clicked_submit:
        raise RuntimeError(
            "Could not find login submit button. "
            "Run with HEADLESS=false and update selectors."
        )

    # ── Wait for navigation ──────────────────────────────────────────────
    try:
        page.wait_for_url("**naukri.com/**", timeout=15000)
    except PlaywrightTimeoutError:
        logger.debug("URL wait timed out — checking login status anyway.")

    page.wait_for_load_state("networkidle", timeout=10000)

    if "login" in page.url.lower():
        raise RuntimeError(
            "Login appears unsuccessful. "
            "Check credentials or complete captcha/2FA manually."
        )

    logger.info("Login successful.")


# ═════════════════════════════════════════════════════════════════════════════
# Session management
# ═════════════════════════════════════════════════════════════════════════════


def _session_meta_path(session_file: str) -> str:
    """Return the path to the session metadata sidecar file."""
    return session_file + ".meta.json"


def save_session(context: BrowserContext, session_file: str) -> None:
    """
    Save browser session state and record the timestamp.

    Creates both the Playwright storage state file and a sidecar
    .meta.json with the save timestamp for expiry tracking.
    """
    context.storage_state(path=session_file)

    meta = {"saved_at": time.time(), "version": 1}
    meta_path = _session_meta_path(session_file)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    logger.info("Session saved to %s", session_file)


def is_session_valid(session_file: str, max_age_hours: int = 24) -> bool:
    """
    Check whether a saved session exists and is not expired.

    Args:
        session_file: Path to the Playwright session state file.
        max_age_hours: Maximum age in hours before the session is
                       considered stale.

    Returns:
        True if the session file exists and is younger than max_age_hours.
    """
    if not os.path.exists(session_file):
        logger.debug("No session file found at %s", session_file)
        return False

    meta_path = _session_meta_path(session_file)
    if not os.path.exists(meta_path):
        # Session exists but no meta — treat as potentially stale.
        logger.debug("Session file exists but no metadata — treating as valid.")
        return True

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        saved_at = meta.get("saved_at", 0)
        age_hours = (time.time() - saved_at) / 3600
        if age_hours > max_age_hours:
            logger.info(
                "Session is %.1f hours old (max %d) — will re-login.",
                age_hours,
                max_age_hours,
            )
            return False
        logger.debug("Session is %.1f hours old — still valid.", age_hours)
        return True
    except (json.JSONDecodeError, KeyError, TypeError):
        logger.warning("Could not read session metadata — treating as valid.")
        return True


def has_profile_access(page: Page, profile_url: str) -> bool:
    """
    Navigate to the profile page and check if we have access.

    Returns False if we're redirected to a login page or see an
    access denied message.
    """
    logger.info("Checking profile access...")
    page.goto(profile_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=10000)
    logger.debug("Profile page URL: %s", page.url)

    if "login" in page.url.lower():
        logger.info("Redirected to login — session expired.")
        return False

    try:
        title = page.title().lower()
        body_text = page.inner_text("body").lower()
        if "access denied" in title or "you don't have permission" in body_text:
            logger.warning("Access denied on profile page.")
            return False
    except Exception:
        logger.debug("Could not read page content for access check.")

    return True


def login_and_save_session(
    playwright: "Playwright",
    config: Config,
) -> None:
    """Login via off-screen browser and persist session to disk."""
    logger.info("Opening browser for login...")
    browser, context, page = launch_browser(playwright)
    try:
        login(page, config)
        save_session(context, config.session_file)
    finally:
        context.close()
        browser.close()
