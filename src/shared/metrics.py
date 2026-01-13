"""OpenTelemetry metrics for Azure Pricing Assistant.

This module provides metrics counters for monitoring application behavior:
- chat_turns_total: Count of chat turn requests
- proposals_generated_total: Count of completed proposal generations
- errors_total: Count of errors by type

Metrics are exported to OTLP endpoint when ENABLE_OTEL=true.
"""

from __future__ import annotations

import logging
from typing import Optional

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

logger = logging.getLogger(__name__)

_METRICS_CONFIGURED = False
_meter: Optional[metrics.Meter] = None
_chat_turns_counter = None
_proposals_counter = None
_errors_counter = None


def configure_metrics() -> None:
    """Configure OpenTelemetry metrics with OTLP exporter."""
    global _METRICS_CONFIGURED, _meter, _chat_turns_counter, _proposals_counter, _errors_counter

    if _METRICS_CONFIGURED:
        return

    import os

    enable_otel = os.getenv("ENABLE_OTEL", "").lower() == "true"
    if not enable_otel:
        logger.debug("Metrics disabled (ENABLE_OTEL not set to true)")
        _METRICS_CONFIGURED = True
        return

    try:
        # Configure OTLP metric exporter
        otlp_endpoint = os.getenv("OTLP_ENDPOINT") or os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
        )

        # Strip trailing slash and ensure proper format
        otlp_endpoint = otlp_endpoint.rstrip("/")
        if not otlp_endpoint.startswith("http://") and not otlp_endpoint.startswith("https://"):
            otlp_endpoint = f"http://{otlp_endpoint}"

        logger.info(f"Configuring metrics export to OTLP endpoint: {otlp_endpoint}")

        # Create OTLP exporter
        exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)

        # Create metric reader with periodic export
        reader = PeriodicExportingMetricReader(exporter, export_interval_millis=5000)

        # Create meter provider
        provider = MeterProvider(metric_readers=[reader])
        metrics.set_meter_provider(provider)

        # Create meter
        _meter = metrics.get_meter("azure_pricing_assistant")

        # Create counters
        _chat_turns_counter = _meter.create_counter(
            name="chat_turns_total",
            description="Total number of chat turn requests processed",
            unit="1",
        )

        _proposals_counter = _meter.create_counter(
            name="proposals_generated_total",
            description="Total number of proposals successfully generated",
            unit="1",
        )

        _errors_counter = _meter.create_counter(
            name="errors_total",
            description="Total number of errors by type",
            unit="1",
        )

        logger.info("OpenTelemetry metrics configured successfully")
        _METRICS_CONFIGURED = True

    except Exception as e:
        logger.warning(f"Failed to configure metrics: {e}")
        _METRICS_CONFIGURED = True


def increment_chat_turns(session_id: str) -> None:
    """
    Increment chat turns counter.

    Args:
        session_id: Session identifier for attribution
    """
    if _chat_turns_counter:
        _chat_turns_counter.add(1, {"session_id": session_id})


def increment_proposals_generated(session_id: str, success: bool = True) -> None:
    """
    Increment proposals generated counter.

    Args:
        session_id: Session identifier for attribution
        success: Whether proposal generation succeeded
    """
    if _proposals_counter:
        _proposals_counter.add(1, {"session_id": session_id, "success": str(success)})


def increment_errors(error_type: str, session_id: Optional[str] = None) -> None:
    """
    Increment errors counter.

    Args:
        error_type: Type/category of error (e.g., 'validation_error', 'mcp_timeout', 'agent_failure')
        session_id: Optional session identifier for attribution
    """
    if _errors_counter:
        attributes = {"error_type": error_type}
        if session_id:
            attributes["session_id"] = session_id
        _errors_counter.add(1, attributes)
