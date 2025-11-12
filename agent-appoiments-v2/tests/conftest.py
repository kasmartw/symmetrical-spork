"""Shared test fixtures."""
import pytest
import os
from unittest.mock import Mock
from src.state import ConversationState, AppointmentState
from langchain_core.messages import HumanMessage, AIMessage


@pytest.fixture(autouse=True)
def setup_env():
    """Set up environment variables for tests."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    yield


@pytest.fixture
def initial_state() -> AppointmentState:
    """Create initial state."""
    return {
        "messages": [],
        "current_state": ConversationState.COLLECT_SERVICE,
        "collected_data": {},
        "available_slots": []
    }


@pytest.fixture
def mock_llm_response():
    """Create mock LLM response."""
    def _create(content: str, tool_calls: list = None):
        msg = Mock()
        msg.content = content
        msg.tool_calls = tool_calls or []
        return msg
    return _create
