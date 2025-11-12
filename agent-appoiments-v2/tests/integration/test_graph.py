"""Integration tests for graph execution."""
import pytest
from src.agent import create_graph
from src.state import ConversationState
from langchain_core.messages import HumanMessage


class TestGraphExecution:
    """Test graph compilation and execution."""

    def test_graph_compiles_successfully(self):
        """Graph compiles without errors."""
        graph = create_graph()
        assert graph is not None

    def test_graph_has_checkpointer(self):
        """Graph uses InMemorySaver checkpointer."""
        graph = create_graph()
        assert graph.checkpointer is not None

    def test_initial_invocation_with_thread_id(self, initial_state):
        """Graph accepts thread_id in config."""
        graph = create_graph()
        config = {"configurable": {"thread_id": "test-1"}}

        initial_state["messages"].append(
            HumanMessage(content="Hello")
        )

        # Should not raise
        result = graph.invoke(initial_state, config=config)
        assert result is not None
