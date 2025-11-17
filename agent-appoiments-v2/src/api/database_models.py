"""SQLAlchemy database models for API layer."""
from datetime import datetime, UTC
from sqlalchemy import Column, String, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


def utc_now():
    """Get current UTC timestamp."""
    return datetime.now(UTC)


class Session(Base):
    """Session tracking table for thread_id mapping."""
    __tablename__ = "sessions"

    session_id = Column(String(255), primary_key=True, index=True)
    thread_id = Column(String(255), nullable=False, unique=True, index=True)
    org_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    last_activity = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def __repr__(self):
        return f"<Session(session_id={self.session_id}, org_id={self.org_id})>"
