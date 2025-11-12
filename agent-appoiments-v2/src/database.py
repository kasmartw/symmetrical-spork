"""Database and checkpointing setup.

Production Pattern:
- PostgresSaver with connection pooling
- Automatic table creation
- Thread-safe operations
"""
import os
from contextlib import contextmanager
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver


def get_connection_pool():
    """
    Create connection pool for PostgreSQL.

    Pattern: Connection pooling for horizontal scaling.
    Pool size: 10 connections (adjust based on load)
    """
    db_uri = os.getenv("DATABASE_URL")
    if not db_uri:
        raise ValueError("DATABASE_URL environment variable required")

    return ConnectionPool(
        conninfo=db_uri,
        min_size=2,
        max_size=10,
    )


@contextmanager
def get_postgres_saver():
    """
    Get PostgresSaver with automatic cleanup.

    Usage:
        with get_postgres_saver() as saver:
            graph = builder.compile(checkpointer=saver)

    Yields:
        PostgresSaver instance
    """
    pool = get_connection_pool()

    try:
        with pool.connection() as conn:
            saver = PostgresSaver(conn)
            yield saver
    finally:
        pool.close()
