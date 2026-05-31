"""Tests for authentication and session management."""

import json
import os
import time

import pytest

from naukri_updater.auth import is_session_valid


class TestSessionExpiry:

    def test_no_session_file(self, tmp_path):
        result = is_session_valid(str(tmp_path / "nonexistent.json"))
        assert result is False

    def test_session_without_meta_treated_as_valid(self, tmp_path):
        session_file = tmp_path / "session.json"
        session_file.write_text("{}")
        result = is_session_valid(str(session_file))
        assert result is True

    def test_fresh_session_is_valid(self, tmp_path):
        session_file = tmp_path / "session.json"
        session_file.write_text("{}")

        meta_file = tmp_path / "session.json.meta.json"
        meta = {"saved_at": time.time(), "version": 1}
        meta_file.write_text(json.dumps(meta))

        result = is_session_valid(str(session_file), max_age_hours=24)
        assert result is True

    def test_expired_session_is_invalid(self, tmp_path):
        session_file = tmp_path / "session.json"
        session_file.write_text("{}")

        meta_file = tmp_path / "session.json.meta.json"
        # Saved 48 hours ago.
        meta = {"saved_at": time.time() - 48 * 3600, "version": 1}
        meta_file.write_text(json.dumps(meta))

        result = is_session_valid(str(session_file), max_age_hours=24)
        assert result is False

    def test_corrupted_meta_treated_as_valid(self, tmp_path):
        session_file = tmp_path / "session.json"
        session_file.write_text("{}")

        meta_file = tmp_path / "session.json.meta.json"
        meta_file.write_text("not valid json{{{")

        result = is_session_valid(str(session_file))
        assert result is True

    def test_custom_max_age(self, tmp_path):
        session_file = tmp_path / "session.json"
        session_file.write_text("{}")

        meta_file = tmp_path / "session.json.meta.json"
        # Saved 2 hours ago.
        meta = {"saved_at": time.time() - 2 * 3600, "version": 1}
        meta_file.write_text(json.dumps(meta))

        # Valid with 4-hour window.
        assert is_session_valid(str(session_file), max_age_hours=4) is True
        # Invalid with 1-hour window.
        assert is_session_valid(str(session_file), max_age_hours=1) is False
