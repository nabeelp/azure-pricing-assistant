"""Tests for web UI error handling and display."""

import pytest
from unittest.mock import AsyncMock, patch
from flask import Flask

from src.web.app import app as flask_app
from src.core.session import InMemorySessionStore
from src.web.interface import WebInterface
from src.web.handlers import WebHandlers


@pytest.fixture
def client():
    """Flask test client."""
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def session_store():
    """Create a fresh session store."""
    return InMemorySessionStore()


@pytest.fixture
def web_interface(session_store):
    """Create a web interface with mocked dependencies."""
    return WebInterface(session_store)


@pytest.fixture
def handlers(web_interface):
    """Create web handlers."""
    return WebHandlers(web_interface)


class TestChatErrorHandling:
    """Tests for chat endpoint error handling."""
    
    def test_chat_returns_error_on_exception(self, client):
        """Chat endpoint should return 500 with error message on exception."""
        with client.session_transaction() as sess:
            sess['session_id'] = 'test-session'
        
        # Mock the handler to raise an exception
        with patch('src.web.app.handlers.handle_chat', new_callable=AsyncMock) as mock_handle:
            mock_handle.side_effect = Exception("Test error")
            
            response = client.post('/api/chat', json={'message': 'test'})
            
            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
            assert 'Test error' in data['error']
    
    def test_chat_handles_network_timeout(self, client):
        """Chat endpoint should handle timeout errors gracefully."""
        with client.session_transaction() as sess:
            sess['session_id'] = 'test-session'
        
        with patch('src.web.app.handlers.handle_chat', new_callable=AsyncMock) as mock_handle:
            mock_handle.side_effect = TimeoutError("Request timed out")
            
            response = client.post('/api/chat', json={'message': 'test'})
            
            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
    
    def test_chat_handles_json_decode_error(self, client):
        """Chat endpoint should handle malformed JSON gracefully."""
        response = client.post(
            '/api/chat',
            data='invalid json',
            content_type='application/json'
        )
        
        # Flask will return 400 for bad JSON
        assert response.status_code in [400, 500]


class TestProposalGenerationErrorHandling:
    """Tests for proposal generation error handling."""
    
    def test_generate_proposal_returns_error_without_session(self, client):
        """Generate proposal should return 400 when no session exists."""
        response = client.post('/api/generate-proposal')
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'session' in data['error'].lower()
    
    def test_generate_proposal_handles_exception(self, client):
        """Generate proposal should return 500 on exception."""
        with client.session_transaction() as sess:
            sess['session_id'] = 'test-session'
        
        with patch('src.web.app.handlers.handle_generate_proposal', new_callable=AsyncMock) as mock_handle:
            mock_handle.side_effect = Exception("Proposal generation failed")
            
            response = client.post('/api/generate-proposal')
            
            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
    
    def test_generate_proposal_stream_without_session(self, client):
        """Generate proposal stream should return 400 without session."""
        response = client.get('/api/generate-proposal-stream')
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


class TestResetErrorHandling:
    """Tests for reset endpoint error handling."""
    
    def test_reset_handles_exception(self, client):
        """Reset endpoint should return 500 on exception."""
        with client.session_transaction() as sess:
            sess['session_id'] = 'test-session'
        
        with patch('src.web.app.handlers.handle_reset', new_callable=AsyncMock) as mock_handle:
            mock_handle.side_effect = Exception("Reset failed")
            
            response = client.post('/api/reset')
            
            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
    
    def test_reset_succeeds_without_session(self, client):
        """Reset should succeed even without active session."""
        response = client.post('/api/reset')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('status') == 'reset'


class TestHandlerErrorHandling:
    """Tests for handler-level error handling."""
    
    @pytest.mark.asyncio
    async def test_handle_chat_propagates_exception(self, handlers):
        """Handle chat should propagate exceptions for proper HTTP error codes."""
        with patch.object(handlers.interface, 'chat_turn', new_callable=AsyncMock) as mock_turn:
            mock_turn.side_effect = RuntimeError("Chat processing failed")
            
            with pytest.raises(RuntimeError):
                await handlers.handle_chat('test-session', 'test message')
    
    @pytest.mark.asyncio
    async def test_handle_generate_proposal_propagates_exception(self, handlers):
        """Handle generate proposal should propagate exceptions."""
        with patch.object(handlers.interface, 'generate_proposal', new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = RuntimeError("Proposal generation failed")
            
            with pytest.raises(RuntimeError):
                await handlers.handle_generate_proposal('test-session')
    
    @pytest.mark.asyncio
    async def test_handle_generate_proposal_returns_error_dict(self, handlers):
        """Handle generate proposal should return error dict when interface returns error."""
        with patch.object(handlers.interface, 'generate_proposal', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {"error": "No BOM available"}
            
            result = await handlers.handle_generate_proposal('test-session')
            
            assert 'error' in result
            assert result['error'] == "No BOM available"


class TestHTMLErrorElements:
    """Tests for HTML error UI elements."""
    
    def test_index_page_contains_error_banner(self, client):
        """Index page should contain error banner element."""
        response = client.get('/')
        
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'id="errorBanner"' in html
        assert 'error-banner' in html
    
    def test_index_page_contains_error_styling(self, client):
        """Index page should contain error message styling."""
        response = client.get('/')
        
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert '.error-banner' in html
        assert '.error-message' in html
        assert 'slideDown' in html  # Animation
    
    def test_index_page_contains_error_handlers(self, client):
        """Index page should contain JavaScript error handling functions."""
        response = client.get('/')
        
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'showErrorBanner' in html
        assert 'hideErrorBanner' in html
        assert 'addErrorMessage' in html
        assert 'retryLastMessage' in html


class TestErrorMessageFormatting:
    """Tests for error message structure and formatting."""
    
    def test_index_page_error_message_has_icon(self, client):
        """Error messages should include icon element."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        
        assert 'error-message-icon' in html
    
    def test_index_page_error_message_has_title_and_detail(self, client):
        """Error messages should have title and detail elements."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        
        assert 'error-message-title' in html
        assert 'error-message-detail' in html
    
    def test_index_page_has_retry_button_styling(self, client):
        """Error messages should have retry button styling."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        
        assert '.retry-button' in html
        assert 'retry-button:hover' in html


class TestErrorHandlingIntegration:
    """Integration tests for error handling workflow."""
    
    def test_chat_error_flow(self, client):
        """Test complete error handling flow for chat errors."""
        with client.session_transaction() as sess:
            sess['session_id'] = 'test-session'
        
        # Simulate backend error
        with patch('src.web.app.handlers.handle_chat', new_callable=AsyncMock) as mock_handle:
            mock_handle.side_effect = Exception("Backend service unavailable")
            
            response = client.post('/api/chat', json={'message': 'test'})
            
            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
            assert len(data['error']) > 0
    
    def test_proposal_stream_error_format(self, client):
        """Test error format for streaming proposal generation."""
        with client.session_transaction() as sess:
            sess['session_id'] = 'test-session'
        
        # Create a session with some data
        from src.core.models import SessionData
        from src.web.app import session_store
        
        session_data = SessionData(
            thread=None,
            history=[{"role": "user", "content": "test"}]
        )
        session_store.set('test-session', session_data)
        
        # Mock the streaming handler to yield error
        async def mock_stream_error(session_id):
            yield {"event_type": "error", "message": "Stream failed"}
        
        with patch('src.web.app.handlers.handle_generate_proposal_stream', mock_stream_error):
            response = client.get('/api/generate-proposal-stream')
            
            assert response.status_code == 200  # SSE returns 200 even on errors
            assert response.content_type == 'text/event-stream; charset=utf-8'


class TestErrorBannerBehavior:
    """Tests for error banner UI behavior."""
    
    def test_error_banner_has_close_button(self, client):
        """Error banner should have close button."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        
        assert 'error-banner-close' in html
        assert 'hideErrorBanner()' in html
    
    def test_error_banner_animation(self, client):
        """Error banner should have slide down animation."""
        response = client.get('/')
        html = response.data.decode('utf-8')
        
        assert '@keyframes slideDown' in html


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
