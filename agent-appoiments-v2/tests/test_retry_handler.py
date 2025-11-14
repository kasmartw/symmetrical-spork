"""Tests for intelligent retry handler."""
import pytest
from langchain_core.messages import AIMessage, ToolMessage
from src.agent import retry_handler_node
from src.state import AppointmentState, ConversationState


class TestRetryHandler:
    """Test retry handler intelligence."""

    def test_retry_on_not_found_error(self):
        """Test retry increments on 'not found' errors."""
        state: AppointmentState = {
            "messages": [
                ToolMessage(
                    content="[ERROR] Appointment APPT-9999 not found",
                    tool_call_id="test-123"
                )
            ],
            "current_state": ConversationState.CANCEL_VERIFY,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = retry_handler_node(state)

        # Should increment cancel retry count
        assert result.get("retry_count", {}).get("cancel") == 1

    def test_no_retry_on_success(self):
        """Test no retry increment on successful tool responses."""
        state: AppointmentState = {
            "messages": [
                ToolMessage(
                    content="[APPOINTMENT] Current appointment: ...",
                    tool_call_id="test-123"
                )
            ],
            "current_state": ConversationState.RESCHEDULE_VERIFY,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = retry_handler_node(state)

        # Should not increment retry count
        assert result.get("retry_count", {}) == {}

    def test_escalation_after_2_failures(self):
        """Test escalation to POST_ACTION after 2 failures."""
        state: AppointmentState = {
            "messages": [
                ToolMessage(
                    content="[ERROR] Appointment APPT-9999 not found",
                    tool_call_id="test-123"
                )
            ],
            "current_state": ConversationState.RESCHEDULE_VERIFY,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {"reschedule": 1},  # Already 1 failure
        }

        result = retry_handler_node(state)

        # Should escalate to POST_ACTION
        assert result.get("current_state") == ConversationState.POST_ACTION
        # Should have escalation message
        messages = result.get("messages", [])
        assert len(messages) > 0
        assert "cannot find your appointment" in messages[0].content.lower()

    def test_no_action_on_non_verify_states(self):
        """Test handler does nothing outside VERIFY states."""
        state: AppointmentState = {
            "messages": [
                ToolMessage(
                    content="[ERROR] Some error",
                    tool_call_id="test-123"
                )
            ],
            "current_state": ConversationState.COLLECT_SERVICE,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = retry_handler_node(state)

        # Should return empty dict (no changes)
        assert result == {}

    def test_immediate_escalation_on_system_error(self):
        """Test immediate escalation on API/system errors (no retry)."""
        state: AppointmentState = {
            "messages": [
                ToolMessage(
                    content="[ERROR] Could not connect to API: Connection timeout",
                    tool_call_id="test-123"
                )
            ],
            "current_state": ConversationState.CANCEL_VERIFY,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = retry_handler_node(state)

        # Should escalate immediately without retry
        assert result.get("current_state") == ConversationState.POST_ACTION
        messages = result.get("messages", [])
        assert "technical difficulties" in messages[0].content.lower()

    def test_retry_on_user_error(self):
        """Test retry on user errors (wrong confirmation number)."""
        state: AppointmentState = {
            "messages": [
                ToolMessage(
                    content="[ERROR] Appointment APPT-9999 not found",
                    tool_call_id="test-123"
                )
            ],
            "current_state": ConversationState.CANCEL_VERIFY,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = retry_handler_node(state)

        # Should increment retry, not escalate yet
        assert result.get("retry_count", {}).get("cancel") == 1
        assert "current_state" not in result  # No state change yet
