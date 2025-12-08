import json
import logging
import os
import sys
from typing import Any, Dict

REQUEST_ID_HEADER = "X-Request-ID"


class JsonFormatter(logging.Formatter):
    """Lightweight JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        log: Dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "time": self.formatTime(record, self.datefmt),
        }

        # Include standard extras if present
        for key in ("request_id", "path", "method", "status_code", "duration_ms", "client"):
            value = record.__dict__.get(key)
            if value is not None:
                log[key] = value

        # Attach exception info if any
        if record.exc_info:
            log["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log, ensure_ascii=False)


def configure_logging(level: str = None) -> None:
    """Configure root logging to JSON."""
    # Avoid duplicate handlers on reloads
    root = logging.getLogger()
    if root.handlers:
        return

    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root.setLevel(log_level)
    root.addHandler(handler)


def get_logger(name: str = "app") -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
