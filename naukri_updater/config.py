"""
Configuration loader for Naukri Updater.

Reads settings from environment variables (via .env file) and returns
a validated, typed Config dataclass. No hardcoded personal data.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

from naukri_updater.logger import get_logger

logger = get_logger(__name__)


def as_bool(value: Optional[str], default: bool = True) -> bool:
    """Convert an env var string to a boolean, with a sensible default."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Config:
    """Immutable configuration for a Naukri update run."""

    # ── Required ─────────────────────────────────────────────────────────
    email: str
    password: str

    # ── Scheduling ───────────────────────────────────────────────────────
    every_minutes: Optional[str] = None
    update_at: Optional[str] = None

    # ── Browser ──────────────────────────────────────────────────────────
    profile_url: str = "https://www.naukri.com/mnjuser/profile"
    headless: bool = True
    launch_minimized: bool = True
    hide_browser_window: bool = True

    # ── Session ──────────────────────────────────────────────────────────
    use_saved_session: bool = True
    save_session_after_login: bool = True
    session_file: str = "naukri_session.json"
    session_max_age_hours: int = 24

    # ── Name Rotation ────────────────────────────────────────────────────
    random_name_update: bool = True
    name_variant_1: str = ""
    name_variant_2: str = ""

    # ── Retry ────────────────────────────────────────────────────────────
    max_retries: int = 3
    max_consecutive_failures: int = 5

    # ── Logging ──────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # ── Notifications ────────────────────────────────────────────────────
    notify_webhook_url: Optional[str] = None
    notify_telegram_bot_token: Optional[str] = None
    notify_telegram_chat_id: Optional[str] = None
    notify_email_smtp_host: Optional[str] = None
    notify_email_smtp_port: int = 587
    notify_email_from: Optional[str] = None
    notify_email_password: Optional[str] = None
    notify_email_to: Optional[str] = None


def load_config(env_path: Optional[str] = None) -> Config:
    """
    Load and validate configuration from environment variables.

    Args:
        env_path: Optional path to the .env file. Defaults to auto-detection.

    Returns:
        A validated Config instance.

    Raises:
        ValueError: If required fields are missing or conflicting options set.
    """
    load_dotenv(env_path)

    email = os.getenv("NAUKRI_EMAIL", "").strip()
    password = os.getenv("NAUKRI_PASSWORD", "").strip()

    if not email or not password:
        raise ValueError(
            "NAUKRI_EMAIL and NAUKRI_PASSWORD must be set in your .env file. "
            "See .env.example for reference."
        )

    every_minutes = os.getenv("UPDATE_EVERY_MINUTES", "").strip() or None
    update_at = os.getenv("UPDATE_AT_HHMM", "").strip() or None

    if every_minutes and update_at:
        raise ValueError(
            "Set only ONE of UPDATE_EVERY_MINUTES or UPDATE_AT_HHMM, not both."
        )

    # Default to every 4 hours if neither is set.
    if not every_minutes and not update_at:
        every_minutes = "240"
        logger.info("No schedule set — defaulting to every 240 minutes.")

    # Name variants: require explicit config if name rotation is enabled.
    random_name_update = as_bool(
        os.getenv("ENABLE_RANDOM_NAME_UPDATE", "false"), default=False
    )
    name_variant_1 = os.getenv("NAME_VARIANT_1", "").strip()
    name_variant_2 = os.getenv("NAME_VARIANT_2", "").strip()

    if random_name_update and (not name_variant_1 or not name_variant_2):
        raise ValueError(
            "ENABLE_RANDOM_NAME_UPDATE is on but NAME_VARIANT_1 and/or "
            "NAME_VARIANT_2 are not set. Please configure both in .env."
        )

    smtp_port_raw = os.getenv("NOTIFY_EMAIL_SMTP_PORT", "587").strip()
    try:
        smtp_port = int(smtp_port_raw)
    except ValueError:
        smtp_port = 587

    config = Config(
        email=email,
        password=password,
        every_minutes=every_minutes,
        update_at=update_at,
        profile_url=os.getenv(
            "PROFILE_URL", "https://www.naukri.com/mnjuser/profile"
        ).strip(),
        headless=as_bool(os.getenv("HEADLESS", "true"), default=True),
        launch_minimized=as_bool(
            os.getenv("LAUNCH_MINIMIZED", "true"), default=True
        ),
        hide_browser_window=as_bool(
            os.getenv("HIDE_BROWSER_WINDOW", "true"), default=True
        ),
        use_saved_session=as_bool(
            os.getenv("USE_SAVED_SESSION", "true"), default=True
        ),
        save_session_after_login=as_bool(
            os.getenv("SAVE_SESSION_AFTER_LOGIN", "true"), default=True
        ),
        session_file=os.getenv("SESSION_FILE", "naukri_session.json").strip(),
        session_max_age_hours=int(
            os.getenv("SESSION_MAX_AGE_HOURS", "24").strip() or "24"
        ),
        random_name_update=random_name_update,
        name_variant_1=name_variant_1,
        name_variant_2=name_variant_2,
        max_retries=int(os.getenv("MAX_RETRIES", "3").strip() or "3"),
        max_consecutive_failures=int(
            os.getenv("MAX_CONSECUTIVE_FAILURES", "5").strip() or "5"
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        log_file=os.getenv("LOG_FILE"),
        notify_webhook_url=os.getenv("NOTIFY_WEBHOOK_URL"),
        notify_telegram_bot_token=os.getenv("NOTIFY_TELEGRAM_BOT_TOKEN"),
        notify_telegram_chat_id=os.getenv("NOTIFY_TELEGRAM_CHAT_ID"),
        notify_email_smtp_host=os.getenv("NOTIFY_EMAIL_SMTP_HOST"),
        notify_email_smtp_port=smtp_port,
        notify_email_from=os.getenv("NOTIFY_EMAIL_FROM"),
        notify_email_password=os.getenv("NOTIFY_EMAIL_PASSWORD"),
        notify_email_to=os.getenv("NOTIFY_EMAIL_TO"),
    )

    logger.debug("Configuration loaded successfully.")
    return config
