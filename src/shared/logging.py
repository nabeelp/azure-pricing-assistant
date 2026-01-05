"""Shared logging utilities for CLI and Web interfaces."""

import logging
import os
import sys
from typing import Dict, Optional

try:
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import (
        BatchLogRecordProcessor,
        OTLPLogExporter,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import get_current_span
except Exception:  # pragma: no cover - optional dependency
    set_logger_provider = None
    LoggerProvider = None
    LoggingHandler = None
    BatchLogRecordProcessor = None
    OTLPLogExporter = None
    Resource = None
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


def _parse_headers(raw_headers: Optional[str]) -> Dict[str, str]:
    headers: Dict[str, str] = {}

    if not raw_headers:
        return headers

    for pair in raw_headers.split(","):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        headers[key.strip()] = value.strip()

    return headers


def _build_otel_handler(
    service_name: str, level: int
) -> Optional[logging.Handler]:
    """Create an OTLP logging handler if OpenTelemetry is available."""

    otel_deps_available = all(
        [
            set_logger_provider,
            LoggerProvider,
            LoggingHandler,
            BatchLogRecordProcessor,
            OTLPLogExporter,
            Resource,
        ]
    )

    if not otel_deps_available:
        return None

    endpoint = os.getenv("OTLP_ENDPOINT") or os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT"
    )

    if not endpoint:
        return None

    headers = _parse_headers(
        os.getenv("OTLP_HEADERS") or os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
    )
    insecure = endpoint.startswith("http://")

    try:
        resource = Resource.create({"service.name": service_name})
        provider = LoggerProvider(resource=resource)
        processor = BatchLogRecordProcessor(
            OTLPLogExporter(endpoint=endpoint, headers=headers, insecure=insecure)
        )
        provider.add_log_record_processor(processor)
        set_logger_provider(provider)

        handler = LoggingHandler(logger_provider=provider, level=level)
        handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
        return handler
    except Exception as exc:  # pragma: no cover - defensive fallback
        sys.stderr.write(
            f"Failed to initialize OpenTelemetry logging exporter: {exc}\n"
        )
        return None


def setup_logging(
    name: str = "pricing_assistant",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    service_name: Optional[str] = None,
) -> logging.Logger:
    """Configure standard logging and (if available) OpenTelemetry export."""

    global _LOGGING_CONFIGURED

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if _LOGGING_CONFIGURED:
        return logger

    resolved_service_name = service_name or name
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

    otel_handler = _build_otel_handler(resolved_service_name, level)
    if otel_handler:
        otel_handler.addFilter(trace_filter)
        root_logger.addHandler(otel_handler)

    _LOGGING_CONFIGURED = True
    return logger
