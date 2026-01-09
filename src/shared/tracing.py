"""Tracing/observability setup utilities.

This repo relies on Agent Framework to create spans for agent/chat operations.

We use Agent Framework's `setup_observability()` so OTLP export includes:
- traces (including agent spans)
- standard Python logs (via an OpenTelemetry LoggingHandler)

We still keep our own console/file logging handlers for local readability.
"""

from __future__ import annotations

import os
from agent_framework.observability import setup_observability


_OBSERVABILITY_CONFIGURED = False


def configure_tracing(service_name: str) -> None:
    """Configure Agent Framework observability.

    Uses Agent Framework's OpenTelemetry setup so OTLP export includes both
    traces and standard Python logs.
    """

    global _OBSERVABILITY_CONFIGURED
    if _OBSERVABILITY_CONFIGURED:
        return

    # Ensure the service name is set for OTel Resource.
    if not os.getenv("OTEL_SERVICE_NAME"):
        os.environ["OTEL_SERVICE_NAME"] = service_name

    # setup_observability reads ENABLE_OTEL + OTLP_ENDPOINT from environment.
    # We call it unconditionally; it will be a no-op if observability is disabled.
    setup_observability()
    _OBSERVABILITY_CONFIGURED = True
