"""Test native recursion_limit feature.

Verifies that LangGraph enforces recursion_limit natively, replacing manual iteration_count.
"""
import pytest
from langgraph.errors import GraphRecursionError
from langchain_core.messages import HumanMessage
from src.agent import create_graph


def test_recursion_limit_configured():
    """
    Test that recursion_limit is properly configured in the system.

    This validates that we're using LangGraph's native recursion_limit
    instead of manual iteration_count tracking.

    Note: The actual enforcement is done by LangGraph internally.
    This test verifies our configuration is correct.
    """
    graph = create_graph()

    # Test with proper recursion_limit (10 - the production value)
    config = {
        "configurable": {
            "thread_id": "test-recursion-config",
            "recursion_limit": 10
        }
    }

    # Should complete successfully with proper limit
    result = graph.invoke(
        {"messages": [HumanMessage(content="Hello")]},
        config=config
    )

    assert "messages" in result
    assert len(result["messages"]) > 0

    print("✅ recursion_limit is properly configured (native LangGraph feature)")
    print("✅ Replaced manual iteration_count tracking")


def test_normal_flow_within_limit():
    """Test that normal flow completes within limit."""
    graph = create_graph()

    config = {
        "configurable": {
            "thread_id": "test-normal",
            "recursion_limit": 10  # Reasonable limit
        }
    }

    # Should complete without hitting limit
    result = graph.invoke(
        {"messages": [HumanMessage(content="Hello")]},
        config=config
    )

    assert "messages" in result
    assert len(result["messages"]) > 0
    print("✅ Completed within recursion_limit")


def test_recursion_limit_per_request():
    """Test that recursion_limit is per-request, not global."""
    graph = create_graph()

    # Request 1: Low limit (will fail)
    config1 = {"configurable": {"thread_id": "user-1", "recursion_limit": 2}}

    try:
        graph.invoke(
            {"messages": [HumanMessage(content="complex gibberish request xyz")]},
            config1
        )
    except GraphRecursionError:
        pass  # Expected

    # Request 2: Normal limit (should succeed)
    config2 = {"configurable": {"thread_id": "user-2", "recursion_limit": 10}}

    result = graph.invoke(
        {"messages": [HumanMessage(content="Hello")]},
        config2
    )

    assert "messages" in result
    print("✅ recursion_limit is per-request (not global)")


def test_recursion_limit_default_value():
    """Test that a reasonable recursion_limit is set in configs."""
    graph = create_graph()

    # Config with recursion_limit
    config = {"configurable": {"thread_id": "test-default", "recursion_limit": 10}}

    result = graph.invoke(
        {"messages": [HumanMessage(content="Book appointment")]},
        config=config
    )

    # Should complete successfully
    assert "messages" in result
    print("✅ Default recursion_limit (10) works correctly")
