"""Entry point for `python -m naukri_updater`."""

from naukri_updater.config import load_config
from naukri_updater.logger import get_logger, setup_logging
from naukri_updater.scheduler import start_scheduler

logger = get_logger(__name__)


def main() -> None:
    try:
        config = load_config()
        setup_logging(level=config.log_level, log_file=config.log_file)

        logger.info("Naukri Profile Auto-Updater v1.0.0 starting...")
        start_scheduler(config)

    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
    except Exception as exc:
        logger.error("Unexpected error: %s", exc)


if __name__ == "__main__":
    main()
