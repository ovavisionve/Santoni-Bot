import logging
import sys
import json
from datetime import datetime, timezone

from app.config import get_settings


class JSONFormatter(logging.Formatter):
    """Structured JSON logging for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)

        # Extra fields
        for key in ("user_id", "agent", "department", "action", "duration_ms", "status_code"):
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging() -> logging.Logger:
    """Configure app-wide logging."""
    settings = get_settings()
    logger = logging.getLogger("santonibot")

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    if settings.app_env == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        )

    logger.addHandler(handler)
    logger.propagate = False

    return logger


def get_logger(name: str = "santonibot") -> logging.Logger:
    """Get a child logger."""
    parent = logging.getLogger("santonibot")
    if not parent.handlers:
        setup_logging()
    return logging.getLogger(f"santonibot.{name}")
