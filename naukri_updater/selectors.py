"""
Centralized CSS selectors for Naukri.com.

All selectors used for interacting with the Naukri UI are defined here
in one place. When Naukri updates their markup, you only need to edit
this file instead of hunting through multiple modules.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LoginSelectors:
    """Selectors for the login page."""

    email: tuple[str, ...] = (
        "input[placeholder*='Email']",
        "input[placeholder*='Username']",
        "input[name='usernameField']",
        "input[id='usernameField']",
        "input[name*='user']",
        "input[id*='user']",
        "input[type='email']",
        "input[autocomplete='username']",
    )

    password: tuple[str, ...] = (
        "input[placeholder*='password']",
        "input[type='password']",
        "input[name*='password']",
        "input[id='passwordField']",
        "input[id*='pass']",
        "input[autocomplete='current-password']",
    )

    submit: tuple[str, ...] = (
        "button[type='submit']",
        "button:has-text('Login')",
        "button:has-text('Sign in')",
        "button:has-text('Continue')",
        "input[type='submit']",
    )

    login_openers: tuple[str, ...] = (
        "a:has-text('Login')",
        "button:has-text('Login')",
        "a[href*='nlogin']",
        "[title*='Login']",
    )


@dataclass(frozen=True)
class CookieSelectors:
    """Selectors for cookie consent banners."""

    accept_buttons: tuple[str, ...] = (
        "button:has-text('Accept')",
        "button:has-text('I Accept')",
        "button:has-text('Got it')",
        "button:has-text('Allow All')",
    )


@dataclass(frozen=True)
class ProfileSelectors:
    """Selectors for profile page interactions."""

    # ── Save buttons ─────────────────────────────────────────────────────
    save_buttons: tuple[str, ...] = (
        "button:has-text('Save')",
        "button:has-text('Save changes')",
        "input[value='Save']",
        "button[class*='save']",
        "button[data-ga-track*='save']",
        "button[type='submit']",
    )

    modal_save_buttons: tuple[str, ...] = (
        "[role='dialog'] button:has-text('Save')",
        "[role='dialog'] button:has-text('Save changes')",
        ".modal button:has-text('Save')",
        "[class*='modal'] button:has-text('Save')",
    )

    container_save_buttons: tuple[str, ...] = (
        "button:has-text('Save')",
        "button:has-text('Save changes')",
        "button:has-text('Update')",
        "button[type='submit']",
        "input[type='submit']",
        "[role='button']:has-text('Save')",
        "[role='button']:has-text('Update')",
    )

    # ── Edit controls (pencil icons) ─────────────────────────────────────
    # Naukri uses span.new-pencil icons inside headings, not text buttons.
    generic_edit: tuple[str, ...] = (
        "span.new-pencil",
        "button:has-text('Edit')",
        "a:has-text('Edit')",
        "[class*='edit']",
        "[data-ga-track*='edit']",
    )

    # Direct selectors to click the pencil icon on the name / personal
    # details section.  The h1 with data-id="name" contains the pencil.
    personal_details_edit: tuple[str, ...] = (
        "h1[data-id='name'] span.new-pencil",
        ".personal-details span.new-pencil",
        ".user-basic-summary-container span.new-pencil",
        "[data-id='name'] span.new-pencil",
        ".personal-details [class*='pencil']",
        "section:has-text('Personal details') span.new-pencil",
        "div:has-text('Personal details') span.new-pencil",
        "section:has-text('Basic details') span.new-pencil",
        "div:has-text('Basic details') span.new-pencil",
        "section:has-text('Personal details') button:has-text('Edit')",
        "div:has-text('Personal Details') button:has-text('Edit')",
        "div:has-text('Name') button:has-text('Edit')",
        "[data-ga-track*='personal'] [class*='edit']",
    )

    card_headings: tuple[str, ...] = (
        "Personal details",
        "Personal Details",
        "Name",
        "Basic details",
        "Basic Details",
    )

    card_scoped_edit: tuple[str, ...] = (
        "span.new-pencil",
        "button:has-text('Edit')",
        "a:has-text('Edit')",
        "button[aria-label*='Edit']",
        "[role='button'][aria-label*='Edit']",
        "[class*='edit'][role='button']",
        "[class*='icon'][class*='edit']",
        "[class*='pencil']",
    )

    card_containers: tuple[str, ...] = (
        "section:has-text('{heading}')",
        "div:has-text('{heading}')",
        "article:has-text('{heading}')",
    )

    # ── Edit containers / modals / drawers ───────────────────────────────
    edit_containers: tuple[str, ...] = (
        "form#editBasicDetailsForm",
        ".basic-details-component",
        "[class*='drawer']",
        "[role='dialog']",
        ".modal",
        "[class*='modal']",
        "[class*='popup']",
    )

    # ── Name fields ──────────────────────────────────────────────────────
    # Inside the editBasicDetailsForm, the name is a single text input.
    first_name: tuple[str, ...] = (
        "input[aria-label*='First']",
        "input[name*='first']",
        "input[id*='first']",
        "input[placeholder*='First']",
    )

    last_name: tuple[str, ...] = (
        "input[aria-label*='Last']",
        "input[name*='last']",
        "input[id*='last']",
        "input[placeholder*='Last']",
    )

    full_name: tuple[str, ...] = (
        "#editBasicDetailsForm input[type='text']",
        ".basic-details-component input[type='text']",
        "input[aria-label='Name']",
        "input[aria-label*='Full']",
        "input[name='name']",
        "input[name*='fullName']",
        "input[id='name']",
        "input[placeholder*='Name']",
        "input[placeholder*='name']",
    )


# ── Singleton instances ──────────────────────────────────────────────────────
LOGIN = LoginSelectors()
COOKIE = CookieSelectors()
PROFILE = ProfileSelectors()
