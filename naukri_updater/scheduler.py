"""
Scheduler and retry logic for Naukri Updater.

Handles the periodic scheduling loop, single update cycles with
exponential backoff retries, and consecutive failure tracking
with notifications.
"""

import time
import traceback
from datetime import datetime
from typing import Optional

import schedule
from playwright.sync_api import sync_playwright

from naukri_updater.auth import (
    has_profile_access,
    is_session_valid,
    login_and_save_session,
    save_session,
)
from naukri_updater.browser import XvfbDisplay, launch_browser
from naukri_updater.config import Config
from naukri_updater.logger import get_logger
from naukri_updater.notifications import NotificationManager
from naukri_updater.profile import update_profile

logger = get_logger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Retry with exponential backoff
# ═════════════════════════════════════════════════════════════════════════════

BACKOFF_DELAYS = [30, 60, 120]  # Seconds between retries.


def run_with_retry(
    config: Config,
    notifier: NotificationManager,
    max_retries: int = 3,
) -> bool:
    """
    Execute a single update cycle with exponential backoff retries.

    Args:
        config: Application configuration.
        notifier: Notification manager for alerts.
        max_retries: Maximum number of retry attempts.

    Returns:
        True if the update succeeded on any attempt.
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "Update attempt %d/%d...", attempt, max_retries
            )
            success = _run_single_cycle(config)
            if success:
                return True
            logger.warning("Attempt %d: update did not complete.", attempt)
        except Exception as exc:
            logger.error(
                "Attempt %d failed with error: %s", attempt, exc
            )
            logger.debug(traceback.format_exc())

        if attempt < max_retries:
            delay = BACKOFF_DELAYS[min(attempt - 1, len(BACKOFF_DELAYS) - 1)]
            logger.info("Retrying in %d seconds...", delay)
            time.sleep(delay)

    return False


def _run_single_cycle(config: Config) -> bool:
    """
    Execute one complete update cycle:
    1. Check/create session
    2. Launch browser
    3. Verify profile access (re-login if needed)
    4. Update profile

    Returns:
        True if the profile was updated successfully.
    """
    with XvfbDisplay():
        with sync_playwright() as playwright:
            session_file = config.session_file

            # Ensure a valid session exists.
            if not is_session_valid(
                session_file, config.session_max_age_hours
            ):
                logger.info("Session missing or expired — logging in...")
                login_and_save_session(playwright, config)

            # Launch browser with saved session.
            logger.info("Launching browser with saved session...")
            browser, context, page = launch_browser(
                playwright, session_file
            )

            try:
                # Verify we can access the profile.
                if not has_profile_access(page, config.profile_url):
                    logger.info("Session expired — re-logging in...")
                    context.close()
                    browser.close()

                    login_and_save_session(playwright, config)

                    # Reopen with fresh session.
                    browser, context, page = launch_browser(
                        playwright, session_file
                    )

                    if not has_profile_access(page, config.profile_url):
                        raise RuntimeError(
                            "Could not access profile after re-login. "
                            "Check credentials or anti-bot restrictions."
                        )

                # Update the profile.
                return update_profile(page, config)

            finally:
                context.close()
                browser.close()


# ═════════════════════════════════════════════════════════════════════════════
# Scheduler loop
# ═════════════════════════════════════════════════════════════════════════════


def start_scheduler(config: Config) -> None:
    """
    Start the scheduling loop that runs profile updates periodically.

    Tracks consecutive failures and sends notifications when failures
    exceed the configured threshold, or when the system recovers.
    """
    notifier = NotificationManager(config)
    consecutive_failures = 0

    def _scheduled_job() -> None:
        nonlocal consecutive_failures

        success = run_with_retry(
            config, notifier, max_retries=config.max_retries
        )

        if success:
            if consecutive_failures > 0:
                notifier.notify_recovery(
                    f"Profile update succeeded after {consecutive_failures} "
                    f"consecutive failure(s)."
                )
            consecutive_failures = 0
            notifier.notify_success()
        else:
            consecutive_failures += 1
            logger.error(
                "Update failed. Consecutive failures: %d/%d",
                consecutive_failures,
                config.max_consecutive_failures,
            )
            if consecutive_failures >= config.max_consecutive_failures:
                notifier.notify_failure(
                    f"Profile update has failed {consecutive_failures} "
                    f"consecutive times. Manual intervention may be needed.\n"
                    f"Last attempt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )

    # Configure schedule.
    if config.every_minutes:
        minutes = int(config.every_minutes)
        logger.info("Scheduling update every %d minute(s).", minutes)
        schedule.every(minutes).minutes.do(_scheduled_job)
    else:
        logger.info("Scheduling daily update at %s.", config.update_at)
        schedule.every().day.at(config.update_at).do(_scheduled_job)

    # Run first update immediately.
    logger.info("Running first update immediately...")
    _scheduled_job()

    logger.info("Scheduler started. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(1)
