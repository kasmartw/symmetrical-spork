"""Test system prompt stability for automatic caching."""
import pytest
from src.agent import build_system_prompt
from src.state import ConversationState


def test_same_state_produces_identical_prompt():
    """Same state should produce byte-identical prompt (enables caching)."""
    state1 = {
        "current_state": ConversationState.COLLECT_SERVICE,
        "messages": [],
        "collected_data": {},
        "available_slots": [],
        "retry_count": {}
    }

    state2 = {
        "current_state": ConversationState.COLLECT_SERVICE,
        "messages": [],
        "collected_data": {},
        "available_slots": [],
        "retry_count": {}
    }

    prompt1 = build_system_prompt(state1)
    prompt2 = build_system_prompt(state2)

    # Must be byte-identical for OpenAI caching
    assert prompt1 == prompt2
    assert hash(prompt1) == hash(prompt2)


def test_prompt_stability_across_different_message_counts():
    """Prompt should be stable regardless of message history (windowed separately)."""
    state_short = {
        "current_state": ConversationState.COLLECT_SERVICE,
        "messages": ["msg1"],
        "collected_data": {},
        "available_slots": [],
        "retry_count": {}
    }

    state_long = {
        "current_state": ConversationState.COLLECT_SERVICE,
        "messages": ["msg1", "msg2", "msg3", "msg4", "msg5"],
        "collected_data": {},
        "available_slots": [],
        "retry_count": {}
    }

    prompt1 = build_system_prompt(state_short)
    prompt2 = build_system_prompt(state_long)

    # System prompt should NOT depend on message history
    # (messages are handled separately by sliding window)
    assert prompt1 == prompt2


def test_prompt_changes_only_with_conversation_state():
    """Prompt should change ONLY when conversation state changes."""
    state_service = {
        "current_state": ConversationState.COLLECT_SERVICE,
        "messages": [],
        "collected_data": {},
        "available_slots": [],
        "retry_count": {}
    }

    state_email = {
        "current_state": ConversationState.COLLECT_EMAIL,
        "messages": [],
        "collected_data": {},
        "available_slots": [],
        "retry_count": {}
    }

    prompt_service = build_system_prompt(state_service)
    prompt_email = build_system_prompt(state_email)

    # Different conversation states = different prompts (expected)
    assert prompt_service != prompt_email

    # But each should be stable when called again
    assert prompt_service == build_system_prompt(state_service)
    assert prompt_email == build_system_prompt(state_email)


def test_prompt_does_not_include_dynamic_data():
    """Prompt should not include timestamps, IDs, or other dynamic data."""
    import time

    state = {
        "current_state": ConversationState.COLLECT_SERVICE,
        "messages": [],
        "collected_data": {},
        "available_slots": [],
        "retry_count": {}
    }

    prompt1 = build_system_prompt(state)
    time.sleep(0.1)  # Wait a bit
    prompt2 = build_system_prompt(state)

    # Should be identical despite time passing
    assert prompt1 == prompt2

    # Should not contain timestamps
    assert "2025" not in prompt1  # No year
    assert ":" not in prompt1 or "TOOLS:" in prompt1  # No time unless it's a label


def test_prompt_has_no_uuids_or_random_data():
    """Prompt should be deterministic, no UUIDs or random content."""
    state = {
        "current_state": ConversationState.COLLECT_SERVICE,
        "messages": [],
        "collected_data": {"session_id": "abc-123-def"},  # Dynamic data in state
        "available_slots": [],
        "retry_count": {}
    }

    prompt = build_system_prompt(state)

    # Should NOT leak session_id or other dynamic state data into prompt
    assert "abc-123-def" not in prompt
    assert "session_id" not in prompt.lower()

    # Multiple calls should produce identical results
    prompts = [build_system_prompt(state) for _ in range(5)]
    assert len(set(prompts)) == 1, "Prompt should be deterministic"


def test_caching_structure_explanation():
    """Document how OpenAI automatic caching works with our structure."""
    from tests.utils.latency_utils import LatencyTracker

    tracker = LatencyTracker()

    # Simulate first call (cache miss)
    state = {
        "current_state": ConversationState.COLLECT_SERVICE,
        "messages": [],
        "collected_data": {},
        "available_slots": [],
        "retry_count": {}
    }

    with tracker.measure("build_prompt_first"):
        prompt1 = build_system_prompt(state)

    # Simulate second call with same state (cache hit in production)
    with tracker.measure("build_prompt_second"):
        prompt2 = build_system_prompt(state)

    # In our code, both are fast (it's just string building)
    # In production, OpenAI caches the PROCESSING of identical prompts
    assert prompt1 == prompt2

    print("\n" + "="*70)
    print("📊 OpenAI Automatic Caching Explanation")
    print("="*70)
    print("\nHow it works:")
    print("  1. First call: OpenAI processes system prompt (cache miss)")
    print("  2. Second call: Identical prefix detected → cache hit")
    print("  3. Cache hit: 50-90% faster processing + lower cost")
    print("\nOur optimization:")
    print("  • build_system_prompt() returns IDENTICAL string for same state")
    print("  • Messages array: [SystemMessage(prompt), ...windowed...]")
    print("  • OpenAI sees identical position[0] → automatic cache")
    print("\nNo configuration needed - it just works!")
    print("="*70)
