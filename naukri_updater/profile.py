"""
Profile update logic for Naukri Updater.

Contains all UI interaction functions for editing and saving profile
fields, including the name-rotation strategy.
"""

import random

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from naukri_updater.config import Config
from naukri_updater.logger import get_logger
from naukri_updater.selectors import PROFILE

logger = get_logger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Generic UI helpers
# ═════════════════════════════════════════════════════════════════════════════


def click_first_visible(
    scope: Page | Locator,
    selectors: tuple[str, ...],
    timeout: int = 1500,
) -> bool:
    """Click the first visible element matching any of the selectors."""
    for selector in selectors:
        try:
            element = scope.locator(selector).first
            if element.is_visible(timeout=timeout):
                element.scroll_into_view_if_needed(timeout=3000)
                try:
                    element.click(timeout=3000)
                except Exception:
                    # Fallback for sticky overlays or intercepted clicks.
                    element.evaluate("el => el.click()")
                logger.debug("Clicked element: %s", selector)
                return True
        except PlaywrightTimeoutError:
            continue
        except Exception:
            logger.debug("Click failed for selector: %s", selector)
            continue
    return False


def fill_first_visible_input(
    scope: Page | Locator,
    selectors: tuple[str, ...],
    value: str,
    timeout: int = 1200,
) -> bool:
    """Fill the first visible input field matching any of the selectors."""
    for selector in selectors:
        try:
            field = scope.locator(selector).first
            if field.is_visible(timeout=timeout):
                field.fill(value)
                actual = field.input_value().strip()
                if actual == value.strip():
                    logger.debug("Filled input: %s", selector)
                    return True
        except PlaywrightTimeoutError:
            continue
        except Exception:
            logger.debug("Fill failed for selector: %s", selector)
            continue
    return False


# ═════════════════════════════════════════════════════════════════════════════
# Save button interactions
# ═════════════════════════════════════════════════════════════════════════════


def click_save_if_visible(page: Page) -> bool:
    """Click a visible Save button directly on the page."""
    return click_first_visible(page, PROFILE.save_buttons, timeout=2000)


def click_modal_save_with_scroll(page: Page) -> bool:
    """
    Find and click a Save button inside a modal dialog.

    Scrolls the modal content up to 6 times to find buttons that may
    be below the fold.
    """
    for _ in range(6):
        if click_first_visible(page, PROFILE.modal_save_buttons):
            return True

        # Scroll inside the modal — save button may be below fold.
        try:
            page.evaluate(
                """() => {
                    const modal = document.querySelector(
                        '[role="dialog"], .modal, [class*="modal"]'
                    );
                    if (modal) modal.scrollTop = modal.scrollHeight;
                    window.scrollBy(0, 500);
                }"""
            )
        except Exception:
            pass
        page.wait_for_timeout(500)

    return False


def get_visible_edit_container(page: Page) -> Locator | None:
    """Find and return a visible edit dialog/modal/drawer container."""
    for selector in PROFILE.edit_containers:
        try:
            container = page.locator(selector).last
            if container.is_visible(timeout=1200):
                return container
        except Exception:
            continue
    return None


def click_save_in_container(page: Page, container: Locator) -> bool:
    """
    Find and click a Save button scoped to a specific container.

    Scrolls inside the container up to 6 times for below-fold buttons.
    """
    for _ in range(6):
        for selector in PROFILE.container_save_buttons:
            try:
                btn = container.locator(selector).first
                if btn.is_visible(timeout=800):
                    btn.scroll_into_view_if_needed(timeout=3000)
                    try:
                        btn.click(timeout=3000)
                    except Exception:
                        btn.evaluate("el => el.click()")
                    logger.debug("Clicked container save: %s", selector)
                    return True
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue

        # Scroll container to reveal more content.
        try:
            container.evaluate("el => { el.scrollTop = el.scrollHeight; }")
        except Exception:
            pass
        page.wait_for_timeout(400)

    return False


# ═════════════════════════════════════════════════════════════════════════════
# Personal details editing
# ═════════════════════════════════════════════════════════════════════════════


def click_personal_details_edit(page: Page) -> bool:
    """
    Find and click the Edit button for the Personal Details section.

    Uses a multi-strategy approach:
    1. Try precise selectors that target the Personal Details section directly.
    2. Try card-scoped selectors (find the card, then find Edit within it).
    3. Scroll the page and retry up to 10 times for lazy-loaded content.
    """
    # Scroll to top for deterministic search.
    try:
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(300)
    except Exception:
        pass

    for _ in range(10):
        # Strategy 1: Precise selectors.
        if click_first_visible(page, PROFILE.personal_details_edit, timeout=1000):
            return True

        # Strategy 2: Card-scoped edit controls.
        for heading in PROFILE.card_headings:
            card_selectors = [
                tpl.format(heading=heading) for tpl in PROFILE.card_containers
            ]
            for card_selector in card_selectors:
                try:
                    card = page.locator(card_selector).first
                    if not card.is_visible(timeout=500):
                        continue
                    for edit_selector in PROFILE.card_scoped_edit:
                        try:
                            edit_btn = card.locator(edit_selector).first
                            if edit_btn.is_visible(timeout=500):
                                edit_btn.scroll_into_view_if_needed(timeout=3000)
                                try:
                                    edit_btn.click(timeout=3000)
                                except Exception:
                                    edit_btn.evaluate("el => el.click()")
                                logger.info(
                                    "Clicked Personal Details edit: "
                                    "%s >> %s",
                                    card_selector,
                                    edit_selector,
                                )
                                return True
                        except Exception:
                            continue
                except Exception:
                    continue

        # Scroll down — the profile card may load lazily.
        try:
            page.evaluate("window.scrollBy(0, 450)")
        except Exception:
            pass
        page.wait_for_timeout(350)

    return False


def choose_target_name(page: Page, name_1: str, name_2: str) -> str:
    """
    Decide which name variant to switch to.

    Prefers the opposite of whichever variant is currently visible
    on the page. Falls back to random choice.
    """
    try:
        page_text = page.inner_text("body").lower()
        n1, n2 = name_1.lower(), name_2.lower()
        if n1 in page_text and n2 not in page_text:
            return name_2
        if n2 in page_text and n1 not in page_text:
            return name_1
    except Exception:
        pass
    return random.choice([name_1, name_2])


def update_name_randomly(page: Page, config: Config) -> bool:
    """
    Toggle the display name between two variants.

    This creates a profile change event that signals "freshness" to
    Naukri's ranking algorithm without changing meaningful content.
    """
    target_name = choose_target_name(
        page, config.name_variant_1, config.name_variant_2
    )
    logger.info("Updating name to: %s", target_name)

    # Enter edit mode for personal details.
    if not click_personal_details_edit(page):
        logger.warning("Could not click Personal Details edit control.")
        return False

    page.wait_for_timeout(1000)
    container = get_visible_edit_container(page)

    # Split into first/last name.
    if " " in target_name:
        first_name, last_name = target_name.split(" ", 1)
    else:
        first_name, last_name = target_name, ""

    updated = False
    scope = container if container is not None else page

    # Try dedicated first/last name fields.
    first_ok = fill_first_visible_input(scope, PROFILE.first_name, first_name)
    last_ok = fill_first_visible_input(scope, PROFILE.last_name, last_name)
    updated = first_ok or last_ok

    # Fallback: single full-name field.
    if not updated:
        updated = fill_first_visible_input(
            scope, PROFILE.full_name, target_name
        )

    if not updated:
        logger.warning("Could not find editable name fields.")
        return False

    # Save changes — try container first, then modal, then page-level.
    if (
        (container is not None and click_save_in_container(page, container))
        or click_modal_save_with_scroll(page)
        or click_save_if_visible(page)
    ):
        page.wait_for_timeout(1200)
        logger.info("Name update saved successfully.")
        return True

    logger.warning("Name was edited but Save button was not found.")
    return False


def touch_profile_save(page: Page) -> bool:
    """
    Trigger a profile refresh by opening any edit dialog and saving.

    This is the fallback strategy when name rotation is disabled or
    fails. It clicks any available Edit button and then saves.
    """
    logger.info("Trying to trigger profile refresh/save...")

    # Strategy 1: click a visible Save button directly.
    if click_save_if_visible(page):
        return True

    # Strategy 2: open any editable section and save.
    for edit_selector in PROFILE.generic_edit:
        try:
            edit_btn = page.locator(edit_selector).first
            if edit_btn.is_visible(timeout=1500):
                edit_btn.click(timeout=2500)
                page.wait_for_timeout(1000)
                if click_save_if_visible(page):
                    logger.info("Opened edit dialog and clicked Save.")
                    return True
        except Exception:
            continue

    return False


def update_profile(page: Page, config: Config) -> bool:
    """
    Main profile update orchestrator.

    Tries name rotation first (if enabled), then falls back to a
    generic profile touch/save.

    Returns:
        True if the profile was successfully updated, False otherwise.
    """
    success = False

    if config.random_name_update:
        success = update_name_randomly(page, config)

    if not success:
        success = touch_profile_save(page)

    if success:
        logger.info("Profile update completed successfully.")
    else:
        logger.error(
            "Could not update profile automatically. "
            "Run with HEADLESS=false to inspect selectors."
        )

    return success
