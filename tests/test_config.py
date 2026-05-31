"""Tests for configuration loading and validation."""

import os

import pytest

from naukri_updater.config import Config, as_bool, load_config


class TestAsBool:
    """Tests for the as_bool helper."""

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("y", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("random", False),
            ("", False),
        ],
    )
    def test_string_values(self, value: str, expected: bool):
        assert as_bool(value) == expected

    def test_none_returns_default_true(self):
        assert as_bool(None, default=True) is True

    def test_none_returns_default_false(self):
        assert as_bool(None, default=False) is False

    def test_whitespace_stripped(self):
        assert as_bool("  true  ") is True
        assert as_bool("  false  ") is False


class TestLoadConfig:
    """Tests for load_config validation."""

    def test_missing_email_raises(self, monkeypatch):
        monkeypatch.setenv("NAUKRI_PASSWORD", "pass123")
        with pytest.raises(ValueError, match="NAUKRI_EMAIL"):
            load_config()

    def test_missing_password_raises(self, monkeypatch):
        monkeypatch.setenv("NAUKRI_EMAIL", "test@example.com")
        with pytest.raises(ValueError, match="NAUKRI_EMAIL"):
            load_config()

    def test_both_schedule_options_raises(self, monkeypatch):
        monkeypatch.setenv("NAUKRI_EMAIL", "test@example.com")
        monkeypatch.setenv("NAUKRI_PASSWORD", "pass123")
        monkeypatch.setenv("UPDATE_EVERY_MINUTES", "60")
        monkeypatch.setenv("UPDATE_AT_HHMM", "09:30")
        with pytest.raises(ValueError, match="only ONE"):
            load_config()

    def test_valid_minimal_config(self, monkeypatch):
        monkeypatch.setenv("NAUKRI_EMAIL", "test@example.com")
        monkeypatch.setenv("NAUKRI_PASSWORD", "pass123")
        config = load_config()
        assert config.email == "test@example.com"
        assert config.password == "pass123"
        assert config.every_minutes == "240"  # Default
        assert config.update_at is None

    def test_name_rotation_requires_variants(self, monkeypatch):
        monkeypatch.setenv("NAUKRI_EMAIL", "test@example.com")
        monkeypatch.setenv("NAUKRI_PASSWORD", "pass123")
        monkeypatch.setenv("ENABLE_RANDOM_NAME_UPDATE", "true")
        with pytest.raises(ValueError, match="NAME_VARIANT"):
            load_config()

    def test_name_rotation_with_variants(self, monkeypatch):
        monkeypatch.setenv("NAUKRI_EMAIL", "test@example.com")
        monkeypatch.setenv("NAUKRI_PASSWORD", "pass123")
        monkeypatch.setenv("ENABLE_RANDOM_NAME_UPDATE", "true")
        monkeypatch.setenv("NAME_VARIANT_1", "John Doe")
        monkeypatch.setenv("NAME_VARIANT_2", "John doe")
        config = load_config()
        assert config.random_name_update is True
        assert config.name_variant_1 == "John Doe"
        assert config.name_variant_2 == "John doe"

    def test_custom_schedule_minutes(self, monkeypatch):
        monkeypatch.setenv("NAUKRI_EMAIL", "test@example.com")
        monkeypatch.setenv("NAUKRI_PASSWORD", "pass123")
        monkeypatch.setenv("UPDATE_EVERY_MINUTES", "120")
        config = load_config()
        assert config.every_minutes == "120"
        assert config.update_at is None

    def test_custom_schedule_time(self, monkeypatch):
        monkeypatch.setenv("NAUKRI_EMAIL", "test@example.com")
        monkeypatch.setenv("NAUKRI_PASSWORD", "pass123")
        monkeypatch.setenv("UPDATE_AT_HHMM", "14:00")
        config = load_config()
        assert config.every_minutes is None
        assert config.update_at == "14:00"

    def test_config_is_immutable(self, monkeypatch):
        monkeypatch.setenv("NAUKRI_EMAIL", "test@example.com")
        monkeypatch.setenv("NAUKRI_PASSWORD", "pass123")
        config = load_config()
        with pytest.raises(AttributeError):
            config.email = "changed"  # type: ignore[misc]

    def test_notification_config(self, monkeypatch):
        monkeypatch.setenv("NAUKRI_EMAIL", "test@example.com")
        monkeypatch.setenv("NAUKRI_PASSWORD", "pass123")
        monkeypatch.setenv("NOTIFY_WEBHOOK_URL", "https://hooks.example.com")
        monkeypatch.setenv("NOTIFY_TELEGRAM_BOT_TOKEN", "bot123")
        monkeypatch.setenv("NOTIFY_TELEGRAM_CHAT_ID", "chat456")
        config = load_config()
        assert config.notify_webhook_url == "https://hooks.example.com"
        assert config.notify_telegram_bot_token == "bot123"
        assert config.notify_telegram_chat_id == "chat456"
