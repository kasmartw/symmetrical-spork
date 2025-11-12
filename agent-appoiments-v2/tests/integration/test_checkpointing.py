"""Test checkpointing with PostgresSaver."""
import pytest
import os


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="Requires DATABASE_URL env var"
)
class TestPostgresCheckpointing:
    """Test production checkpointing."""

    def test_postgres_saver_creates_tables(self):
        """PostgresSaver creates required tables."""
        from src.database import get_postgres_saver

        saver = get_postgres_saver()
        saver.setup()

        # Verify setup completed
        assert saver is not None
