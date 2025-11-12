"""Integration test for cancellation API endpoint.

Tests the new PATCH endpoint that changes appointment status to 'cancelled'
without deleting the appointment record.
"""
import pytest
import requests
from src import config


BASE_URL = config.MOCK_API_BASE_URL


def test_cancel_appointment_success():
    """Test successful appointment cancellation (changes status, doesn't delete)."""
    # Step 1: Create an appointment first
    appointment_data = {
        "service_id": "srv-001",
        "date": "2025-12-15",
        "start_time": "10:00",
        "client": {
            "name": "Test User",
            "email": "test@example.com",
            "phone": "5551234567"
        }
    }

    create_response = requests.post(f"{BASE_URL}/appointments", json=appointment_data)
    assert create_response.status_code == 201

    created = create_response.json()
    confirmation_number = created["appointment"]["confirmation_number"]
    assert created["appointment"]["status"] == "confirmed"

    # Step 2: Cancel the appointment using PATCH
    cancel_response = requests.patch(f"{BASE_URL}/appointments/{confirmation_number}")
    assert cancel_response.status_code == 200

    cancel_data = cancel_response.json()
    assert cancel_data["success"] is True
    assert "cancelled" in cancel_data["message"].lower()
    assert cancel_data["appointment"]["status"] == "cancelled"
    assert "cancelled_at" in cancel_data["appointment"]

    # Step 3: Verify appointment still exists (not deleted) with cancelled status
    get_response = requests.get(f"{BASE_URL}/appointments/{confirmation_number}")
    assert get_response.status_code == 200

    get_data = get_response.json()
    assert get_data["appointment"]["status"] == "cancelled"
    assert get_data["appointment"]["confirmation_number"] == confirmation_number


def test_cancel_appointment_not_found():
    """Test cancellation with invalid confirmation number."""
    response = requests.patch(f"{BASE_URL}/appointments/APPT-99999")

    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert "not found" in data["error"].lower()


def test_cancel_already_cancelled():
    """Test cancelling an appointment that's already cancelled."""
    # Step 1: Create and cancel an appointment
    appointment_data = {
        "service_id": "srv-001",
        "date": "2025-12-15",
        "start_time": "11:00",
        "client": {
            "name": "Test User 2",
            "email": "test2@example.com",
            "phone": "5557654321"
        }
    }

    create_response = requests.post(f"{BASE_URL}/appointments", json=appointment_data)
    confirmation_number = create_response.json()["appointment"]["confirmation_number"]

    # First cancellation
    first_cancel = requests.patch(f"{BASE_URL}/appointments/{confirmation_number}")
    assert first_cancel.status_code == 200

    # Step 2: Try to cancel again
    second_cancel = requests.patch(f"{BASE_URL}/appointments/{confirmation_number}")

    assert second_cancel.status_code == 400
    data = second_cancel.json()
    assert data["success"] is False
    assert "already cancelled" in data["error"].lower()


def test_cancel_appointment_tool_integration():
    """Test the cancel_appointment_tool with actual API."""
    from src.tools_cancellation import cancel_appointment_tool

    # Step 1: Create appointment
    appointment_data = {
        "service_id": "srv-002",
        "date": "2025-12-16",
        "start_time": "14:00",
        "client": {
            "name": "Tool Test User",
            "email": "tooltest@example.com",
            "phone": "5559876543"
        }
    }

    create_response = requests.post(f"{BASE_URL}/appointments", json=appointment_data)
    confirmation_number = create_response.json()["appointment"]["confirmation_number"]

    # Step 2: Cancel using the tool
    result = cancel_appointment_tool.invoke({"confirmation_number": confirmation_number})

    assert "[SUCCESS]" in result
    assert confirmation_number in result
    assert "cancelled" in result.lower()
    assert "Status: cancelled" in result

    # Step 3: Verify it's cancelled but not deleted
    get_response = requests.get(f"{BASE_URL}/appointments/{confirmation_number}")
    assert get_response.status_code == 200
    assert get_response.json()["appointment"]["status"] == "cancelled"


def test_cancel_appointment_tool_not_found():
    """Test tool with non-existent confirmation number."""
    from src.tools_cancellation import cancel_appointment_tool

    result = cancel_appointment_tool.invoke({"confirmation_number": "APPT-INVALID"})

    assert "[ERROR]" in result
    assert "not found" in result.lower()
