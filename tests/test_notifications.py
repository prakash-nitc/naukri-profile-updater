"""Tests for notification system."""

from unittest.mock import MagicMock, patch

import pytest

from naukri_updater.config import Config
from naukri_updater.notifications import (
    EmailNotifier,
    NotificationManager,
    TelegramNotifier,
    WebhookNotifier,
)


def _make_config(**overrides) -> Config:
    """Create a Config with test defaults."""
    defaults = {
        "email": "test@example.com",
        "password": "pass123",
    }
    defaults.update(overrides)
    return Config(**defaults)


class TestWebhookNotifier:

    @patch("naukri_updater.notifications.requests.post")
    def test_send_success(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()

        notifier = WebhookNotifier("https://hooks.example.com")
        result = notifier.send("Test", "Hello", "info")

        assert result is True
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        assert "Test" in payload["text"]
        assert "✅" in payload["text"]

    @patch("naukri_updater.notifications.requests.post")
    def test_send_error_level(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()

        notifier = WebhookNotifier("https://hooks.example.com")
        notifier.send("Failure", "Something broke", "error")

        payload = mock_post.call_args[1]["json"]
        assert "❌" in payload["text"]

    @patch("naukri_updater.notifications.requests.post")
    def test_send_failure_returns_false(self, mock_post):
        mock_post.side_effect = Exception("Network error")

        notifier = WebhookNotifier("https://hooks.example.com")
        result = notifier.send("Test", "Hello")

        assert result is False


class TestTelegramNotifier:

    @patch("naukri_updater.notifications.requests.post")
    def test_send_formats_html(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()

        notifier = TelegramNotifier("bot_token_123", "chat_456")
        notifier.send("Title", "Message", "info")

        payload = mock_post.call_args[1]["json"]
        assert payload["parse_mode"] == "HTML"
        assert "<b>Title</b>" in payload["text"]
        assert payload["chat_id"] == "chat_456"


class TestNotificationManager:

    def test_no_notifiers_when_unconfigured(self):
        config = _make_config()
        manager = NotificationManager(config)
        assert manager.has_notifiers is False

    def test_webhook_configured(self):
        config = _make_config(notify_webhook_url="https://hooks.example.com")
        manager = NotificationManager(config)
        assert manager.has_notifiers is True
        assert len(manager._notifiers) == 1
        assert isinstance(manager._notifiers[0], WebhookNotifier)

    def test_telegram_configured(self):
        config = _make_config(
            notify_telegram_bot_token="token",
            notify_telegram_chat_id="chatid",
        )
        manager = NotificationManager(config)
        assert manager.has_notifiers is True
        assert isinstance(manager._notifiers[0], TelegramNotifier)

    def test_email_requires_all_fields(self):
        # Missing to_addr — should not configure.
        config = _make_config(
            notify_email_smtp_host="smtp.example.com",
            notify_email_from="a@b.com",
            notify_email_password="pass",
        )
        manager = NotificationManager(config)
        assert manager.has_notifiers is False

    def test_multiple_notifiers(self):
        config = _make_config(
            notify_webhook_url="https://hooks.example.com",
            notify_telegram_bot_token="token",
            notify_telegram_chat_id="chatid",
        )
        manager = NotificationManager(config)
        assert len(manager._notifiers) == 2

    @patch("naukri_updater.notifications.requests.post")
    def test_notify_success_dispatches(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()

        config = _make_config(notify_webhook_url="https://hooks.example.com")
        manager = NotificationManager(config)
        manager.notify_success("All good")

        assert mock_post.called
