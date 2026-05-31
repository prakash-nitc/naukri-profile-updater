"""
Logging configuration for Naukri Updater.

Provides colored console output and optional file logging,
replacing the original project's bare print() calls with
Python's standard logging module.
"""

import logging
import os
import sys
from typing import Optional


# ── ANSI color codes for console output ──────────────────────────────────────
class _Colors:
    RESET = "\033[0m"
    GRAY = "\033[90m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD_RED = "\033[1;91m"
    CYAN = "\033[96m"

    LEVEL_MAP = {
        logging.DEBUG: GRAY,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED,
    }


class ColoredFormatter(logging.Formatter):
    """Formatter that adds ANSI colors to log level names in the console."""

    BASE_FMT = "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s"
    DATE_FMT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, use_colors: bool = True) -> None:
        super().__init__(fmt=self.BASE_FMT, datefmt=self.DATE_FMT)
        self._use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        if self._use_colors:
            color = _Colors.LEVEL_MAP.get(record.levelno, _Colors.RESET)
            record.levelname = f"{color}{record.levelname}{_Colors.RESET}"
            record.name = f"{_Colors.CYAN}{record.name}{_Colors.RESET}"
        return super().format(record)


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure the root logger for the naukri_updater package.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR). Defaults to
               the LOG_LEVEL env var, or INFO if not set.
        log_file: Optional path to a log file. Defaults to LOG_FILE env var.
    """
    level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    log_file = log_file or os.getenv("LOG_FILE")
    numeric_level = getattr(logging, level, logging.INFO)

    root_logger = logging.getLogger("naukri_updater")
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers on repeated calls.
    root_logger.handlers.clear()

    # ── Console handler (colored) ────────────────────────────────────────
    use_colors = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter(use_colors=use_colors))
    root_logger.addHandler(console_handler)

    # ── File handler (plain text) ────────────────────────────────────────
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter(
                fmt="[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger under the naukri_updater namespace.

    Usage:
        from naukri_updater.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    return logging.getLogger(f"naukri_updater.{name}")
