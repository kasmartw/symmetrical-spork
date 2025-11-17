"""Database and checkpointing setup.

Production Pattern:
- PostgresSaver with async connection pooling
- Automatic table creation via setup()
- Thread-safe operations
- Proper connection lifecycle management
"""
import os
from contextlib import contextmanager
from typing import Optional
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver


# Global connection pool (initialized on first use)
_connection_pool: Optional[ConnectionPool] = None


def get_connection_pool() -> ConnectionPool:
    """
    Get or create connection pool for PostgreSQL.

    Pattern: Singleton connection pool for horizontal scaling.
    Pool configuration:
    - min_size=2: Minimum connections kept alive
    - max_size=10: Maximum connections (adjust based on load)
    - Connection reuse across requests

    Returns:
        ConnectionPool instance

    Raises:
        ValueError: If DATABASE_URL not set
    """
    global _connection_pool

    if _connection_pool is None:
        db_uri = os.getenv("DATABASE_URL")
        if not db_uri:
            raise ValueError(
                "DATABASE_URL environment variable required. "
                "Format: postgresql://user:password@host:port/database"
            )

        _connection_pool = ConnectionPool(
            conninfo=db_uri,
            min_size=2,
            max_size=10,
            timeout=30,  # Connection acquisition timeout
        )

    return _connection_pool


@contextmanager
def get_postgres_saver():
    """
    Get PostgresSaver with automatic cleanup.

    Context manager pattern ensures proper connection lifecycle.

    Usage:
        with get_postgres_saver() as saver:
            saver.setup()  # Create tables if not exist
            graph = builder.compile(checkpointer=saver)

    Yields:
        PostgresSaver: Configured checkpointer instance
    """
    pool = get_connection_pool()

    try:
        with pool.connection() as conn:
            saver = PostgresSaver(conn)
            yield saver
    finally:
        # Connection returned to pool automatically
        pass


def close_connection_pool():
    """
    Close the global connection pool.

    Call this during application shutdown to gracefully close
    all database connections.

    Usage:
        @app.on_event("shutdown")
        async def shutdown():
            close_connection_pool()
    """
    global _connection_pool

    if _connection_pool is not None:
        _connection_pool.close()
        _connection_pool = None


def init_database():
    """
    Initialize database tables for checkpointing.

    Creates all necessary tables for LangGraph checkpointing.
    Safe to call multiple times (idempotent).

    Usage:
        @app.on_event("startup")
        async def startup():
            init_database()
    """
    with get_postgres_saver() as saver:
        saver.setup()
