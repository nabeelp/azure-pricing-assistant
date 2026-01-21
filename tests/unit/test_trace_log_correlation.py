import logging

import pytest

try:
    from opentelemetry.trace import (
        NonRecordingSpan,
        SpanContext,
        TraceFlags,
        use_span,
    )
except Exception:  # pragma: no cover
    NonRecordingSpan = None
    SpanContext = None
    TraceFlags = None
    use_span = None

from src.shared.logging import TraceContextFilter


@pytest.mark.skipif(NonRecordingSpan is None, reason="opentelemetry is not installed")
def test_trace_context_filter_sets_ids_when_span_active() -> None:
    filter_ = TraceContextFilter()

    span_context = SpanContext(
        trace_id=int("1" * 32, 16),
        span_id=int("2" * 16, 16),
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
        trace_state={},
    )

    span = NonRecordingSpan(span_context)

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    with use_span(span, end_on_exit=False):
        assert filter_.filter(record) is True

    assert record.trace_id == "1" * 32
    assert record.span_id == "2" * 16


def test_trace_context_filter_sets_placeholders_when_no_span() -> None:
    filter_ = TraceContextFilter()

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    assert filter_.filter(record) is True
    assert record.trace_id == "-"
    assert record.span_id == "-"
