"""Web session-level tracing helpers.

Creates a long-lived OpenTelemetry span per logical user session so that all
logs and traces within that session share the same trace context (trace_id/span_id).

This enables correlation of all operations within a single user session across:
- Console logs (via TraceContextFilter in src/shared/logging.py)
- OTLP-exported traces (via Agent Framework observability)
- Child spans created by orchestrator stages

Usage:
    span = get_or_create_session_span(session_id)
    with trace.use_span(span, end_on_exit=False):
        # All operations here share the session's trace context
        ...
    
    # When session ends:
    end_session_span(session_id)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict

from agent_framework.observability import get_tracer

try:
    from opentelemetry import trace
except Exception:  # pragma: no cover
    trace = None


@dataclass
class _SessionSpan:
    span: Any
    created_at: float


_SESSION_SPANS: Dict[str, _SessionSpan] = {}


def get_or_create_session_span(session_id: str) -> Any:
    if trace is None:
        raise RuntimeError("OpenTelemetry is not available")

    existing = _SESSION_SPANS.get(session_id)
    if existing is not None:
        return existing.span

    tracer = get_tracer(instrumenting_module_name="azure_pricing_assistant.session")
    span = tracer.start_span(
        name="session.web",
        attributes={"session.id": session_id, "session.type": "web"},
    )
    _SESSION_SPANS[session_id] = _SessionSpan(span=span, created_at=time.time())
    return span


def end_session_span(session_id: str) -> None:
    existing = _SESSION_SPANS.pop(session_id, None)
    if existing is None:
        return

    try:
        existing.span.end()
    except Exception:
        pass
