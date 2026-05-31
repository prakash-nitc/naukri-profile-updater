"""
Notification system for Naukri Updater.

Supports multiple notification channels (webhook, email, Telegram)
so you know when profile updates succeed, fail, or need attention.
"""

import smtplib
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from typing import Optional

import requests

from naukri_updater.config import Config
from naukri_updater.logger import get_logger

logger = get_logger(__name__)


class Notifier(ABC):
    """Base class for notification backends."""

    @abstractmethod
    def send(self, title: str, message: str, level: str = "info") -> bool:
        """
        Send a notification.

        Args:
            title: Short summary (e.g., "Profile Updated").
            message: Detailed message body.
            level: One of "info", "warning", "error".

        Returns:
            True if sent successfully.
        """
        ...


class WebhookNotifier(Notifier):
    """
    Generic webhook notifier (works with Slack, Discord, etc.).

    Sends a JSON POST request to the configured URL.
    """

    def __init__(self, url: str) -> None:
        self.url = url

    def send(self, title: str, message: str, level: str = "info") -> bool:
        emoji = {"info": "✅", "warning": "⚠️", "error": "❌"}.get(level, "ℹ️")
        payload = {"text": f"{emoji} *{title}*\n{message}"}
        try:
            resp = requests.post(self.url, json=payload, timeout=10)
            resp.raise_for_status()
            logger.debug("Webhook notification sent.")
            return True
        except Exception as exc:
            logger.warning("Webhook notification failed: %s", exc)
            return False


class TelegramNotifier(Notifier):
    """Sends notifications via Telegram Bot API."""

    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, title: str, message: str, level: str = "info") -> bool:
        emoji = {"info": "✅", "warning": "⚠️", "error": "❌"}.get(level, "ℹ️")
        text = f"{emoji} <b>{title}</b>\n{message}"
        try:
            resp = requests.post(
                self.API_URL.format(token=self.bot_token),
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                },
                timeout=10,
            )
            resp.raise_for_status()
            logger.debug("Telegram notification sent.")
            return True
        except Exception as exc:
            logger.warning("Telegram notification failed: %s", exc)
            return False


class EmailNotifier(Notifier):
    """Sends notifications via SMTP email."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        from_addr: str,
        password: str,
        to_addr: str,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_addr = from_addr
        self.password = password
        self.to_addr = to_addr

    def send(self, title: str, message: str, level: str = "info") -> bool:
        msg = MIMEText(message)
        msg["Subject"] = f"[Naukri Updater] {title}"
        msg["From"] = self.from_addr
        msg["To"] = self.to_addr

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_addr, self.password)
                server.sendmail(self.from_addr, [self.to_addr], msg.as_string())
            logger.debug("Email notification sent to %s.", self.to_addr)
            return True
        except Exception as exc:
            logger.warning("Email notification failed: %s", exc)
            return False


class NotificationManager:
    """
    Dispatches notifications to all configured backends.

    Automatically initializes available notifiers based on the Config.
    """

    def __init__(self, config: Config) -> None:
        self._notifiers: list[Notifier] = []
        self._setup(config)

    def _setup(self, config: Config) -> None:
        """Initialize notifiers based on available configuration."""
        if config.notify_webhook_url:
            self._notifiers.append(WebhookNotifier(config.notify_webhook_url))
            logger.info("Webhook notifications enabled.")

        if config.notify_telegram_bot_token and config.notify_telegram_chat_id:
            self._notifiers.append(
                TelegramNotifier(
                    config.notify_telegram_bot_token,
                    config.notify_telegram_chat_id,
                )
            )
            logger.info("Telegram notifications enabled.")

        if all(
            [
                config.notify_email_smtp_host,
                config.notify_email_from,
                config.notify_email_password,
                config.notify_email_to,
            ]
        ):
            self._notifiers.append(
                EmailNotifier(
                    smtp_host=config.notify_email_smtp_host,  # type: ignore[arg-type]
                    smtp_port=config.notify_email_smtp_port,
                    from_addr=config.notify_email_from,  # type: ignore[arg-type]
                    password=config.notify_email_password,  # type: ignore[arg-type]
                    to_addr=config.notify_email_to,  # type: ignore[arg-type]
                )
            )
            logger.info("Email notifications enabled.")

        if not self._notifiers:
            logger.debug(
                "No notification backends configured. "
                "Set NOTIFY_* env vars to enable."
            )

    @property
    def has_notifiers(self) -> bool:
        return len(self._notifiers) > 0

    def notify(self, title: str, message: str, level: str = "info") -> None:
        """Send a notification to all configured backends."""
        for notifier in self._notifiers:
            try:
                notifier.send(title, message, level)
            except Exception as exc:
                logger.warning(
                    "Notification backend %s failed: %s",
                    type(notifier).__name__,
                    exc,
                )

    def notify_success(self, message: str = "Profile updated.") -> None:
        self.notify("Profile Updated", message, level="info")

    def notify_failure(self, message: str) -> None:
        self.notify("Update Failed", message, level="error")

    def notify_recovery(self, message: str = "Updates resuming.") -> None:
        self.notify("Recovery", message, level="warning")
