"""
Web dashboard for Naukri Profile Auto-Updater.

Provides a browser-based UI to configure, start/stop, and monitor
the profile updater without touching the terminal.
"""

import collections
import logging
import os
import threading
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv, set_key
from flask import Flask, jsonify, render_template, request

# ── App state ────────────────────────────────────────────────────────────────

_updater_thread: threading.Thread | None = None
_updater_stop = threading.Event()
_status = {
    "running": False,
    "last_update": None,
    "last_result": None,
    "consecutive_failures": 0,
    "started_at": None,
    "total_updates": 0,
    "schedule": None,
    "next_run": None,
}
_log_buffer: collections.deque = collections.deque(maxlen=200)

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")


# ── Log capture ──────────────────────────────────────────────────────────────

class DashboardLogHandler(logging.Handler):
    """Captures log records into the in-memory ring buffer."""

    def emit(self, record):
        try:
            msg = self.format(record)
            _log_buffer.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "level": record.levelname,
                "message": msg,
            })
        except Exception:
            pass


def _install_log_handler():
    """Install our handler on the root naukri_updater logger."""
    handler = DashboardLogHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    # Capture from the naukri_updater namespace
    for name in ("naukri_updater",):
        logger = logging.getLogger(name)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)


# ── Scheduling helpers ───────────────────────────────────────────────────────

def _seconds_until_daily(hhmm: str) -> float:
    """Seconds from now until the next occurrence of HH:MM (today or tomorrow)."""
    now = datetime.now()
    hour, minute = (int(p) for p in hhmm.split(":"))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def _next_wait_seconds(config) -> float:
    """
    Compute how long to sleep before the next update.

    Daily mode (UPDATE_AT_HHMM) takes precedence; otherwise fall back to the
    interval in minutes (default 240).
    """
    if config.update_at:
        return _seconds_until_daily(config.update_at)
    interval_min = int(config.every_minutes) if config.every_minutes else 240
    return interval_min * 60


# ── Updater thread ───────────────────────────────────────────────────────────

def _run_updater():
    """Background thread that runs the update loop."""
    global _status
    _status["running"] = True
    _status["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        load_dotenv(ENV_PATH, override=True)
        from naukri_updater.config import load_config
        from naukri_updater.logger import setup_logging

        config = load_config()
        setup_logging(config.log_level, config.log_file)
        _install_log_handler()

        from playwright.sync_api import sync_playwright
        from naukri_updater.auth import (
            has_profile_access,
            is_session_valid,
            login_and_save_session,
        )
        from naukri_updater.browser import launch_browser
        from naukri_updater.profile import update_profile

        logger = logging.getLogger("naukri_updater")
        if config.update_at:
            _status["schedule"] = f"Daily at {config.update_at}"
            logger.info("Dashboard: updater started (daily at %s).", config.update_at)
        else:
            interval_min = int(config.every_minutes) if config.every_minutes else 240
            _status["schedule"] = f"Every {interval_min} min"
            logger.info("Dashboard: updater started (every %d min).", interval_min)

        def _do_single_update():
            """Execute one update cycle."""
            with sync_playwright() as pw:
                # Login if needed
                if not is_session_valid(config.session_file, config.session_max_age_hours):
                    logger.info("Session missing or expired — logging in...")
                    login_and_save_session(pw, config)

                # Open profile with saved session
                logger.info("Launching browser with saved session...")
                browser, context, page = launch_browser(pw, config.session_file)
                try:
                    if not has_profile_access(page, config.profile_url):
                        logger.info("Session invalid — re-logging in...")
                        context.close()
                        browser.close()
                        login_and_save_session(pw, config)
                        browser, context, page = launch_browser(pw, config.session_file)
                        if not has_profile_access(page, config.profile_url):
                            raise RuntimeError(
                                "Could not access profile after re-login. "
                                "Check credentials or anti-bot restrictions."
                            )

                    return update_profile(page, config)
                finally:
                    context.close()
                    browser.close()

        def _run_once_and_record():
            """Run a single update and update the shared status dict."""
            try:
                success = _do_single_update()
                _status["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                _status["last_result"] = "success" if success else "partial"
                _status["total_updates"] += 1
                _status["consecutive_failures"] = (
                    0 if success else _status["consecutive_failures"] + 1
                )
            except Exception as e:
                logger.error("Update failed: %s", e)
                _status["last_result"] = "error"
                _status["consecutive_failures"] += 1

        # First run immediately.
        _run_once_and_record()

        # Schedule loop — recompute the wait each cycle so daily-time mode
        # always targets the next HH:MM occurrence.
        while True:
            wait_sec = _next_wait_seconds(config)
            _status["next_run"] = (
                datetime.now() + timedelta(seconds=wait_sec)
            ).strftime("%Y-%m-%d %H:%M:%S")
            if _updater_stop.wait(timeout=wait_sec):
                break
            _run_once_and_record()

    except Exception as e:
        _log_buffer.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "level": "ERROR",
            "message": f"Updater crashed: {e}",
        })
    finally:
        _status["running"] = False
        _status["next_run"] = None


# ── Config helpers ───────────────────────────────────────────────────────────

ENV_KEYS = [
    "NAUKRI_EMAIL", "NAUKRI_PASSWORD",
    "UPDATE_EVERY_MINUTES", "UPDATE_AT_HHMM",
    "HEADLESS", "ENABLE_RANDOM_NAME_UPDATE",
    "NAME_VARIANT_1", "NAME_VARIANT_2",
    "SESSION_MAX_AGE_HOURS", "MAX_RETRIES",
    "LOG_LEVEL", "LOG_FILE",
    "NOTIFY_WEBHOOK_URL",
    "NOTIFY_TELEGRAM_BOT_TOKEN", "NOTIFY_TELEGRAM_CHAT_ID",
    "NOTIFY_EMAIL_SMTP_HOST", "NOTIFY_EMAIL_SMTP_PORT",
    "NOTIFY_EMAIL_FROM", "NOTIFY_EMAIL_PASSWORD", "NOTIFY_EMAIL_TO",
]


def _read_config():
    """Read current .env values."""
    load_dotenv(ENV_PATH, override=True)
    config = {}
    for key in ENV_KEYS:
        val = os.environ.get(key, "")
        # Mask password
        if "PASSWORD" in key and val:
            config[key] = "•" * min(len(val), 12)
        else:
            config[key] = val
    return config


def _write_config(data: dict):
    """Write values to .env file."""
    for key, value in data.items():
        if key in ENV_KEYS:
            # Don't overwrite password if masked
            if "PASSWORD" in key and "•" in value:
                continue
            if value:
                set_key(ENV_PATH, key, value)
            else:
                # Remove the key if empty
                set_key(ENV_PATH, key, "")


# ── Flask app ────────────────────────────────────────────────────────────────

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    return jsonify(_status)


@app.route("/api/config", methods=["GET"])
def api_config_get():
    return jsonify(_read_config())


@app.route("/api/config", methods=["POST"])
def api_config_set():
    data = request.get_json(force=True)
    _write_config(data)
    return jsonify({"ok": True})


@app.route("/api/start", methods=["POST"])
def api_start():
    global _updater_thread
    if _status["running"]:
        return jsonify({"ok": False, "error": "Already running"})

    _updater_stop.clear()
    _updater_thread = threading.Thread(target=_run_updater, daemon=True)
    _updater_thread.start()
    return jsonify({"ok": True})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    if not _status["running"]:
        return jsonify({"ok": False, "error": "Not running"})

    _updater_stop.set()
    _status["running"] = False
    _log_buffer.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "level": "INFO",
        "message": "Updater stopped by user.",
    })
    return jsonify({"ok": True})


@app.route("/api/logs")
def api_logs():
    return jsonify(list(_log_buffer))


def run_dashboard(port=5000):
    """Entry point for the dashboard."""
    print(f"\n  Dashboard running at: http://localhost:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
