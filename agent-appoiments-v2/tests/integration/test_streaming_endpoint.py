"""Test /api/v1/chat/stream endpoint."""
import pytest
import json
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.fixture
def client():
    """Create FastAPI test client."""
    from src.api_server import app
    return TestClient(app)


def test_streaming_endpoint_returns_sse_events(client, monkeypatch):
    """POST /api/v1/chat/stream should return Server-Sent Events."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    session_id = str(uuid4())

    with client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={
            "message": "Hello",
            "session_id": session_id,
            "org_id": "org-test-123"
        }
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                data_str = line[6:]  # Remove "data: " prefix
                event_data = json.loads(data_str)
                events.append(event_data)

        # Should have at least one event
        assert len(events) > 0

        # Last event should have done=True
        assert events[-1]["done"] is True


def test_streaming_endpoint_streams_chunks(client, monkeypatch):
    """Streaming should send multiple chunks during processing."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    session_id = str(uuid4())

    with client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={
            "message": "I need an appointment for consultation",
            "session_id": session_id,
            "org_id": "org-test-123"
        }
    ) as response:
        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                event_data = json.loads(data_str)
                events.append(event_data)

        # Should have multiple chunks (agent processes through steps)
        assert len(events) >= 2

        # Events should have chunk field
        for event in events[:-1]:  # All except last
            assert "chunk" in event
