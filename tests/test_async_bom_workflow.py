"""Tests for asynchronous BOM update workflow."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.models import SessionData
from src.core.orchestrator import run_question_turn, _run_bom_task_background
from src.core.session import InMemorySessionStore


class TestAsyncBOMWorkflow:
    """Test background BOM task execution and state management."""

    @pytest.mark.asyncio
    async def test_run_question_turn_spawns_background_task(self):
        """Verify run_question_turn spawns BOM task without blocking."""
        # Setup
        session_store = InMemorySessionStore()
        session_id = "test-session-1"
        
        mock_client = MagicMock()
        mock_agent = MagicMock()
        mock_thread = MagicMock()
        
        # Mock Question Agent creation and streaming
        with patch("src.core.orchestrator.create_question_agent") as mock_create_agent, \
             patch("src.core.orchestrator.should_trigger_bom_update", return_value=True), \
             patch("src.core.orchestrator._run_bom_task_background") as mock_bom_task:
            
            mock_create_agent.return_value = mock_agent
            mock_agent.get_new_thread.return_value = mock_thread
            
            # Simulate agent streaming response with service mention
            async def mock_stream(*args, **kwargs):
                class MockUpdate:
                    text = "Let's use Azure App Service for your web application."
                yield MockUpdate()
            
            mock_agent.run_stream = mock_stream
            
            # Run question turn
            result = await run_question_turn(
                client=mock_client,
                session_store=session_store,
                session_id=session_id,
                user_message="I need a web app",
                enable_incremental_bom=True
            )
            
            # Verify response returned immediately (not blocked)
            assert result is not None
            assert "response" in result
            assert "bom_task_status" in result
            assert result["bom_task_status"] == "queued"
            
            # Verify session state
            session_data = session_store.get(session_id)
            assert session_data is not None
            assert session_data.bom_task_status == "queued"
            assert session_data.bom_task_handle is not None
            
            # Wait a bit for background task to potentially start
            await asyncio.sleep(0.1)
            
            # Clean up any spawned tasks
            if session_data.bom_task_handle and not session_data.bom_task_handle.done():
                session_data.bom_task_handle.cancel()
                try:
                    await session_data.bom_task_handle
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_background_task_state_transitions(self):
        """Verify BOM task updates session state through lifecycle."""
        # Setup
        session_store = InMemorySessionStore()
        session_id = "test-session-2"
        
        # Initialize session
        thread = MagicMock()
        session_data = SessionData(thread=thread, history=[])
        session_data.bom_task_status = "idle"
        session_store.set(session_id, session_data)
        
        mock_client = MagicMock()
        
        # Mock run_incremental_bom_update to return quickly
        async def mock_bom_update(*args, **kwargs):
            await asyncio.sleep(0.05)  # Simulate fast BOM generation
            return {"bom_items": [{"serviceName": "App Service"}]}
        
        with patch("src.core.orchestrator.run_incremental_bom_update", side_effect=mock_bom_update):
            # Run background task
            await _run_bom_task_background(
                client=mock_client,
                session_store=session_store,
                session_id=session_id,
                recent_context="user: I need a web app"
            )
            
            # Verify final state
            session_data = session_store.get(session_id)
            assert session_data.bom_task_status == "complete"
            assert session_data.bom_last_update is not None
            assert session_data.bom_task_error is None

    @pytest.mark.asyncio
    async def test_background_task_handles_timeout(self):
        """Verify BOM task handles timeout gracefully."""
        # Setup
        session_store = InMemorySessionStore()
        session_id = "test-session-timeout"
        
        # Initialize session
        thread = MagicMock()
        session_data = SessionData(thread=thread, history=[])
        session_store.set(session_id, session_data)
        
        mock_client = MagicMock()
        
        # Mock run_incremental_bom_update to timeout
        async def mock_slow_bom(*args, **kwargs):
            await asyncio.sleep(35)  # Exceeds 30s timeout
        
        with patch("src.core.orchestrator.run_incremental_bom_update", side_effect=mock_slow_bom), \
             patch("src.core.orchestrator.increment_errors") as mock_increment_errors:
            # Run background task (should timeout)
            await _run_bom_task_background(
                client=mock_client,
                session_store=session_store,
                session_id=session_id,
                recent_context="user: Complex requirements"
            )
            
            # Verify error state
            session_data = session_store.get(session_id)
            assert session_data.bom_task_status == "error"
            assert session_data.bom_task_error is not None
            assert "timed out" in session_data.bom_task_error.lower()
            
            # Verify metrics were incremented
            mock_increment_errors.assert_called_once_with("bom_timeout", session_id=session_id)

    @pytest.mark.asyncio
    async def test_background_task_handles_exception(self):
        """Verify BOM task handles exceptions gracefully."""
        # Setup
        session_store = InMemorySessionStore()
        session_id = "test-session-error"
        
        # Initialize session
        thread = MagicMock()
        session_data = SessionData(thread=thread, history=[])
        session_store.set(session_id, session_data)
        
        mock_client = MagicMock()
        
        # Mock run_incremental_bom_update to raise exception
        async def mock_failing_bom(*args, **kwargs):
            raise ValueError("MCP server unavailable")
        
        with patch("src.core.orchestrator.run_incremental_bom_update", side_effect=mock_failing_bom), \
             patch("src.core.orchestrator.increment_errors") as mock_increment_errors:
            # Run background task (should handle error)
            await _run_bom_task_background(
                client=mock_client,
                session_store=session_store,
                session_id=session_id,
                recent_context="user: Some input"
            )
            
            # Verify error state
            session_data = session_store.get(session_id)
            assert session_data.bom_task_status == "error"
            assert session_data.bom_task_error is not None
            assert "failed" in session_data.bom_task_error.lower()
            
            # Verify metrics were incremented
            mock_increment_errors.assert_called_once_with("bom_task_failure", session_id=session_id)

    @pytest.mark.asyncio
    async def test_task_cancellation_on_new_request(self):
        """Verify previous BOM task is cancelled when new one starts."""
        # Setup
        session_store = InMemorySessionStore()
        session_id = "test-session-cancel"
        
        mock_client = MagicMock()
        mock_agent = MagicMock()
        mock_thread = MagicMock()
        
        # Mock Question Agent
        with patch("src.core.orchestrator.create_question_agent") as mock_create_agent, \
             patch("src.core.orchestrator.should_trigger_bom_update", return_value=True):
            
            mock_create_agent.return_value = mock_agent
            mock_agent.get_new_thread.return_value = mock_thread
            
            # Simulate agent streaming
            async def mock_stream(*args, **kwargs):
                class MockUpdate:
                    text = "Azure App Service"
                yield MockUpdate()
            
            mock_agent.run_stream = mock_stream
            
            # First request - spawns BOM task
            result1 = await run_question_turn(
                client=mock_client,
                session_store=session_store,
                session_id=session_id,
                user_message="I need a web app",
                enable_incremental_bom=True
            )
            
            session_data = session_store.get(session_id)
            first_task = session_data.bom_task_handle
            assert first_task is not None
            assert not first_task.done()
            
            # Second request - should cancel first task
            result2 = await run_question_turn(
                client=mock_client,
                session_store=session_store,
                session_id=session_id,
                user_message="Actually, make it bigger",
                enable_incremental_bom=True
            )
            
            # Wait for cancellation
            await asyncio.sleep(0.1)
            
            # Verify first task was cancelled
            assert first_task.done()
            assert first_task.cancelled()
            
            # Verify second task is running
            session_data = session_store.get(session_id)
            second_task = session_data.bom_task_handle
            assert second_task is not None
            assert second_task != first_task
            
            # Clean up
            if second_task and not second_task.done():
                second_task.cancel()
                try:
                    await second_task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_non_blocking_behavior(self):
        """Verify chat response returns before BOM task completes."""
        # Setup
        session_store = InMemorySessionStore()
        session_id = "test-session-nonblocking"
        
        mock_client = MagicMock()
        mock_agent = MagicMock()
        mock_thread = MagicMock()
        
        # Track timing
        chat_complete_time = None
        bom_complete_time = None
        
        with patch("src.core.orchestrator.create_question_agent") as mock_create_agent, \
             patch("src.core.orchestrator.should_trigger_bom_update", return_value=True), \
             patch("src.core.orchestrator.run_incremental_bom_update") as mock_bom_update:
            
            mock_create_agent.return_value = mock_agent
            mock_agent.get_new_thread.return_value = mock_thread
            
            # Simulate agent streaming
            async def mock_stream(*args, **kwargs):
                class MockUpdate:
                    text = "Azure SQL Database"
                yield MockUpdate()
            
            mock_agent.run_stream = mock_stream
            
            # Mock BOM update with delay
            async def slow_bom_update(*args, **kwargs):
                nonlocal bom_complete_time
                await asyncio.sleep(0.2)  # Simulate slow BOM generation
                bom_complete_time = asyncio.get_event_loop().time()
                return {"bom_items": [{"serviceName": "SQL Database"}]}
            
            mock_bom_update.side_effect = slow_bom_update
            
            # Run question turn
            start_time = asyncio.get_event_loop().time()
            result = await run_question_turn(
                client=mock_client,
                session_store=session_store,
                session_id=session_id,
                user_message="I need a database",
                enable_incremental_bom=True
            )
            chat_complete_time = asyncio.get_event_loop().time()
            
            # Verify chat response returned immediately (before BOM completes)
            assert result is not None
            assert (chat_complete_time - start_time) < 0.15  # Should be fast
            
            # Wait for BOM task to complete
            session_data = session_store.get(session_id)
            if session_data.bom_task_handle:
                try:
                    await asyncio.wait_for(session_data.bom_task_handle, timeout=1.0)
                except asyncio.TimeoutError:
                    session_data.bom_task_handle.cancel()
            
            # Verify BOM completed after chat response
            if bom_complete_time:
                assert bom_complete_time > chat_complete_time

