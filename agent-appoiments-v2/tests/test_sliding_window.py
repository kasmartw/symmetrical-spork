"""Test sliding window message management."""
import pytest
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.agent import apply_sliding_window
from src.state import ConversationState
from tests.utils.latency_utils import LatencyTracker


def test_sliding_window_keeps_system_message():
    """System message should always be preserved."""
    messages = [
        SystemMessage(content="System prompt"),
        HumanMessage(content="msg1"),
        AIMessage(content="resp1"),
        HumanMessage(content="msg2"),
        AIMessage(content="resp2"),
    ]

    result = apply_sliding_window(messages, window_size=2)

    # Should keep system message + last 2 messages
    assert len(result) == 3
    assert isinstance(result[0], SystemMessage)
    assert result[0].content == "System prompt"
    assert isinstance(result[1], HumanMessage)
    assert result[1].content == "msg2"
    assert isinstance(result[2], AIMessage)
    assert result[2].content == "resp2"


def test_sliding_window_with_fewer_messages_than_window():
    """When messages < window size, return all messages."""
    messages = [
        SystemMessage(content="System prompt"),
        HumanMessage(content="msg1"),
        AIMessage(content="resp1"),
    ]

    result = apply_sliding_window(messages, window_size=10)

    # Should return all messages unchanged
    assert len(result) == 3
    assert result == messages


def test_sliding_window_preserves_message_order():
    """Messages should maintain chronological order."""
    messages = [
        SystemMessage(content="System prompt"),
        HumanMessage(content="msg1"),
        AIMessage(content="resp1"),
        HumanMessage(content="msg2"),
        AIMessage(content="resp2"),
        HumanMessage(content="msg3"),
        AIMessage(content="resp3"),
        HumanMessage(content="msg4"),
        AIMessage(content="resp4"),
    ]

    result = apply_sliding_window(messages, window_size=4)

    # Should keep system + last 4 messages (2 exchanges)
    assert len(result) == 5
    assert result[0].content == "System prompt"
    assert result[1].content == "msg3"
    assert result[2].content == "resp3"
    assert result[3].content == "msg4"
    assert result[4].content == "resp4"


def test_sliding_window_no_system_message():
    """Should work even if no system message present."""
    messages = [
        HumanMessage(content="msg1"),
        AIMessage(content="resp1"),
        HumanMessage(content="msg2"),
        AIMessage(content="resp2"),
    ]

    result = apply_sliding_window(messages, window_size=2)

    # Should keep last 2 messages only
    assert len(result) == 2
    assert result[0].content == "msg2"
    assert result[1].content == "resp2"


def test_sliding_window_performance():
    """Sliding window should be fast even with many messages."""
    tracker = LatencyTracker()

    # Create large message history
    messages = [SystemMessage(content="System")]
    for i in range(1000):
        messages.append(HumanMessage(content=f"msg{i}"))
        messages.append(AIMessage(content=f"resp{i}"))

    # Measure window application
    with tracker.measure("sliding_window", message_count=len(messages)):
        result = apply_sliding_window(messages, window_size=10)

    stats = tracker.get_stats("sliding_window")

    # Should complete in under 10ms
    assert stats["avg_ms"] < 10, f"Too slow: {stats['avg_ms']:.2f}ms"

    # Should return correct size
    assert len(result) == 11  # 1 system + 10 messages

    print(f"\n✅ Sliding window processed {len(messages)} messages in {stats['avg_ms']:.2f}ms")


def test_agent_node_applies_sliding_window_with_latency(monkeypatch):
    """Integration test: agent_node should apply sliding window and measure latency."""
    from src.agent import agent_node
    from unittest.mock import MagicMock
    from tests.utils.latency_utils import LatencyTracker

    tracker = LatencyTracker()

    # Mock the LLM
    mock_llm = MagicMock()
    mock_response = AIMessage(content="Test response")
    mock_llm.invoke.return_value = mock_response

    # Patch llm_with_tools
    monkeypatch.setattr("src.agent.llm_with_tools", mock_llm)

    # Create state with 15 messages (exceeds window of 10)
    messages = []
    for i in range(15):
        messages.append(HumanMessage(content=f"User message {i}"))
        messages.append(AIMessage(content=f"AI response {i}"))

    state = {
        "messages": messages,
        "current_state": ConversationState.COLLECT_SERVICE,
        "collected_data": {},
        "available_slots": [],
        "retry_count": {}
    }

    # Call agent_node and measure latency
    with tracker.measure("agent_node", message_count=len(messages)):
        result = agent_node(state)

    # Verify LLM was called with windowed messages
    call_args = mock_llm.invoke.call_args[0][0]

    # Should have system message + last 10 conversation messages
    assert len(call_args) == 11  # 1 system + 10 windowed
    assert isinstance(call_args[0], SystemMessage)

    # Last user message should be "User message 14"
    assert "User message 14" in call_args[-2].content

    # Print latency stats
    stats = tracker.get_stats("agent_node")
    print(f"\n✅ agent_node with {len(messages)} messages: {stats['avg_ms']:.2f}ms")
