from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonLogFormatter(logging.Formatter):
    """Structured JSON formatter for application logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field_name in (
            "request_id",
            "correlation_id",
            "trace_id",
            "tenant_id",
            "user_id",
            "path",
            "method",
            "status_code",
            "latency_ms",
        ):
            value = getattr(record, field_name, None)
            if value is not None:
                payload[field_name] = value

        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_structured_logging(log_level: str = "INFO") -> None:
    """Configure root logger to emit JSON logs."""
    root = logging.getLogger()
    root.setLevel(log_level.upper())

    for handler in list(root.handlers):
        root.removeHandler(handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JsonLogFormatter())
    root.addHandler(stream_handler)
