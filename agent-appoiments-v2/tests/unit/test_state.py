"""Test state schema definitions (LangGraph 1.0 patterns)."""
import pytest
from typing import get_type_hints
from src.state import ConversationState, AppointmentState, validate_transition, VALID_TRANSITIONS


class TestStateSchema:
    """Test state schema structure."""

    def test_conversation_state_enum_complete(self):
        """All conversation states are defined."""
        required_states = [
            "COLLECT_SERVICE",
            "SHOW_AVAILABILITY",
            "COLLECT_DATE",
            "COLLECT_TIME",
            "COLLECT_NAME",
            "COLLECT_EMAIL",
            "COLLECT_PHONE",
            "SHOW_SUMMARY",
            "CONFIRM",
            "CREATE_APPOINTMENT",
            "COMPLETE",
        ]

        for state in required_states:
            assert hasattr(ConversationState, state)

    def test_appointment_state_has_messages(self):
        """AppointmentState has messages field with add_messages reducer."""
        hints = get_type_hints(AppointmentState, include_extras=True)
        assert "messages" in hints
        # Verify it's Annotated with add_messages
        assert hasattr(hints["messages"], "__metadata__")

    def test_appointment_state_has_current_state(self):
        """AppointmentState tracks current conversation state."""
        hints = get_type_hints(AppointmentState)
        assert "current_state" in hints

    def test_appointment_state_has_collected_data(self):
        """AppointmentState has structured data collection."""
        hints = get_type_hints(AppointmentState)
        assert "collected_data" in hints


class TestStateTransitions:
    """Test state machine transition guards."""

    def test_valid_transition_collect_service_to_show_availability(self):
        """Valid: COLLECT_SERVICE → SHOW_AVAILABILITY."""
        assert validate_transition(
            ConversationState.COLLECT_SERVICE,
            ConversationState.SHOW_AVAILABILITY
        ) is True

    def test_invalid_transition_skip_states(self):
        """Invalid: Cannot skip states."""
        assert validate_transition(
            ConversationState.COLLECT_SERVICE,
            ConversationState.COLLECT_DATE
        ) is False

    def test_invalid_transition_backward(self):
        """Invalid: No backward transitions."""
        assert validate_transition(
            ConversationState.COLLECT_EMAIL,
            ConversationState.COLLECT_NAME
        ) is False

    def test_complete_state_transitions_to_post_action(self):
        """COMPLETE state transitions to POST_ACTION for continued service (v1.2)."""
        assert ConversationState.POST_ACTION in VALID_TRANSITIONS[ConversationState.COMPLETE]

    def test_all_states_have_transitions_defined(self):
        """Every state has transition rules."""
        for state in ConversationState:
            assert state in VALID_TRANSITIONS
