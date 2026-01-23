"""Tests for /api/proposals endpoint to retrieve all proposals."""

import pytest
from flask import Flask
from flask.testing import FlaskClient
from unittest.mock import MagicMock

from src.core.session import InMemorySessionStore
from src.core.models import SessionData, ProposalBundle
from src.web.interface import WebInterface
from src.web.handlers import WebHandlers


@pytest.fixture
def app():
    """Create a test Flask app."""
    from src.web.app import app as flask_app
    
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-secret-key'
    
    return flask_app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def session_store():
    """Create a session store with test data."""
    store = InMemorySessionStore()
    
    # Session 1 with proposal
    proposal1 = ProposalBundle(
        bom_text="BOM for session 1",
        pricing_text="Pricing for session 1",
        proposal_text="Proposal for session 1"
    )
    session1 = SessionData(
        thread=MagicMock(),
        history=[],
        turn_count=5,
        bom_items=[{"serviceName": "VM", "sku": "D2s_v3"}],
        proposal=proposal1
    )
    store.set("session1", session1)
    
    # Session 2 with proposal
    proposal2 = ProposalBundle(
        bom_text="BOM for session 2",
        pricing_text="Pricing for session 2",
        proposal_text="Proposal for session 2"
    )
    session2 = SessionData(
        thread=MagicMock(),
        history=[],
        turn_count=3,
        bom_items=[{"serviceName": "App Service", "sku": "P1v2"}],
        proposal=proposal2
    )
    store.set("session2", session2)
    
    # Session 3 without proposal (should not be included)
    session3 = SessionData(
        thread=MagicMock(),
        history=[],
        turn_count=1,
        bom_items=[],
        proposal=None
    )
    store.set("session3", session3)
    
    return store


class TestProposalsEndpoint:
    """Test /api/proposals endpoint."""

    def test_get_all_proposals_returns_200(self, client, session_store, app):
        """Test that /api/proposals returns HTTP 200 OK."""
        # Replace the session store in the app
        with app.app_context():
            from src.web.app import handlers
            handlers.interface.context.session_store = session_store
            
            response = client.get('/api/proposals')
            assert response.status_code == 200

    def test_get_all_proposals_returns_correct_count(self, client, session_store, app):
        """Test that /api/proposals returns correct proposal count."""
        with app.app_context():
            from src.web.app import handlers
            handlers.interface.context.session_store = session_store
            
            response = client.get('/api/proposals')
            data = response.get_json()
            
            assert data['count'] == 2  # Only 2 sessions have proposals
            assert len(data['proposals']) == 2

    def test_get_all_proposals_contains_session_ids(self, client, session_store, app):
        """Test that proposals include session IDs."""
        with app.app_context():
            from src.web.app import handlers
            handlers.interface.context.session_store = session_store
            
            response = client.get('/api/proposals')
            data = response.get_json()
            
            session_ids = [p['session_id'] for p in data['proposals']]
            assert 'session1' in session_ids
            assert 'session2' in session_ids
            assert 'session3' not in session_ids  # No proposal

    def test_get_all_proposals_contains_proposal_data(self, client, session_store, app):
        """Test that proposals contain bom, pricing, and proposal text."""
        with app.app_context():
            from src.web.app import handlers
            handlers.interface.context.session_store = session_store
            
            response = client.get('/api/proposals')
            data = response.get_json()
            
            for proposal in data['proposals']:
                assert 'session_id' in proposal
                assert 'bom' in proposal
                assert 'pricing' in proposal
                assert 'proposal' in proposal
                
                # Verify content is present
                assert len(proposal['bom']) > 0
                assert len(proposal['pricing']) > 0
                assert len(proposal['proposal']) > 0

    def test_get_all_proposals_with_empty_store(self, client, app):
        """Test /api/proposals with no proposals stored."""
        empty_store = InMemorySessionStore()
        
        with app.app_context():
            from src.web.app import handlers
            handlers.interface.context.session_store = empty_store
            
            response = client.get('/api/proposals')
            data = response.get_json()
            
            assert response.status_code == 200
            assert data['count'] == 0
            assert data['proposals'] == []

    def test_get_all_proposals_excludes_sessions_without_proposals(self, client, session_store, app):
        """Test that only sessions with proposals are included."""
        with app.app_context():
            from src.web.app import handlers
            handlers.interface.context.session_store = session_store
            
            response = client.get('/api/proposals')
            data = response.get_json()
            
            # Verify session3 (no proposal) is not included
            session_ids = [p['session_id'] for p in data['proposals']]
            assert 'session3' not in session_ids
            
            # Only sessions with proposals should be returned
            assert all(
                session_store.get(sid).proposal is not None 
                for sid in session_ids
            )


class TestSessionStoreGetAllWithProposals:
    """Test InMemorySessionStore.get_all_with_proposals method."""

    def test_get_all_with_proposals_returns_only_sessions_with_proposals(self):
        """Test that method returns only sessions that have proposals."""
        store = InMemorySessionStore()
        
        # Add session with proposal
        proposal1 = ProposalBundle(bom_text="BOM1", pricing_text="Price1", proposal_text="Prop1")
        session1 = SessionData(thread=MagicMock(), history=[], proposal=proposal1)
        store.set("has_proposal", session1)
        
        # Add session without proposal
        session2 = SessionData(thread=MagicMock(), history=[], proposal=None)
        store.set("no_proposal", session2)
        
        result = store.get_all_with_proposals()
        
        assert "has_proposal" in result
        assert "no_proposal" not in result
        assert len(result) == 1

    def test_get_all_with_proposals_returns_empty_dict_when_none_exist(self):
        """Test method returns empty dict when no proposals exist."""
        store = InMemorySessionStore()
        
        session1 = SessionData(thread=MagicMock(), history=[], proposal=None)
        session2 = SessionData(thread=MagicMock(), history=[], proposal=None)
        store.set("session1", session1)
        store.set("session2", session2)
        
        result = store.get_all_with_proposals()
        
        assert result == {}

    def test_get_all_with_proposals_returns_empty_dict_for_empty_store(self):
        """Test method returns empty dict for empty store."""
        store = InMemorySessionStore()
        
        result = store.get_all_with_proposals()
        
        assert result == {}


class TestWebHandlersGetAllProposals:
    """Test WebHandlers.handle_get_all_proposals method."""

    def test_handle_get_all_proposals_returns_proposals_array(self):
        """Test handler returns proposals array."""
        session_store = InMemorySessionStore()
        proposal = ProposalBundle(
            bom_text="Test BOM",
            pricing_text="Test Pricing",
            proposal_text="Test Proposal"
        )
        session_data = SessionData(
            thread=MagicMock(),
            history=[],
            proposal=proposal
        )
        session_store.set("test_session", session_data)
        
        web_interface = WebInterface(session_store)
        handlers = WebHandlers(web_interface)
        
        result = handlers.handle_get_all_proposals()
        
        assert 'proposals' in result
        assert 'count' in result
        assert result['count'] == 1
        assert len(result['proposals']) == 1

    def test_handle_get_all_proposals_includes_correct_structure(self):
        """Test handler returns correct proposal structure."""
        session_store = InMemorySessionStore()
        proposal = ProposalBundle(
            bom_text="Test BOM",
            pricing_text="Test Pricing",
            proposal_text="Test Proposal"
        )
        session_data = SessionData(
            thread=MagicMock(),
            history=[],
            proposal=proposal
        )
        session_store.set("test_session", session_data)
        
        web_interface = WebInterface(session_store)
        handlers = WebHandlers(web_interface)
        
        result = handlers.handle_get_all_proposals()
        
        proposal_item = result['proposals'][0]
        assert proposal_item['session_id'] == 'test_session'
        assert proposal_item['bom'] == 'Test BOM'
        assert proposal_item['pricing'] == 'Test Pricing'
        assert proposal_item['proposal'] == 'Test Proposal'

    def test_handle_get_all_proposals_with_empty_store(self):
        """Test handler with empty session store."""
        session_store = InMemorySessionStore()
        web_interface = WebInterface(session_store)
        handlers = WebHandlers(web_interface)
        
        result = handlers.handle_get_all_proposals()
        
        assert result['proposals'] == []
        assert result['count'] == 0
        assert 'error' not in result
