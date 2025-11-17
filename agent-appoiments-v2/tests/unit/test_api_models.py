"""Test API request/response models."""
import pytest
from pydantic import ValidationError
from src.api.models import ChatRequest, ChatResponse


def test_chat_request_valid():
    """Valid chat request should pass validation."""
    req = ChatRequest(
        message="Hello",
        session_id="550e8400-e29b-41d4-a716-446655440000",
        org_id="org-123"
    )
    assert req.message == "Hello"
    assert str(req.session_id) == "550e8400-e29b-41d4-a716-446655440000"


def test_chat_request_empty_message_fails():
    """Empty message should fail validation."""
    with pytest.raises(ValidationError) as exc_info:
        ChatRequest(
            message="",
            session_id="550e8400-e29b-41d4-a716-446655440000",
            org_id="org-123"
        )
    assert "message" in str(exc_info.value)


def test_chat_request_too_long_message_fails():
    """Message exceeding 2000 chars should fail."""
    with pytest.raises(ValidationError):
        ChatRequest(
            message="x" * 2001,
            session_id="550e8400-e29b-41d4-a716-446655440000",
            org_id="org-123"
        )


def test_chat_request_invalid_uuid_fails():
    """Invalid UUID should fail validation."""
    with pytest.raises(ValidationError):
        ChatRequest(
            message="Hello",
            session_id="not-a-uuid",
            org_id="org-123"
        )


def test_chat_response_valid():
    """Valid chat response should serialize correctly."""
    resp = ChatResponse(
        response="Appointment created!",
        session_id="550e8400-e29b-41d4-a716-446655440000",
        metadata={"state": "COMPLETE"}
    )
    assert resp.response == "Appointment created!"
    assert resp.metadata["state"] == "COMPLETE"
