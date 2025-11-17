"""
Evaluation test for prebuilt agent vs custom agent.

This test determines if we should use prebuilt or continue custom optimization.
"""
import pytest
import time
import asyncio
from langchain_core.messages import HumanMessage
from src.agent import create_graph as create_custom_graph
from src.agent_prebuilt import create_prebuilt_graph


@pytest.mark.asyncio
async def test_prebuilt_functional_booking():
    """Test that prebuilt agent can complete full booking flow."""
    graph = create_prebuilt_graph()
    config = {"configurable": {"thread_id": "eval-booking", "recursion_limit": 10}}

    # Simulate full booking conversation
    messages = [
        "I want to book an appointment",
        "General Consultation",
        "Morning",
        "Tomorrow at 9am",
        "John Doe",
        "john@example.com",
        "5551234567",
        "yes"
    ]

    state = {"messages": []}
    for msg in messages:
        state["messages"].append(HumanMessage(content=msg))
        result = graph.invoke(state, config)
        state = result

    # Verify booking completed
    last_message = str(result["messages"][-1].content)
    assert "APPT-" in last_message or "confirmation" in last_message.lower(), \
        "Booking did not complete with confirmation number"

    print("✅ Prebuilt agent: Booking flow works")


@pytest.mark.asyncio
async def test_prebuilt_functional_cancellation():
    """Test that prebuilt agent can cancel appointments."""
    graph = create_prebuilt_graph()
    config = {"configurable": {"thread_id": "eval-cancel", "recursion_limit": 10}}

    # Simplified cancel test
    messages = [
        "Cancel my appointment",
        "APPT-12345"
    ]

    state = {"messages": []}
    for msg in messages:
        state["messages"].append(HumanMessage(content=msg))
        result = graph.invoke(state, config)
        state = result

    # Should ask for confirmation or show appointment details
    assert len(result["messages"]) > len(messages)
    print("✅ Prebuilt agent: Cancellation flow works")


@pytest.mark.performance
@pytest.mark.asyncio
async def test_compare_prebuilt_vs_custom_performance():
    """
    CRITICAL TEST: Compare prebuilt vs custom agent performance.

    Decision criteria:
    - If prebuilt is within 20% of custom → USE PREBUILT (less maintenance)
    - If prebuilt is >20% slower → CONTINUE CUSTOM OPTIMIZATION
    """
    custom_graph = create_custom_graph()
    prebuilt_graph = create_prebuilt_graph()

    test_flow = [
        "Book appointment",
        "General Consultation",
        "Morning",
        "Tomorrow at 9am",
        "Jane Smith",
        "jane@example.com",
        "5559876543",
        "yes"
    ]

    # Test custom agent
    custom_config = {"configurable": {"thread_id": "perf-custom", "recursion_limit": 10}}
    custom_state = {"messages": []}
    start = time.time()
    for msg in test_flow:
        custom_state["messages"].append(HumanMessage(content=msg))
        result_custom = custom_graph.invoke(custom_state, custom_config)
        custom_state = result_custom
    custom_time = time.time() - start

    # Test prebuilt agent
    prebuilt_config = {"configurable": {"thread_id": "perf-prebuilt", "recursion_limit": 10}}
    prebuilt_state = {"messages": []}
    start = time.time()
    for msg in test_flow:
        prebuilt_state["messages"].append(HumanMessage(content=msg))
        result_prebuilt = prebuilt_graph.invoke(prebuilt_state, prebuilt_config)
        prebuilt_state = result_prebuilt
    prebuilt_time = time.time() - start

    # Calculate difference
    diff_pct = ((prebuilt_time / custom_time - 1) * 100) if custom_time > 0 else 0

    print("\n" + "="*80)
    print("📊 PREBUILT vs CUSTOM PERFORMANCE COMPARISON")
    print("="*80)
    print(f"Custom Agent:   {custom_time:.2f}s")
    print(f"Prebuilt Agent: {prebuilt_time:.2f}s")
    print(f"Difference:     {abs(diff_pct):.1f}% ({'prebuilt faster' if prebuilt_time < custom_time else 'custom faster'})")
    print("="*80)

    # Decision criteria
    if prebuilt_time <= custom_time * 1.2:  # Within 20%
        print("\n✅ RECOMMENDATION: USE PREBUILT AGENT")
        print("   Reasons:")
        print("   - Performance competitive with custom")
        print("   - Less code to maintain")
        print("   - Battle-tested optimizations")
        print("   - Automatic updates from LangGraph")
    else:
        print("\n⚠️  RECOMMENDATION: CONTINUE CUSTOM OPTIMIZATION")
        print("   Reasons:")
        print(f"   - Prebuilt is {abs(diff_pct):.1f}% slower (>20% threshold)")
        print("   - Custom optimization likely to yield better results")

    # Informational only - no hard assertion
    # Team decides based on printed recommendation


@pytest.mark.asyncio
async def test_prebuilt_state_compatibility():
    """Test if prebuilt agent's state is compatible with our needs."""
    graph = create_prebuilt_graph()
    config = {"configurable": {"thread_id": "eval-state", "recursion_limit": 10}}

    state = {"messages": [HumanMessage(content="Hello")]}
    result = graph.invoke(state, config)

    # Check state structure
    assert "messages" in result
    assert len(result["messages"]) > 1

    # Check if we can extract conversation context
    # (Prebuilt doesn't have current_state field, must infer from messages)
    print("✅ Prebuilt agent: State structure compatible")
