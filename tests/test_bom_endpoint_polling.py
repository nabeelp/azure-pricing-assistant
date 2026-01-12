"""Tests for enhanced /api/bom endpoint with polling support."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.core.models import SessionData
from src.core.session import InMemorySessionStore
from src.web.interface import WebInterface


class TestBOMEndpointPollingSupport:
    """Test /api/bom endpoint enhancements for polling-based updates."""

    @pytest.mark.asyncio
    async def test_get_bom_returns_task_status(self):
        """Verify get_bom_items returns bom_task_status field."""
        # Setup
        session_store = InMemorySessionStore()
        session_id = "test-session-1"
        
        thread = MagicMock()
        session_data = SessionData(thread=thread, history=[])
        session_data.bom_items = [{"serviceName": "App Service"}]
        session_data.bom_task_status = "complete"
        session_store.set(session_id, session_data)
        
        interface = WebInterface(session_store)
        
        # Get BOM
        result = await interface.get_bom_items(session_id)
        
        # Verify task status included
        assert "bom_task_status" in result
        assert result["bom_task_status"] == "complete"
        assert "bom_items" in result
        assert len(result["bom_items"]) == 1

    @pytest.mark.asyncio
    async def test_get_bom_returns_last_update_timestamp(self):
        """Verify get_bom_items returns bom_last_update timestamp."""
        # Setup
        session_store = InMemorySessionStore()
        session_id = "test-session-2"
        
        thread = MagicMock()
        session_data = SessionData(thread=thread, history=[])
        session_data.bom_items = [{"serviceName": "SQL Database"}]
        session_data.bom_task_status = "complete"
        session_data.bom_last_update = datetime(2026, 1, 12, 15, 30, 45)
        session_store.set(session_id, session_data)
        
        interface = WebInterface(session_store)
        
        # Get BOM
        result = await interface.get_bom_items(session_id)
        
        # Verify timestamp included and formatted as ISO 8601
        assert "bom_last_update" in result
        assert result["bom_last_update"] == "2026-01-12T15:30:45"
        assert "bom_items" in result

    @pytest.mark.asyncio
    async def test_get_bom_returns_task_error(self):
        """Verify get_bom_items returns bom_task_error when status is error."""
        # Setup
        session_store = InMemorySessionStore()
        session_id = "test-session-3"
        
        thread = MagicMock()
        session_data = SessionData(thread=thread, history=[])
        session_data.bom_task_status = "error"
        session_data.bom_task_error = "MCP server unavailable"
        session_store.set(session_id, session_data)
        
        interface = WebInterface(session_store)
        
        # Get BOM
        result = await interface.get_bom_items(session_id)
        
        # Verify error included
        assert "bom_task_error" in result
        assert result["bom_task_error"] == "MCP server unavailable"
        assert result["bom_task_status"] == "error"

    @pytest.mark.asyncio
    async def test_get_bom_idle_status_for_new_session(self):
        """Verify get_bom_items returns idle status for new session."""
        # Setup
        session_store = InMemorySessionStore()
        session_id = "test-session-new"
        
        interface = WebInterface(session_store)
        
        # Get BOM (session doesn't exist)
        result = await interface.get_bom_items(session_id)
        
        # Verify default values
        assert result["bom_task_status"] == "idle"
        assert result["bom_items"] == []
        assert result["bom_last_update"] is None
        assert result["bom_task_error"] is None

    @pytest.mark.asyncio
    async def test_get_bom_processing_status(self):
        """Verify get_bom_items returns processing status during BOM generation."""
        # Setup
        session_store = InMemorySessionStore()
        session_id = "test-session-processing"
        
        thread = MagicMock()
        session_data = SessionData(thread=thread, history=[])
        session_data.bom_task_status = "processing"
        session_data.bom_items = [{"serviceName": "Storage"}]
        session_store.set(session_id, session_data)
        
        interface = WebInterface(session_store)
        
        # Get BOM
        result = await interface.get_bom_items(session_id)
        
        # Verify processing status
        assert result["bom_task_status"] == "processing"
        assert len(result["bom_items"]) == 1
        assert result["bom_last_update"] is None  # Not yet updated

    @pytest.mark.asyncio
    async def test_get_bom_queued_status(self):
        """Verify get_bom_items returns queued status when task is waiting."""
        # Setup
        session_store = InMemorySessionStore()
        session_id = "test-session-queued"
        
        thread = MagicMock()
        session_data = SessionData(thread=thread, history=[])
        session_data.bom_task_status = "queued"
        session_store.set(session_id, session_data)
        
        interface = WebInterface(session_store)
        
        # Get BOM
        result = await interface.get_bom_items(session_id)
        
        # Verify queued status
        assert result["bom_task_status"] == "queued"
        assert result["bom_items"] == []

    @pytest.mark.asyncio
    async def test_get_bom_null_fields_when_not_set(self):
        """Verify get_bom_items returns null for optional fields when not set."""
        # Setup
        session_store = InMemorySessionStore()
        session_id = "test-session-defaults"
        
        thread = MagicMock()
        session_data = SessionData(thread=thread, history=[])
        session_data.bom_task_status = "idle"
        # Don't set bom_last_update or bom_task_error
        session_store.set(session_id, session_data)
        
        interface = WebInterface(session_store)
        
        # Get BOM
        result = await interface.get_bom_items(session_id)
        
        # Verify null fields
        assert result["bom_last_update"] is None
        assert result["bom_task_error"] is None
        assert result["bom_task_status"] == "idle"

    @pytest.mark.asyncio
    async def test_get_bom_includes_all_required_fields(self):
        """Verify get_bom_items response has all required fields."""
        # Setup
        session_store = InMemorySessionStore()
        session_id = "test-session-complete"
        
        thread = MagicMock()
        session_data = SessionData(thread=thread, history=[])
        session_data.bom_items = [
            {"serviceName": "App Service", "sku": "P1v2"},
            {"serviceName": "SQL Database", "sku": "S1"}
        ]
        session_data.bom_task_status = "complete"
        session_data.bom_last_update = datetime(2026, 1, 12, 16, 0, 0)
        session_data.bom_task_error = None
        session_store.set(session_id, session_data)
        
        interface = WebInterface(session_store)
        
        # Get BOM
        result = await interface.get_bom_items(session_id)
        
        # Verify all required fields present
        assert "bom_items" in result
        assert "bom_task_status" in result
        assert "bom_last_update" in result
        assert "bom_task_error" in result
        
        # Verify values
        assert len(result["bom_items"]) == 2
        assert result["bom_task_status"] == "complete"
        assert result["bom_last_update"] == "2026-01-12T16:00:00"
        assert result["bom_task_error"] is None

    @pytest.mark.asyncio
    async def test_get_bom_change_detection_with_timestamp(self):
        """Verify bom_last_update timestamp enables change detection."""
        # Setup
        session_store = InMemorySessionStore()
        session_id = "test-session-changes"
        
        thread = MagicMock()
        session_data = SessionData(thread=thread, history=[])
        session_data.bom_items = [{"serviceName": "App Service"}]
        session_data.bom_task_status = "complete"
        timestamp1 = datetime(2026, 1, 12, 10, 0, 0)
        session_data.bom_last_update = timestamp1
        session_store.set(session_id, session_data)
        
        interface = WebInterface(session_store)
        
        # First poll
        result1 = await interface.get_bom_items(session_id)
        assert result1["bom_last_update"] == "2026-01-12T10:00:00"
        
        # Simulate BOM update
        session_data.bom_items.append({"serviceName": "SQL Database"})
        timestamp2 = datetime(2026, 1, 12, 10, 5, 0)
        session_data.bom_last_update = timestamp2
        session_store.set(session_id, session_data)
        
        # Second poll
        result2 = await interface.get_bom_items(session_id)
        assert result2["bom_last_update"] == "2026-01-12T10:05:00"
        
        # Verify timestamp changed (enables change detection in UI)
        assert result2["bom_last_update"] != result1["bom_last_update"]
        assert len(result2["bom_items"]) == 2

