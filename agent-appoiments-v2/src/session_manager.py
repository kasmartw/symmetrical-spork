"""Session management for mapping client session_id to LangGraph thread_id."""
import uuid
from datetime import datetime, timedelta, UTC
from typing import Optional
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, Session as SQLSession
from src.api.database_models import Base, Session


class SessionNotFoundError(Exception):
    """Raised when session_id not found in database."""
    pass


class SessionManager:
    """
    Manages mapping between client session_id and LangGraph thread_id.

    Responsibilities:
    - Generate unique thread_id for each session
    - Store session metadata (org_id, timestamps)
    - Cleanup expired sessions (>48 hours inactive)

    Pattern: Thin wrapper around SQLAlchemy for session persistence.
    """

    def __init__(self, database_url: str):
        """
        Initialize SessionManager with database connection.

        Args:
            database_url: SQLAlchemy connection string
        """
        self.engine = create_engine(database_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_session(self, session_id: str, org_id: str) -> str:
        """
        Create new session with generated thread_id.

        Args:
            session_id: Client-provided session UUID
            org_id: Organization identifier

        Returns:
            Generated thread_id for LangGraph checkpointing
        """
        thread_id = f"thread-{uuid.uuid4()}"

        with self.SessionLocal() as db:
            session = Session(
                session_id=session_id,
                thread_id=thread_id,
                org_id=org_id,
                created_at=datetime.now(UTC),
                last_activity=datetime.now(UTC)
            )
            db.add(session)
            db.commit()

        return thread_id

    def get_thread_id(self, session_id: str) -> str:
        """
        Get thread_id for existing session.

        Args:
            session_id: Client-provided session UUID

        Returns:
            thread_id for LangGraph

        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        with self.SessionLocal() as db:
            session = db.query(Session).filter(Session.session_id == session_id).first()

            if not session:
                raise SessionNotFoundError(f"Session {session_id} not found")

            # Update last_activity timestamp
            session.last_activity = datetime.now(UTC)
            db.commit()

            return session.thread_id

    def get_or_create_thread_id(self, session_id: str, org_id: str) -> str:
        """
        Get existing thread_id or create new session.

        Args:
            session_id: Client-provided session UUID
            org_id: Organization identifier

        Returns:
            thread_id (existing or newly created)
        """
        try:
            return self.get_thread_id(session_id)
        except SessionNotFoundError:
            return self.create_session(session_id, org_id)

    def cleanup_expired_sessions(self, max_age_hours: int = 48) -> int:
        """
        Delete sessions older than max_age_hours.

        Args:
            max_age_hours: Maximum session age in hours (default: 48)

        Returns:
            Number of deleted sessions
        """
        cutoff_time = datetime.now(UTC) - timedelta(hours=max_age_hours)

        with self.SessionLocal() as db:
            deleted = db.query(Session).filter(
                Session.last_activity < cutoff_time
            ).delete()
            db.commit()

        return deleted

    def _update_last_activity(self, session_id: str, timestamp: datetime):
        """Helper for testing - manually update last_activity."""
        with self.SessionLocal() as db:
            session = db.query(Session).filter(Session.session_id == session_id).first()
            if session:
                session.last_activity = timestamp
                db.commit()
