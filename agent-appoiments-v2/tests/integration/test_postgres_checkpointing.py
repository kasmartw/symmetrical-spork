"""Test PostgreSQL checkpointing functionality."""
import pytest
import os
from uuid import uuid4
from langchain_core.messages import HumanMessage
from src.agent import create_production_graph
from src.database import get_postgres_saver


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set - skipping Postgres tests"
)
def test_postgres_saver_persists_conversation():
    """PostgresSaver should persist conversation state across sessions."""
    # Create graph with PostgreSQL checkpointer
    graph = create_production_graph()

    # Session 1: Send first message
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result1 = graph.invoke(
        {"messages": [HumanMessage(content="Hello")]},
        config=config
    )

    assert len(result1["messages"]) > 0

    # Session 2: Continue conversation (should have history)
    result2 = graph.invoke(
        {"messages": [HumanMessage(content="I need an appointment")]},
        config=config
    )

    # Should have messages from both sessions
    assert len(result2["messages"]) > len(result1["messages"])


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set - skipping Postgres tests"
)
def test_postgres_saver_setup_creates_tables():
    """PostgresSaver.setup() should create necessary tables."""
    with get_postgres_saver() as saver:
        # This should not raise an exception
        saver.setup()

        # Verify we can write a checkpoint
        from langgraph.checkpoint.base import Checkpoint
        checkpoint = Checkpoint(
            v=1,
            id=str(uuid4()),
            ts="2025-01-01T00:00:00Z",
            channel_values={},
            channel_versions={},
            versions_seen={}
        )

        # Should succeed without errors
        config = {"configurable": {"thread_id": str(uuid4())}}
        saver.put(config, checkpoint, {})
