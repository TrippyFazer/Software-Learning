"""Structured JSON logging.

One log line per event, machine-parseable, safe by construction: nothing in
this module ever logs credentials or session tokens (and the auth module
never passes them in).
"""

import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Extra structured fields attached via logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key in ("request_id", "path", "method", "status", "duration_ms", "user_id", "event"):
                entry[key] = value
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # uvicorn's default access log is redundant with our request middleware
    logging.getLogger("uvicorn.access").disabled = True
