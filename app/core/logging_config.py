from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGS_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_FILE_PATH = LOGS_DIR / "app.log"


class ContextDefaultsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for field, default in (
            ("telegram_user_id", "-"),
            ("submission_id", "-"),
            ("state", "-"),
            ("step", "-"),
            ("attempt", "-"),
            ("duration_ms", "-"),
            ("success", "-"),
        ):
            if not hasattr(record, field):
                setattr(record, field, default)
        return True


def configure_logging(log_level: str) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter(
            fmt=(
                "%(asctime)s %(levelname)s %(name)s "
                "telegram_user_id=%(telegram_user_id)s submission_id=%(submission_id)s "
                "state=%(state)s step=%(step)s attempt=%(attempt)s "
                "duration_ms=%(duration_ms)s success=%(success)s %(message)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    file_handler = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter(
            fmt=(
                "%(asctime)s.%(msecs)03d %(levelname)s %(name)s "
                "pid=%(process)d thread=%(threadName)s "
                "file=%(pathname)s:%(lineno)d "
                "telegram_user_id=%(telegram_user_id)s submission_id=%(submission_id)s "
                "state=%(state)s step=%(step)s attempt=%(attempt)s "
                "duration_ms=%(duration_ms)s success=%(success)s %(message)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    if not any(
        isinstance(existing_filter, ContextDefaultsFilter)
        for existing_filter in root_logger.filters
    ):
        root_logger.addFilter(ContextDefaultsFilter())
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    for handler in root_logger.handlers:
        if not any(
            isinstance(existing_filter, ContextDefaultsFilter)
            for existing_filter in handler.filters
        ):
            handler.addFilter(ContextDefaultsFilter())
