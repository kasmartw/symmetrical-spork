"""Test state schema definitions (LangGraph 1.0 patterns)."""
import pytest
from typing import get_type_hints
from src.state import ConversationState, AppointmentState


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
