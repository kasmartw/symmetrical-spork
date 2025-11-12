"""Unit tests for retry handler logic."""
import pytest
from langchain_core.messages import ToolMessage, AIMessage
from src.agent import retry_handler_node
from src.state import ConversationState


def test_retry_handler_increments_count_on_error():
    """Test that retry_handler increments count when tool returns error."""
    state = {
        "messages": [
            ToolMessage(content="[ERROR] Appointment APPT-9999 not found.", tool_call_id="test")
        ],
        "current_state": ConversationState.RESCHEDULE_VERIFY,
        "retry_count": {},
        "collected_data": {},
        "available_slots": []
    }

    result = retry_handler_node(state)

    assert "retry_count" in result
    assert result["retry_count"]["reschedule"] == 1


def test_retry_handler_escalates_after_2_failures():
    """Test that retry_handler escalates to POST_ACTION after 2 failures."""
    state = {
        "messages": [
            ToolMessage(content="[ERROR] Appointment APPT-9999 not found.", tool_call_id="test")
        ],
        "current_state": ConversationState.RESCHEDULE_VERIFY,
        "retry_count": {"reschedule": 1},  # Already failed once
        "collected_data": {},
        "available_slots": []
    }

    result = retry_handler_node(state)

    assert "current_state" in result
    assert result["current_state"] == ConversationState.POST_ACTION
    assert result["retry_count"]["reschedule"] == 2
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert "cannot find your appointment" in result["messages"][0].content.lower()


def test_retry_handler_does_nothing_on_success():
    """Test that retry_handler does nothing when tool succeeds."""
    state = {
        "messages": [
            ToolMessage(content="[APPOINTMENT] Current appointment details:\nConfirmation: APPT-1234", tool_call_id="test")
        ],
        "current_state": ConversationState.RESCHEDULE_VERIFY,
        "retry_count": {},
        "collected_data": {},
        "available_slots": []
    }

    result = retry_handler_node(state)

    assert result == {}


def test_retry_handler_ignores_other_states():
    """Test that retry_handler only works in verification states."""
    state = {
        "messages": [
            ToolMessage(content="[ERROR] Some error", tool_call_id="test")
        ],
        "current_state": ConversationState.RESCHEDULE_SELECT_DATETIME,
        "retry_count": {},
        "collected_data": {},
        "available_slots": []
    }

    result = retry_handler_node(state)

    assert result == {}


def test_retry_handler_works_for_cancel():
    """Test that retry_handler works for cancellation flow too."""
    state = {
        "messages": [
            ToolMessage(content="[ERROR] Appointment APPT-9999 not found.", tool_call_id="test")
        ],
        "current_state": ConversationState.CANCEL_VERIFY,
        "retry_count": {},
        "collected_data": {},
        "available_slots": []
    }

    result = retry_handler_node(state)

    assert "retry_count" in result
    assert result["retry_count"]["cancel"] == 1
