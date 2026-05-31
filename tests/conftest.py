"""Shared test fixtures."""

import os

import pytest


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure tests don't leak env vars."""
    env_vars = [
        "NAUKRI_EMAIL",
        "NAUKRI_PASSWORD",
        "UPDATE_EVERY_MINUTES",
        "UPDATE_AT_HHMM",
        "HEADLESS",
        "PROFILE_URL",
        "USE_SAVED_SESSION",
        "SAVE_SESSION_AFTER_LOGIN",
        "SESSION_FILE",
        "SESSION_MAX_AGE_HOURS",
        "ENABLE_RANDOM_NAME_UPDATE",
        "NAME_VARIANT_1",
        "NAME_VARIANT_2",
        "LOG_LEVEL",
        "LOG_FILE",
        "MAX_RETRIES",
        "MAX_CONSECUTIVE_FAILURES",
        "NOTIFY_WEBHOOK_URL",
        "NOTIFY_TELEGRAM_BOT_TOKEN",
        "NOTIFY_TELEGRAM_CHAT_ID",
        "NOTIFY_EMAIL_SMTP_HOST",
        "NOTIFY_EMAIL_SMTP_PORT",
        "NOTIFY_EMAIL_FROM",
        "NOTIFY_EMAIL_PASSWORD",
        "NOTIFY_EMAIL_TO",
        "LAUNCH_MINIMIZED",
        "HIDE_BROWSER_WINDOW",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)
