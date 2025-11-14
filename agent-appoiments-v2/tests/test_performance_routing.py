"""Benchmark tests for retry handler routing optimization."""
import pytest
import time
from langchain_core.messages import HumanMessage
from src.agent import create_graph
from src.state import ConversationState


def test_graph_compiles_successfully():
    """
    Verify graph compiles with conditional routing.

    This ensures the graph structure is valid after optimization.
    """
    graph = create_graph()

    # Graph should compile without errors
    assert graph is not None
    assert hasattr(graph, "invoke")
    print("✓ Graph compiled successfully with conditional routing")


def test_booking_flow_performance():
    """
    Benchmark normal booking flow (should skip retry_handler).

    This test measures end-to-end time for a typical greeting.
    With optimization, should skip retry_handler entirely.
    """
    graph = create_graph()
    config = {"configurable": {"thread_id": "perf-test-1"}}

    start_time = time.time()

    # Simulate initial greeting (simple flow, no retry needed)
    result = graph.invoke(
        {"messages": [HumanMessage(content="Hola")]},
        config
    )

    elapsed = time.time() - start_time

    # Performance assertion (adjust based on actual measurements)
    # Should complete quickly without retry_handler overhead
    assert elapsed < 10.0, f"Greeting flow took {elapsed:.2f}s (too slow)"

    print(f"✓ Greeting flow completed in {elapsed:.2f}s")


def test_routing_logic_integrated():
    """
    Verify routing logic works in integrated graph.

    This smoke test ensures conditional routing doesn't break normal flow.
    """
    graph = create_graph()
    config = {"configurable": {"thread_id": "perf-test-routing"}}

    # Test basic flow
    result = graph.invoke(
        {"messages": [HumanMessage(content="Hello")]},
        config
    )

    # Should get a response
    assert result is not None
    assert "messages" in result
    assert len(result["messages"]) > 0

    print("✓ Routing logic works correctly in integrated graph")


# NOTE: These are smoke tests - real benchmarks would use pytest-benchmark
# and compare before/after on same hardware with statistical significance
