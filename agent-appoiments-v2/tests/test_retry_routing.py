"""Tests for retry handler routing optimization."""
import pytest
from langchain_core.messages import AIMessage, ToolMessage
from src.agent import should_use_retry_handler
from src.state import AppointmentState, ConversationState


class TestRetryHandlerRouting:
    """Test routing decisions for retry handler."""

    def test_should_use_retry_in_cancel_verify(self):
        """Test routing uses retry_handler in CANCEL_VERIFY state."""
        state: AppointmentState = {
            "messages": [],
            "current_state": ConversationState.CANCEL_VERIFY,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = should_use_retry_handler(state)
        assert result == "retry_handler", "Should route to retry_handler in CANCEL_VERIFY"

    def test_should_use_retry_in_reschedule_verify(self):
        """Test routing uses retry_handler in RESCHEDULE_VERIFY state."""
        state: AppointmentState = {
            "messages": [],
            "current_state": ConversationState.RESCHEDULE_VERIFY,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = should_use_retry_handler(state)
        assert result == "retry_handler", "Should route to retry_handler in RESCHEDULE_VERIFY"

    def test_should_skip_retry_in_collect_service(self):
        """Test routing skips retry_handler in COLLECT_SERVICE."""
        state: AppointmentState = {
            "messages": [],
            "current_state": ConversationState.COLLECT_SERVICE,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = should_use_retry_handler(state)
        assert result == "agent", "Should skip retry_handler and go direct to agent"

    def test_should_skip_retry_in_collect_time_preference(self):
        """Test routing skips retry_handler in COLLECT_TIME_PREFERENCE."""
        state: AppointmentState = {
            "messages": [],
            "current_state": ConversationState.COLLECT_TIME_PREFERENCE,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = should_use_retry_handler(state)
        assert result == "agent", "Should skip retry_handler in COLLECT_TIME_PREFERENCE"

    def test_should_skip_retry_in_collect_date(self):
        """Test routing skips retry_handler in COLLECT_DATE."""
        state: AppointmentState = {
            "messages": [],
            "current_state": ConversationState.COLLECT_DATE,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = should_use_retry_handler(state)
        assert result == "agent", "Should skip in COLLECT_DATE"

    def test_should_skip_retry_in_collect_email(self):
        """Test routing skips retry_handler in COLLECT_EMAIL."""
        state: AppointmentState = {
            "messages": [],
            "current_state": ConversationState.COLLECT_EMAIL,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = should_use_retry_handler(state)
        assert result == "agent", "Should skip in COLLECT_EMAIL"

    def test_should_skip_retry_in_confirm(self):
        """Test routing skips retry_handler in CONFIRM."""
        state: AppointmentState = {
            "messages": [],
            "current_state": ConversationState.CONFIRM,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = should_use_retry_handler(state)
        assert result == "agent", "Should skip in CONFIRM"

    def test_should_skip_retry_in_post_action(self):
        """Test routing skips retry_handler in POST_ACTION."""
        state: AppointmentState = {
            "messages": [],
            "current_state": ConversationState.POST_ACTION,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = should_use_retry_handler(state)
        assert result == "agent", "Should skip in POST_ACTION"
