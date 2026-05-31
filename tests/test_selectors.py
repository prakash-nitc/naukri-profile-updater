"""Tests for centralized selectors."""

from naukri_updater.selectors import COOKIE, LOGIN, PROFILE


class TestSelectorGroups:
    """Verify selector groups are non-empty and well-formed."""

    def test_login_email_selectors_exist(self):
        assert len(LOGIN.email) > 0
        for s in LOGIN.email:
            assert isinstance(s, str)
            assert len(s) > 0

    def test_login_password_selectors_exist(self):
        assert len(LOGIN.password) > 0

    def test_login_submit_selectors_exist(self):
        assert len(LOGIN.submit) > 0

    def test_cookie_selectors_exist(self):
        assert len(COOKIE.accept_buttons) > 0

    def test_profile_save_selectors_exist(self):
        assert len(PROFILE.save_buttons) > 0

    def test_profile_edit_selectors_exist(self):
        assert len(PROFILE.personal_details_edit) > 0
        assert len(PROFILE.generic_edit) > 0

    def test_name_field_selectors_exist(self):
        assert len(PROFILE.first_name) > 0
        assert len(PROFILE.last_name) > 0
        assert len(PROFILE.full_name) > 0

    def test_card_containers_have_placeholder(self):
        """Ensure card container templates use {heading} placeholder."""
        for tpl in PROFILE.card_containers:
            assert "{heading}" in tpl

    def test_no_duplicate_selectors_in_login(self):
        assert len(LOGIN.email) == len(set(LOGIN.email))
        assert len(LOGIN.password) == len(set(LOGIN.password))
        assert len(LOGIN.submit) == len(set(LOGIN.submit))
