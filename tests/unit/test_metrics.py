"""Tests for OpenTelemetry metrics module."""

import os
import pytest
from unittest.mock import MagicMock, patch, call

from src.shared.metrics import (
    configure_metrics,
    increment_chat_turns,
    increment_proposals_generated,
    increment_errors,
)


class TestMetricsConfiguration:
    """Tests for metrics configuration."""

    def test_configure_metrics_disabled_by_default(self):
        """Test metrics are disabled when ENABLE_OTEL is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Should not raise exception
            configure_metrics()

    def test_configure_metrics_disabled_explicitly(self):
        """Test metrics are disabled when ENABLE_OTEL is false."""
        with patch.dict(os.environ, {"ENABLE_OTEL": "false"}):
            configure_metrics()

    @patch("src.shared.metrics.OTLPMetricExporter")
    @patch("src.shared.metrics.PeriodicExportingMetricReader")
    @patch("src.shared.metrics.MeterProvider")
    @patch("src.shared.metrics.metrics.set_meter_provider")
    @patch("src.shared.metrics.metrics.get_meter")
    def test_configure_metrics_enabled(
        self, mock_get_meter, mock_set_provider, mock_provider_class, mock_reader_class, mock_exporter_class
    ):
        """Test metrics are configured when ENABLE_OTEL is true."""
        # Reset global state
        import src.shared.metrics as metrics_module
        metrics_module._METRICS_CONFIGURED = False

        with patch.dict(os.environ, {"ENABLE_OTEL": "true", "OTLP_ENDPOINT": "http://localhost:4317"}):
            # Setup mocks
            mock_exporter = MagicMock()
            mock_exporter_class.return_value = mock_exporter

            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader

            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider

            mock_meter = MagicMock()
            mock_get_meter.return_value = mock_meter

            # Create counter mocks
            mock_chat_counter = MagicMock()
            mock_proposals_counter = MagicMock()
            mock_errors_counter = MagicMock()
            
            mock_meter.create_counter.side_effect = [
                mock_chat_counter,
                mock_proposals_counter,
                mock_errors_counter,
            ]

            # Configure metrics
            configure_metrics()

            # Verify OTLP exporter was created with correct endpoint
            mock_exporter_class.assert_called_once()
            call_kwargs = mock_exporter_class.call_args.kwargs
            assert call_kwargs["endpoint"] == "http://localhost:4317"
            assert call_kwargs["insecure"] is True

            # Verify meter provider was set
            mock_set_provider.assert_called_once_with(mock_provider)

            # Verify meter was retrieved
            mock_get_meter.assert_called_once_with("azure_pricing_assistant")

            # Verify counters were created
            assert mock_meter.create_counter.call_count == 3

    def test_configure_metrics_handles_errors_gracefully(self):
        """Test metrics configuration handles errors without crashing."""
        with patch.dict(os.environ, {"ENABLE_OTEL": "true"}):
            with patch("src.shared.metrics.OTLPMetricExporter", side_effect=Exception("Test error")):
                # Should not raise exception
                configure_metrics()


class TestMetricsIncrements:
    """Tests for metrics increment functions."""

    def test_increment_chat_turns_when_configured(self):
        """Test chat turns counter is incremented when metrics are configured."""
        import src.shared.metrics as metrics_module
        
        mock_counter = MagicMock()
        metrics_module._chat_turns_counter = mock_counter

        increment_chat_turns("session-123")

        mock_counter.add.assert_called_once_with(1, {"session_id": "session-123"})

    def test_increment_chat_turns_when_not_configured(self):
        """Test chat turns increment is safe when metrics not configured."""
        import src.shared.metrics as metrics_module
        
        metrics_module._chat_turns_counter = None

        # Should not raise exception
        increment_chat_turns("session-123")

    def test_increment_proposals_generated_success(self):
        """Test proposals counter is incremented with success=True."""
        import src.shared.metrics as metrics_module
        
        mock_counter = MagicMock()
        metrics_module._proposals_counter = mock_counter

        increment_proposals_generated("session-123", success=True)

        mock_counter.add.assert_called_once_with(1, {"session_id": "session-123", "success": "True"})

    def test_increment_proposals_generated_failure(self):
        """Test proposals counter is incremented with success=False."""
        import src.shared.metrics as metrics_module
        
        mock_counter = MagicMock()
        metrics_module._proposals_counter = mock_counter

        increment_proposals_generated("session-123", success=False)

        mock_counter.add.assert_called_once_with(1, {"session_id": "session-123", "success": "False"})

    def test_increment_errors_with_session(self):
        """Test errors counter is incremented with error type and session."""
        import src.shared.metrics as metrics_module
        
        mock_counter = MagicMock()
        metrics_module._errors_counter = mock_counter

        increment_errors("validation_error", session_id="session-123")

        mock_counter.add.assert_called_once_with(1, {"error_type": "validation_error", "session_id": "session-123"})

    def test_increment_errors_without_session(self):
        """Test errors counter is incremented with only error type."""
        import src.shared.metrics as metrics_module
        
        mock_counter = MagicMock()
        metrics_module._errors_counter = mock_counter

        increment_errors("mcp_timeout")

        mock_counter.add.assert_called_once_with(1, {"error_type": "mcp_timeout"})

    def test_increment_errors_when_not_configured(self):
        """Test errors increment is safe when metrics not configured."""
        import src.shared.metrics as metrics_module
        
        metrics_module._errors_counter = None

        # Should not raise exception
        increment_errors("test_error")


class TestMetricsURLHandling:
    """Tests for OTLP endpoint URL handling."""

    @patch("src.shared.metrics.OTLPMetricExporter")
    @patch("src.shared.metrics.PeriodicExportingMetricReader")
    @patch("src.shared.metrics.MeterProvider")
    @patch("src.shared.metrics.metrics.set_meter_provider")
    @patch("src.shared.metrics.metrics.get_meter")
    def test_endpoint_with_trailing_slash(
        self, mock_get_meter, mock_set_provider, mock_provider_class, mock_reader_class, mock_exporter_class
    ):
        """Test OTLP endpoint trailing slash is stripped."""
        import src.shared.metrics as metrics_module
        metrics_module._METRICS_CONFIGURED = False

        with patch.dict(os.environ, {"ENABLE_OTEL": "true", "OTLP_ENDPOINT": "http://localhost:4317/"}):
            mock_meter = MagicMock()
            mock_get_meter.return_value = mock_meter
            mock_meter.create_counter.return_value = MagicMock()

            configure_metrics()

            call_kwargs = mock_exporter_class.call_args.kwargs
            assert call_kwargs["endpoint"] == "http://localhost:4317"

    @patch("src.shared.metrics.OTLPMetricExporter")
    @patch("src.shared.metrics.PeriodicExportingMetricReader")
    @patch("src.shared.metrics.MeterProvider")
    @patch("src.shared.metrics.metrics.set_meter_provider")
    @patch("src.shared.metrics.metrics.get_meter")
    def test_endpoint_without_scheme(
        self, mock_get_meter, mock_set_provider, mock_provider_class, mock_reader_class, mock_exporter_class
    ):
        """Test OTLP endpoint without scheme gets http:// prefix."""
        import src.shared.metrics as metrics_module
        metrics_module._METRICS_CONFIGURED = False

        with patch.dict(os.environ, {"ENABLE_OTEL": "true", "OTLP_ENDPOINT": "localhost:4317"}):
            mock_meter = MagicMock()
            mock_get_meter.return_value = mock_meter
            mock_meter.create_counter.return_value = MagicMock()

            configure_metrics()

            call_kwargs = mock_exporter_class.call_args.kwargs
            assert call_kwargs["endpoint"] == "http://localhost:4317"

    @patch("src.shared.metrics.OTLPMetricExporter")
    @patch("src.shared.metrics.PeriodicExportingMetricReader")
    @patch("src.shared.metrics.MeterProvider")
    @patch("src.shared.metrics.metrics.set_meter_provider")
    @patch("src.shared.metrics.metrics.get_meter")
    def test_default_endpoint_used(
        self, mock_get_meter, mock_set_provider, mock_provider_class, mock_reader_class, mock_exporter_class
    ):
        """Test default OTLP endpoint is used when not specified."""
        import src.shared.metrics as metrics_module
        metrics_module._METRICS_CONFIGURED = False

        with patch.dict(os.environ, {"ENABLE_OTEL": "true"}, clear=True):
            mock_meter = MagicMock()
            mock_get_meter.return_value = mock_meter
            mock_meter.create_counter.return_value = MagicMock()

            configure_metrics()

            call_kwargs = mock_exporter_class.call_args.kwargs
            assert call_kwargs["endpoint"] == "http://localhost:4317"


class TestMetricsIdempotence:
    """Tests for metrics configuration idempotence."""

    @patch("src.shared.metrics.OTLPMetricExporter")
    @patch("src.shared.metrics.PeriodicExportingMetricReader")
    @patch("src.shared.metrics.MeterProvider")
    def test_configure_metrics_is_idempotent(self, mock_provider_class, mock_reader_class, mock_exporter_class):
        """Test configure_metrics can be called multiple times safely."""
        import src.shared.metrics as metrics_module
        metrics_module._METRICS_CONFIGURED = False

        with patch.dict(os.environ, {"ENABLE_OTEL": "true"}):
            with patch("src.shared.metrics.metrics.set_meter_provider"), \
                 patch("src.shared.metrics.metrics.get_meter") as mock_get_meter:
                
                mock_meter = MagicMock()
                mock_get_meter.return_value = mock_meter
                mock_meter.create_counter.return_value = MagicMock()

                # Configure multiple times
                configure_metrics()
                configure_metrics()
                configure_metrics()

                # Exporter should only be created once
                assert mock_exporter_class.call_count == 1
