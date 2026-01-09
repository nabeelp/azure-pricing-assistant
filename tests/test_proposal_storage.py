"""Tests for proposal storage mechanism."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.models import SessionData, ProposalBundle
from src.core.session import InMemorySessionStore


class TestProposalStorageInSession:
    """Test proposal storage in SessionData."""

    def test_session_data_has_proposal_field(self):
        """Test that SessionData has proposal field."""
        session_data = SessionData(thread=None, history=[])
        assert hasattr(session_data, "proposal")
        assert session_data.proposal is None

    def test_session_data_stores_proposal_bundle(self):
        """Test that SessionData can store ProposalBundle."""
        proposal = ProposalBundle(
            bom_text="BOM content",
            pricing_text="Pricing content",
            proposal_text="Proposal content"
        )
        session_data = SessionData(thread=None, history=[], proposal=proposal)
        
        assert session_data.proposal is not None
        assert session_data.proposal.bom_text == "BOM content"
        assert session_data.proposal.pricing_text == "Pricing content"
        assert session_data.proposal.proposal_text == "Proposal content"


class TestProposalStorageInHandler:
    """Test proposal storage in WorkflowHandler."""

    @pytest.mark.asyncio
    async def test_handle_proposal_generation_stores_proposal(self):
        """Test that handle_proposal_generation stores proposal in session."""
        from src.interfaces.context import InterfaceContext
        from src.interfaces.handlers import WorkflowHandler
        
        session_store = InMemorySessionStore()
        session_id = "test_session"
        
        # Create session with mock thread and history
        mock_thread = MagicMock()
        session_data = SessionData(
            thread=mock_thread,
            history=[
                {"role": "user", "content": "I need a web app"},
                {"role": "assistant", "content": "What region?"},
                {"role": "user", "content": "East US"}
            ]
        )
        session_store.set(session_id, session_data)
        
        # Mock the client and orchestrator
        mock_client = MagicMock()
        context = InterfaceContext(session_store)
        context._client = mock_client
        
        handler = WorkflowHandler()
        
        # Mock run_bom_pricing_proposal
        mock_bundle = ProposalBundle(
            bom_text="Test BOM",
            pricing_text="Test Pricing",
            proposal_text="Test Proposal"
        )
        
        with patch("src.interfaces.handlers.run_bom_pricing_proposal", return_value=mock_bundle):
            with patch("src.interfaces.handlers.end_session_span"):
                result = await handler.handle_proposal_generation(context, session_id)
        
        # Verify result
        assert "error" not in result
        assert result["bom"] == "Test BOM"
        assert result["pricing"] == "Test Pricing"
        assert result["proposal"] == "Test Proposal"
        
        # Verify proposal was stored in session
        updated_session = session_store.get(session_id)
        assert updated_session.proposal is not None
        assert updated_session.proposal.bom_text == "Test BOM"
        assert updated_session.proposal.pricing_text == "Test Pricing"
        assert updated_session.proposal.proposal_text == "Test Proposal"

    @pytest.mark.asyncio
    async def test_get_stored_proposal_returns_proposal(self):
        """Test that get_stored_proposal returns stored proposal."""
        from src.interfaces.context import InterfaceContext
        from src.interfaces.handlers import WorkflowHandler
        
        session_store = InMemorySessionStore()
        session_id = "test_session"
        
        # Create session with stored proposal
        proposal = ProposalBundle(
            bom_text="Stored BOM",
            pricing_text="Stored Pricing",
            proposal_text="Stored Proposal"
        )
        session_data = SessionData(
            thread=MagicMock(),
            history=[],
            proposal=proposal
        )
        session_store.set(session_id, session_data)
        
        context = InterfaceContext(session_store)
        handler = WorkflowHandler()
        
        result = handler.get_stored_proposal(context, session_id)
        
        assert "error" not in result
        assert result["bom"] == "Stored BOM"
        assert result["pricing"] == "Stored Pricing"
        assert result["proposal"] == "Stored Proposal"

    @pytest.mark.asyncio
    async def test_get_stored_proposal_no_session(self):
        """Test that get_stored_proposal returns error when no session exists."""
        from src.interfaces.context import InterfaceContext
        from src.interfaces.handlers import WorkflowHandler
        
        session_store = InMemorySessionStore()
        context = InterfaceContext(session_store)
        handler = WorkflowHandler()
        
        result = handler.get_stored_proposal(context, "nonexistent_session")
        
        assert "error" in result
        assert result["error"] == "Session not found"

    @pytest.mark.asyncio
    async def test_get_stored_proposal_no_proposal(self):
        """Test that get_stored_proposal returns error when no proposal stored."""
        from src.interfaces.context import InterfaceContext
        from src.interfaces.handlers import WorkflowHandler
        
        session_store = InMemorySessionStore()
        session_id = "test_session"
        
        # Create session without proposal
        session_data = SessionData(thread=MagicMock(), history=[])
        session_store.set(session_id, session_data)
        
        context = InterfaceContext(session_store)
        handler = WorkflowHandler()
        
        result = handler.get_stored_proposal(context, session_id)
        
        assert "error" in result
        assert result["error"] == "No proposal found for this session"


class TestProposalStorageInWebInterface:
    """Test proposal storage through WebInterface."""

    def test_web_interface_has_get_stored_proposal_method(self):
        """Test that WebInterface has get_stored_proposal method."""
        from src.web.interface import WebInterface
        
        session_store = InMemorySessionStore()
        interface = WebInterface(session_store)
        
        assert hasattr(interface, "get_stored_proposal")
        assert callable(interface.get_stored_proposal)

    def test_web_interface_get_stored_proposal(self):
        """Test WebInterface.get_stored_proposal returns stored proposal."""
        from src.web.interface import WebInterface
        
        session_store = InMemorySessionStore()
        session_id = "test_session"
        
        # Create session with stored proposal
        proposal = ProposalBundle(
            bom_text="Web BOM",
            pricing_text="Web Pricing",
            proposal_text="Web Proposal"
        )
        session_data = SessionData(
            thread=MagicMock(),
            history=[],
            proposal=proposal
        )
        session_store.set(session_id, session_data)
        
        interface = WebInterface(session_store)
        result = interface.get_stored_proposal(session_id)
        
        assert "error" not in result
        assert result["bom"] == "Web BOM"
        assert result["pricing"] == "Web Pricing"
        assert result["proposal"] == "Web Proposal"


class TestProposalStorageInWebHandlers:
    """Test proposal storage through WebHandlers."""

    def test_web_handlers_has_handle_get_proposal_method(self):
        """Test that WebHandlers has handle_get_proposal method."""
        from src.web.interface import WebInterface
        from src.web.handlers import WebHandlers
        
        session_store = InMemorySessionStore()
        interface = WebInterface(session_store)
        handlers = WebHandlers(interface)
        
        assert hasattr(handlers, "handle_get_proposal")
        assert callable(handlers.handle_get_proposal)

    def test_web_handlers_handle_get_proposal(self):
        """Test WebHandlers.handle_get_proposal returns stored proposal."""
        from src.web.interface import WebInterface
        from src.web.handlers import WebHandlers
        
        session_store = InMemorySessionStore()
        session_id = "test_session"
        
        # Create session with stored proposal
        proposal = ProposalBundle(
            bom_text="Handler BOM",
            pricing_text="Handler Pricing",
            proposal_text="Handler Proposal"
        )
        session_data = SessionData(
            thread=MagicMock(),
            history=[],
            proposal=proposal
        )
        session_store.set(session_id, session_data)
        
        interface = WebInterface(session_store)
        handlers = WebHandlers(interface)
        
        result = handlers.handle_get_proposal(session_id)
        
        assert "error" not in result
        assert result["bom"] == "Handler BOM"
        assert result["pricing"] == "Handler Pricing"
        assert result["proposal"] == "Handler Proposal"

    def test_web_handlers_handle_get_proposal_no_proposal(self):
        """Test WebHandlers.handle_get_proposal with no proposal."""
        from src.web.interface import WebInterface
        from src.web.handlers import WebHandlers
        
        session_store = InMemorySessionStore()
        session_id = "test_session"
        
        # Create session without proposal
        session_data = SessionData(thread=MagicMock(), history=[])
        session_store.set(session_id, session_data)
        
        interface = WebInterface(session_store)
        handlers = WebHandlers(interface)
        
        result = handlers.handle_get_proposal(session_id)
        
        assert "error" in result
        assert "No proposal found" in result["error"]


class TestProposalStorageEndToEnd:
    """Test end-to-end proposal storage and retrieval."""

    @pytest.mark.asyncio
    async def test_generate_and_retrieve_proposal(self):
        """Test generating a proposal and then retrieving it."""
        from src.web.interface import WebInterface
        from src.web.handlers import WebHandlers
        
        session_store = InMemorySessionStore()
        session_id = "test_session"
        
        # Create session with mock thread and history
        mock_thread = MagicMock()
        session_data = SessionData(
            thread=mock_thread,
            history=[
                {"role": "user", "content": "I need a web app"},
                {"role": "assistant", "content": "What region?"},
                {"role": "user", "content": "East US"}
            ]
        )
        session_store.set(session_id, session_data)
        
        # Create interface and handlers
        interface = WebInterface(session_store)
        handlers = WebHandlers(interface)
        
        # Mock the client and orchestrator
        mock_client = MagicMock()
        interface.context._client = mock_client
        
        # Mock run_bom_pricing_proposal
        mock_bundle = ProposalBundle(
            bom_text="E2E BOM",
            pricing_text="E2E Pricing",
            proposal_text="E2E Proposal"
        )
        
        with patch("src.interfaces.handlers.run_bom_pricing_proposal", return_value=mock_bundle):
            with patch("src.interfaces.handlers.end_session_span"):
                # Generate proposal
                gen_result = await handlers.handle_generate_proposal(session_id)
        
        # Verify generation succeeded
        assert "error" not in gen_result
        assert gen_result["bom"] == "E2E BOM"
        
        # Retrieve stored proposal
        retrieve_result = handlers.handle_get_proposal(session_id)
        
        # Verify retrieval succeeded
        assert "error" not in retrieve_result
        assert retrieve_result["bom"] == "E2E BOM"
        assert retrieve_result["pricing"] == "E2E Pricing"
        assert retrieve_result["proposal"] == "E2E Proposal"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
