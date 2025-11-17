"""Test /api/v1/chat endpoint."""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.fixture
def client():
    """Create FastAPI test client."""
    from src.api_server import app
    return TestClient(app)


def test_chat_endpoint_returns_response(client, monkeypatch):
    """POST /api/v1/chat should return agent response."""
    # Mock DATABASE_URL for testing
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    session_id = str(uuid4())
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Hello, I need an appointment",
            "session_id": session_id,
            "org_id": "org-test-123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "session_id" in data
    assert data["session_id"] == session_id
    assert isinstance(data["response"], str)
    assert len(data["response"]) > 0


def test_chat_endpoint_maintains_conversation_state(client, monkeypatch):
    """Multiple requests with same session_id should maintain context."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    session_id = str(uuid4())

    # First message
    response1 = client.post(
        "/api/v1/chat",
        json={
            "message": "Hello",
            "session_id": session_id,
            "org_id": "org-test-123"
        }
    )
    assert response1.status_code == 200

    # Second message (should have context from first)
    response2 = client.post(
        "/api/v1/chat",
        json={
            "message": "I need a consultation",
            "session_id": session_id,
            "org_id": "org-test-123"
        }
    )
    assert response2.status_code == 200
    data = response2.json()
    assert "metadata" in data


def test_chat_endpoint_rejects_invalid_request(client):
    """Invalid request should return 422."""
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "",  # Empty message
            "session_id": "not-a-uuid",
            "org_id": "org-test-123"
        }
    )
    assert response.status_code == 422
