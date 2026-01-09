"""Shared logging utilities for CLI and Web interfaces.

This module does not configure OTLP log exporting.
It enriches standard Python logs with trace/span ids for correlation.

OTLP exporting of standard Python logs is configured via Agent Framework
observability (see `src/shared/tracing.py`).
"""

import logging
import sys
from typing import Optional

try:
    from opentelemetry.trace import get_current_span
except Exception:  # pragma: no cover - optional dependency
    get_current_span = None


_LOGGING_CONFIGURED = False


class TraceContextFilter(logging.Filter):
    """Attach trace/span ids to records so they can be correlated across sinks."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        if get_current_span is None:
            record.trace_id = "-"
            record.span_id = "-"
            return True

        try:
            span = get_current_span()
            span_context = span.get_span_context()

            if span_context and span_context.is_valid:
                record.trace_id = format(span_context.trace_id, "032x")
                record.span_id = format(span_context.span_id, "016x")
            else:
                record.trace_id = "-"
                record.span_id = "-"
        except Exception:
            record.trace_id = "-"
            record.span_id = "-"

        return True

def setup_logging(
    name: str = "pricing_assistant",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    service_name: Optional[str] = None,
) -> logging.Logger:
    """Configure standard logging with trace/span correlation fields."""

    global _LOGGING_CONFIGURED

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if _LOGGING_CONFIGURED:
        return logger

    _ = service_name or name
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    trace_filter = TraceContextFilter()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s "
        "[trace_id=%(trace_id)s span_id=%(span_id)s]"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(trace_filter)
    root_logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(trace_filter)
        root_logger.addHandler(file_handler)

    _LOGGING_CONFIGURED = True
    return logger
