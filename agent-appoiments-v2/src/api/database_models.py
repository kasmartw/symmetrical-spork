"""SQLAlchemy database models for API layer."""
from datetime import datetime, UTC
from sqlalchemy import Column, String, DateTime, Boolean, JSON, create_engine
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


class Organization(Base):
    """Organization configuration table for multi-tenancy."""
    __tablename__ = "organizations"

    org_id = Column(String(100), primary_key=True, index=True)
    org_name = Column(String(200), nullable=True)
    system_prompt = Column(String(5000), nullable=True)
    services = Column(JSON, nullable=False, default=list)  # List of ServiceConfig dicts
    permissions = Column(JSON, nullable=False)  # PermissionsConfig dict
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def __repr__(self):
        return f"<Organization(org_id={self.org_id}, active={self.is_active})>"
