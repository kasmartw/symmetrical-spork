"""Test session management functionality."""
import pytest
from uuid import UUID
from datetime import datetime, timedelta, UTC
from src.session_manager import SessionManager, SessionNotFoundError


@pytest.fixture
def session_manager():
    """Create SessionManager with in-memory database."""
    return SessionManager(database_url="sqlite:///:memory:")


def test_create_session_generates_thread_id(session_manager):
    """Creating session should generate unique thread_id."""
    session_id = "550e8400-e29b-41d4-a716-446655440000"
    org_id = "org-123"

    thread_id = session_manager.create_session(session_id, org_id)

    assert isinstance(thread_id, str)
    assert len(thread_id) > 0
    assert thread_id != session_id  # Should be different


def test_get_thread_id_retrieves_existing_session(session_manager):
    """Getting thread_id for existing session should return same value."""
    session_id = "550e8400-e29b-41d4-a716-446655440000"
    org_id = "org-123"

    thread_id_1 = session_manager.create_session(session_id, org_id)
    thread_id_2 = session_manager.get_thread_id(session_id)

    assert thread_id_1 == thread_id_2


def test_get_thread_id_raises_for_nonexistent_session(session_manager):
    """Getting thread_id for non-existent session should raise error."""
    with pytest.raises(SessionNotFoundError):
        session_manager.get_thread_id("nonexistent-session-id")


def test_cleanup_expired_sessions_removes_old_sessions(session_manager):
    """Cleanup should remove sessions older than 48 hours."""
    # Create old session (manually set timestamp)
    old_session_id = "old-session-id"
    session_manager.create_session(old_session_id, "org-123")

    # Manually update timestamp to 49 hours ago
    session_manager._update_last_activity(
        old_session_id,
        datetime.now(UTC) - timedelta(hours=49)
    )

    # Create recent session
    recent_session_id = "recent-session-id"
    session_manager.create_session(recent_session_id, "org-123")

    # Cleanup expired sessions
    deleted_count = session_manager.cleanup_expired_sessions(max_age_hours=48)

    assert deleted_count == 1

    # Old session should be gone
    with pytest.raises(SessionNotFoundError):
        session_manager.get_thread_id(old_session_id)

    # Recent session should still exist
    assert session_manager.get_thread_id(recent_session_id) is not None
