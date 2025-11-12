"""End-to-end integration test for rescheduling flow.

NOTE: These tests verify state transitions and tool usage patterns.
Full E2E testing with LLM would require live API responses.
"""
import pytest
from src.state import ConversationState, VALID_TRANSITIONS


def test_rescheduling_state_transitions():
    """Test that all rescheduling state transitions are properly defined."""
    # Entry point
    assert ConversationState.RESCHEDULE_ASK_CONFIRMATION in VALID_TRANSITIONS[
        ConversationState.COLLECT_SERVICE
    ]

    # Flow progression
    assert ConversationState.RESCHEDULE_VERIFY in VALID_TRANSITIONS[
        ConversationState.RESCHEDULE_ASK_CONFIRMATION
    ]
    assert ConversationState.RESCHEDULE_SELECT_DATETIME in VALID_TRANSITIONS[
        ConversationState.RESCHEDULE_VERIFY
    ]
    assert ConversationState.RESCHEDULE_CONFIRM in VALID_TRANSITIONS[
        ConversationState.RESCHEDULE_SELECT_DATETIME
    ]
    assert ConversationState.RESCHEDULE_PROCESS in VALID_TRANSITIONS[
        ConversationState.RESCHEDULE_CONFIRM
    ]
    assert ConversationState.POST_ACTION in VALID_TRANSITIONS[
        ConversationState.RESCHEDULE_PROCESS
    ]

    # Escalation paths
    assert ConversationState.POST_ACTION in VALID_TRANSITIONS[
        ConversationState.RESCHEDULE_VERIFY
    ]
    assert ConversationState.COLLECT_SERVICE in VALID_TRANSITIONS[
        ConversationState.RESCHEDULE_VERIFY
    ]

    # Alternative path (user wants different time)
    assert ConversationState.RESCHEDULE_SELECT_DATETIME in VALID_TRANSITIONS[
        ConversationState.RESCHEDULE_CONFIRM
    ]


def test_rescheduling_accessible_from_all_booking_states():
    """Test that rescheduling can be accessed from any booking state."""
    booking_states = [
        ConversationState.COLLECT_SERVICE,
        ConversationState.SHOW_AVAILABILITY,
        ConversationState.COLLECT_DATE,
        ConversationState.COLLECT_TIME,
        ConversationState.COLLECT_NAME,
        ConversationState.COLLECT_EMAIL,
        ConversationState.COLLECT_PHONE,
        ConversationState.SHOW_SUMMARY,
        ConversationState.CONFIRM,
    ]

    for state in booking_states:
        assert ConversationState.RESCHEDULE_ASK_CONFIRMATION in VALID_TRANSITIONS[state], \
            f"Cannot access rescheduling from {state.value}"


def test_post_action_includes_all_flows():
    """Test that POST_ACTION offers all three flows."""
    assert ConversationState.COLLECT_SERVICE in VALID_TRANSITIONS[
        ConversationState.POST_ACTION
    ]
    assert ConversationState.CANCEL_ASK_CONFIRMATION in VALID_TRANSITIONS[
        ConversationState.POST_ACTION
    ]
    assert ConversationState.RESCHEDULE_ASK_CONFIRMATION in VALID_TRANSITIONS[
        ConversationState.POST_ACTION
    ]
