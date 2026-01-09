"""Tests for Web handlers and API endpoints."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.web.handlers import WebHandlers
from src.web.interface import WebInterface
from src.core.session import InMemorySessionStore


class TestWebHandlersChatEndpoint:
    """Test chat endpoint handler."""

    @pytest.mark.asyncio
    async def test_handle_chat_success(self):
        """Test successful chat endpoint call."""
        # Mock WebInterface
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.chat_turn.return_value = {
            "response": "I'll help you estimate costs.",
            "is_done": False,
            "bom_items": [],
            "bom_updated": False,
            "error": None,
        }

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_chat("session1", "What are costs for a VM?")

        assert result["response"] == "I'll help you estimate costs."
        assert result["is_done"] is False
        assert result["bom_items"] == []
        assert result["bom_updated"] is False
        assert result["error"] is None
        mock_interface.chat_turn.assert_called_once_with("session1", "What are costs for a VM?")

    @pytest.mark.asyncio
    async def test_handle_chat_with_error(self):
        """Test chat endpoint with error response."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.chat_turn.return_value = {
            "response": "",
            "is_done": False,
            "error": "Configuration error",
        }

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_chat("session1", "Hello")

        assert result["error"] == "Configuration error"
        assert result["is_done"] is False

    @pytest.mark.asyncio
    async def test_handle_chat_workflow_complete(self):
        """Test chat endpoint signals workflow completion."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.chat_turn.return_value = {
            "response": '{"requirements": "Web app", "done": true}',
            "is_done": True,
            "bom_items": [{"serviceName": "Azure App Service", "sku": "P1v2", "quantity": 1, "region": "East US", "armRegionName": "eastus", "hours_per_month": 730}],
            "bom_updated": True,
            "error": None,
        }

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_chat("session1", "Done")

        assert result["is_done"] is True
        assert result["bom_items"] is not None
        assert len(result["bom_items"]) == 1
        # JSON response is filtered by the handler
        assert result["response"] == ""

    @pytest.mark.asyncio
    async def test_handle_chat_preserves_response(self):
        """Test that response is not modified by handler."""
        mock_interface = AsyncMock(spec=WebInterface)
        original_response = "Detailed explanation about Azure services"
        mock_interface.chat_turn.return_value = {
            "response": original_response,
            "is_done": False,
            "bom_items": [],
            "bom_updated": False,
            "error": None,
        }

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_chat("session1", "Tell me more")

        assert result["response"] == original_response


class TestWebHandlersProposalEndpoint:
    """Test proposal generation endpoint handler."""

    @pytest.mark.asyncio
    async def test_handle_generate_proposal_success(self):
        """Test successful proposal generation."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.generate_proposal.return_value = {
            "bom": '[{"serviceName": "VM", "sku": "D2"}]',
            "pricing": '{"total_monthly": 100.00}',
            "proposal": "# Azure Proposal\n\nFull proposal here.",
        }

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_generate_proposal("session1")

        assert "bom" in result
        assert "pricing" in result
        assert "proposal" in result
        assert "# Azure Proposal" in result["proposal"]

    @pytest.mark.asyncio
    async def test_handle_generate_proposal_with_error(self):
        """Test proposal generation with error."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.generate_proposal.return_value = {
            "error": "Session not found"
        }

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_generate_proposal("invalid_session")

        assert "error" in result
        assert result["error"] == "Session not found"
        assert "bom" not in result

    @pytest.mark.asyncio
    async def test_handle_generate_proposal_with_missing_fields(self):
        """Test proposal generation with partial data."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.generate_proposal.return_value = {
            "bom": "[]",
            "pricing": "{}",
            "proposal": "",
        }

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_generate_proposal("session1")

        assert result["bom"] == "[]"
        assert result["pricing"] == "{}"
        assert result["proposal"] == ""


class TestWebHandlersResetEndpoint:
    """Test session reset endpoint handler."""

    @pytest.mark.asyncio
    async def test_handle_reset_success(self):
        """Test successful session reset."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.reset_session.return_value = None

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_reset("session1")

        assert result["status"] == "reset"
        mock_interface.reset_session.assert_called_once_with("session1")

    @pytest.mark.asyncio
    async def test_handle_reset_clears_history(self):
        """Test reset endpoint clears session state."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.reset_session.return_value = None

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_reset("session1")

        assert result["status"] == "reset"
        # Verify reset was called
        mock_interface.reset_session.assert_called_once()


class TestWebHandlersHistoryEndpoint:
    """Test session history retrieval endpoint handler."""

    @pytest.mark.asyncio
    async def test_handle_history_empty(self):
        """Test history endpoint with no messages."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.get_session_history.return_value = []

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_history("session1")

        assert result["history"] == []

    @pytest.mark.asyncio
    async def test_handle_history_with_messages(self):
        """Test history endpoint with message history."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.get_session_history.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_history("session1")

        assert len(result["history"]) == 2
        assert result["history"][0]["role"] == "user"
        assert result["history"][1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_handle_history_preserves_order(self):
        """Test that history maintains message order."""
        mock_interface = AsyncMock(spec=WebInterface)
        messages = [
            {"role": "user", "content": f"Message {i}"} for i in range(5)
        ]
        mock_interface.get_session_history.return_value = messages

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_history("session1")

        assert len(result["history"]) == 5
        for i, msg in enumerate(result["history"]):
            assert msg["content"] == f"Message {i}"


class TestWebHandlerSessionIsolation:
    """Test that sessions are properly isolated."""

    @pytest.mark.asyncio
    async def test_different_sessions_independent(self):
        """Test that different sessions don't interfere."""
        mock_interface = AsyncMock(spec=WebInterface)

        # Set up different responses for different sessions
        async def chat_turn_side_effect(session_id, message):
            if session_id == "session1":
                return {
                    "response": "Response for session 1",
                    "is_done": False,
                    "error": None,
                }
            else:
                return {
                    "response": "Response for session 2",
                    "is_done": False,
                    "error": None,
                }

        mock_interface.chat_turn.side_effect = chat_turn_side_effect

        handlers = WebHandlers(mock_interface)

        result1 = await handlers.handle_chat("session1", "Hello")
        result2 = await handlers.handle_chat("session2", "Hello")

        assert result1["response"] == "Response for session 1"
        assert result2["response"] == "Response for session 2"

    @pytest.mark.asyncio
    async def test_reset_affects_only_target_session(self):
        """Test that reset only affects the specified session."""
        mock_interface = AsyncMock(spec=WebInterface)
        reset_calls = []

        async def reset_side_effect(session_id):
            reset_calls.append(session_id)

        mock_interface.reset_session.side_effect = reset_side_effect

        handlers = WebHandlers(mock_interface)

        await handlers.handle_reset("session1")
        await handlers.handle_reset("session2")

        assert reset_calls == ["session1", "session2"]
        assert mock_interface.reset_session.call_count == 2


class TestWebHandlerTurnLimitEnforcement:
    """Test turn limit enforcement in web handlers."""

    @pytest.mark.asyncio
    async def test_handle_chat_respects_turn_limit(self):
        """Test that handler respects 20-turn limit."""
        mock_interface = AsyncMock(spec=WebInterface)

        # Simulate reaching turn limit
        mock_interface.chat_turn.return_value = {
            "response": "",
            "is_done": False,
            "error": "Turn limit exceeded (20 turns)",
        }

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_chat("session1", "Message at turn 21")

        assert "Turn limit" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_chat_allows_below_limit(self):
        """Test that handler allows chat below 20 turns."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.chat_turn.return_value = {
            "response": "Response at turn 10",
            "is_done": False,
            "error": None,
        }

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_chat("session1", "Message")

        assert result["error"] is None
        assert "turn 10" in result["response"].lower()


class TestWebHandlerResponseFormats:
    """Test response format consistency."""

    @pytest.mark.asyncio
    async def test_chat_response_has_required_fields(self):
        """Test chat response has response, is_done, error fields."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.chat_turn.return_value = {
            "response": "Test",
            "is_done": False,
            "error": None,
        }

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_chat("session1", "Test")

        assert "response" in result
        assert "is_done" in result
        assert "error" in result
        assert isinstance(result["response"], str)
        assert isinstance(result["is_done"], bool)

    @pytest.mark.asyncio
    async def test_proposal_response_has_required_fields(self):
        """Test proposal response has required fields when successful."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.generate_proposal.return_value = {
            "bom": "[]",
            "pricing": "{}",
            "proposal": "# Proposal",
        }

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_generate_proposal("session1")

        assert "bom" in result or "error" in result
        assert "pricing" in result or "error" in result
        assert "proposal" in result or "error" in result

    @pytest.mark.asyncio
    async def test_reset_response_format(self):
        """Test reset response has status field."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.reset_session.return_value = None

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_reset("session1")

        assert "status" in result
        assert result["status"] == "reset"

    @pytest.mark.asyncio
    async def test_history_response_format(self):
        """Test history response has history field."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.get_session_history.return_value = []

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_history("session1")

        assert "history" in result
        assert isinstance(result["history"], list)


class TestWebHandlerErrorHandling:
    """Test error handling in web handlers."""

    @pytest.mark.asyncio
    async def test_handle_chat_returns_error_gracefully(self):
        """Test chat handles errors without raising exceptions."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.chat_turn.return_value = {
            "response": "",
            "is_done": False,
            "error": "Backend error",
        }

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_chat("session1", "Test")

        assert result["error"] == "Backend error"
        assert result["is_done"] is False

    @pytest.mark.asyncio
    async def test_handle_proposal_returns_error_gracefully(self):
        """Test proposal generation handles errors without raising."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.generate_proposal.return_value = {
            "error": "Session not ready for proposal"
        }

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_generate_proposal("session1")

        assert "error" in result
        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_handler_with_none_values(self):
        """Test handler handles None values in responses."""
        mock_interface = AsyncMock(spec=WebInterface)
        mock_interface.chat_turn.return_value = {
            "response": None,
            "is_done": False,
            "error": None,
        }

        handlers = WebHandlers(mock_interface)
        result = await handlers.handle_chat("session1", "Test")

        # Handler should return empty string for None response
        assert result["response"] is None or result["response"] == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
