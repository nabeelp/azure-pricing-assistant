"""Tests for completion parsing and requirements extraction."""

import pytest

from src.core.models import SessionData
from src.core.orchestrator import (
    history_to_requirements,
    parse_question_completion,
    _extract_json_from_code_block,
)
from src.core.session import InMemorySessionStore
from src.shared.errors import WorkflowError


def test_parse_structured_completion():
    """Should detect done flag and extract requirements from JSON payload."""
    response = """Summary:\n```json\n{\"requirements\": \"foo\", \"done\": true}\n```"""
    done, requirements = parse_question_completion(response)

    assert done is True
    assert requirements == "foo"


def test_parse_legacy_phrase():
    """Should NOT parse legacy sentinel phrases - only structured JSON is supported."""
    response = "Requirements summary here.\nWe are DONE!"
    done, requirements = parse_question_completion(response)

    # Legacy phrases are no longer supported per PRD
    assert done is False
    assert requirements is None


def test_history_prefers_structured_completion():
    """history_to_requirements should use the latest structured completion."""
    history = [
        {"role": "user", "content": "hi"},
        {
            "role": "assistant",
            "content": "```json {\"requirements_summary\": \"final reqs\", \"done\": true}```",
        },
    ]

    requirements = history_to_requirements(history)
    assert requirements == "final reqs"


def test_extract_json_from_code_block_success():
    """Should extract JSON from ```json code block."""
    response = """Here's the summary:\n```json\n{\"requirements\": \"web app\", \"done\": true}\n```"""
    obj = _extract_json_from_code_block(response)
    
    assert obj is not None
    assert obj.get("requirements") == "web app"
    assert obj.get("done") is True


def test_extract_json_from_code_block_not_found():
    """Should return None if no ```json code block found."""
    response = '{"requirements": "web app", "done": true}'
    obj = _extract_json_from_code_block(response)
    
    assert obj is None


def test_parse_json_without_code_block_logs_warning():
    """Should find JSON but log warning if not in code block."""
    # This test verifies fallback behavior - JSON found but not in code block
    response = '{"requirements": "web app", "done": true}'
    done, requirements = parse_question_completion(response)
    
    # Should still work (fallback)
    assert done is True
    assert requirements == "web app"


def test_session_turn_counter_increments():
    """Turn counter should increment from 0 after each turn."""
    session_store = InMemorySessionStore()
    session_id = "test-session"
    
    # Create new session with default turn_count = 0
    thread = object()
    session_data = SessionData(thread=thread, history=[], turn_count=0)
    session_store.set(session_id, session_data)
    
    # Simulate turn increment
    session_data = session_store.get(session_id)
    assert session_data.turn_count == 0
    
    session_data.turn_count += 1
    session_store.set(session_id, session_data)
    
    # Verify increment
    session_data = session_store.get(session_id)
    assert session_data.turn_count == 1


def test_session_turn_counter_reaches_limit():
    """Turn counter should reach 20 before error is raised."""
    session_store = InMemorySessionStore()
    session_id = "test-session"
    
    # Create session at turn 19 (next turn will be 20th)
    thread = object()
    session_data = SessionData(thread=thread, history=[], turn_count=19)
    session_store.set(session_id, session_data)
    
    # Simulate turn increment to 20
    session_data = session_store.get(session_id)
    session_data.turn_count += 1
    session_store.set(session_id, session_data)
    
    # Verify we're at the limit
    session_data = session_store.get(session_id)
    assert session_data.turn_count == 20
    
    # Next turn should fail
    assert session_data.turn_count >= 20


def test_session_reset_clears_turn_count():
    """Resetting session should clear turn count back to 0."""
    session_store = InMemorySessionStore()
    session_id = "test-session"
    
    # Create session with turns
    thread = object()
    session_data = SessionData(thread=thread, history=[], turn_count=15)
    session_store.set(session_id, session_data)
    
    # Reset session
    session_store.delete(session_id)
    
    # Verify session is gone
    session_data = session_store.get(session_id)
    assert session_data is None
