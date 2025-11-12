"""Unit tests for state machine structure."""
from src.state import ConversationState, VALID_TRANSITIONS


def test_reschedule_states_exist():
    """Verify all rescheduling states are defined."""
    expected_states = [
        ConversationState.RESCHEDULE_ASK_CONFIRMATION,
        ConversationState.RESCHEDULE_VERIFY,
        ConversationState.RESCHEDULE_SELECT_DATETIME,
        ConversationState.RESCHEDULE_CONFIRM,
        ConversationState.RESCHEDULE_PROCESS,
    ]

    for state in expected_states:
        assert state in ConversationState.__members__.values()


def test_reschedule_transitions_valid():
    """Verify rescheduling flow transitions are defined."""
    # Can enter reschedule from any booking state
    assert ConversationState.RESCHEDULE_ASK_CONFIRMATION in VALID_TRANSITIONS[
        ConversationState.COLLECT_SERVICE
    ]

    # Reschedule flow progression
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

    # Escalation path (after 2 failures)
    assert ConversationState.POST_ACTION in VALID_TRANSITIONS[
        ConversationState.RESCHEDULE_VERIFY
    ]
    assert ConversationState.COLLECT_SERVICE in VALID_TRANSITIONS[
        ConversationState.POST_ACTION
    ]
