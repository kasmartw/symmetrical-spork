"""Integration tests for rescheduling API endpoint."""
import pytest
import requests
from datetime import datetime, timedelta
from src import config


BASE_URL = config.MOCK_API_BASE_URL


def test_reschedule_appointment_success():
    """Test successful rescheduling (updates date/time, preserves client info)."""
    # Get available slots first
    slots_resp = requests.get(f"{BASE_URL}/availability?service_id=srv-001")
    slots = slots_resp.json()["available_slots"]

    # Use first two different dates
    first_slot = slots[0]
    second_slot = next((s for s in slots if s["date"] != first_slot["date"]), slots[1])

    # Create appointment
    create_data = {
        "service_id": "srv-001",
        "date": first_slot["date"],
        "start_time": first_slot["start_time"],
        "client": {
            "name": "Test User",
            "email": "testreschedule@example.com",
            "phone": "1234567890"
        }
    }

    create_resp = requests.post(f"{BASE_URL}/appointments", json=create_data)
    assert create_resp.status_code == 201
    conf_num = create_resp.json()["appointment"]["confirmation_number"]

    # Reschedule to new date/time
    reschedule_data = {
        "date": second_slot["date"],
        "start_time": second_slot["start_time"]
    }

    reschedule_resp = requests.put(
        f"{BASE_URL}/appointments/{conf_num}/reschedule",
        json=reschedule_data
    )

    assert reschedule_resp.status_code == 200
    data = reschedule_resp.json()
    assert data["success"] is True

    appointment = data["appointment"]
    assert appointment["confirmation_number"] == conf_num
    assert appointment["date"] == second_slot["date"]
    assert appointment["start_time"] == second_slot["start_time"]

    # Client info preserved
    assert appointment["client"]["name"] == "Test User"
    assert appointment["client"]["email"] == "testreschedule@example.com"

    # Status remains confirmed
    assert appointment["status"] == "confirmed"
    assert "rescheduled_at" in appointment


def test_reschedule_invalid_confirmation():
    """Test rescheduling with invalid confirmation number."""
    reschedule_data = {"date": "2025-11-20", "start_time": "14:00"}

    resp = requests.put(
        f"{BASE_URL}/appointments/APPT-99999/reschedule",
        json=reschedule_data
    )

    assert resp.status_code == 404
    assert resp.json()["success"] is False
    assert "not found" in resp.json()["error"].lower()


def test_reschedule_cancelled_appointment():
    """Test that cancelled appointments cannot be rescheduled."""
    # Get available slots
    slots_resp = requests.get(f"{BASE_URL}/availability?service_id=srv-001")
    slots = slots_resp.json()["available_slots"]
    first_slot = slots[0]
    second_slot = next((s for s in slots if s["date"] != first_slot["date"]), slots[1])

    # Create and cancel appointment
    create_data = {
        "service_id": "srv-001",
        "date": first_slot["date"],
        "start_time": first_slot["start_time"],
        "client": {
            "name": "Cancel Test",
            "email": "canceltest@example.com",
            "phone": "9876543210"
        }
    }

    create_resp = requests.post(f"{BASE_URL}/appointments", json=create_data)
    conf_num = create_resp.json()["appointment"]["confirmation_number"]

    # Cancel it
    requests.patch(f"{BASE_URL}/appointments/{conf_num}")

    # Try to reschedule
    reschedule_data = {"date": second_slot["date"], "start_time": second_slot["start_time"]}
    reschedule_resp = requests.put(
        f"{BASE_URL}/appointments/{conf_num}/reschedule",
        json=reschedule_data
    )

    assert reschedule_resp.status_code == 400
    assert "cancelled" in reschedule_resp.json()["error"].lower()


def test_reschedule_to_unavailable_slot():
    """Test rescheduling to already booked slot returns error with alternatives."""
    # Get available slots
    slots_resp = requests.get(f"{BASE_URL}/availability?service_id=srv-001")
    slots = slots_resp.json()["available_slots"]

    # Use three different slots
    first_slot = slots[0]
    second_slot = slots[1]
    third_slot = slots[2]

    # Create first appointment
    first_data = {
        "service_id": "srv-001",
        "date": first_slot["date"],
        "start_time": first_slot["start_time"],
        "client": {
            "name": "First User",
            "email": "first@example.com",
            "phone": "1111111111"
        }
    }
    requests.post(f"{BASE_URL}/appointments", json=first_data)

    # Create second appointment
    second_data = {
        "service_id": "srv-001",
        "date": second_slot["date"],
        "start_time": second_slot["start_time"],
        "client": {
            "name": "Second User",
            "email": "second@example.com",
            "phone": "2222222222"
        }
    }
    second_resp = requests.post(f"{BASE_URL}/appointments", json=second_data)
    conf_num = second_resp.json()["appointment"]["confirmation_number"]

    # Try to reschedule second to first's slot (should fail - already booked)
    reschedule_data = {"date": first_slot["date"], "start_time": first_slot["start_time"]}
    reschedule_resp = requests.put(
        f"{BASE_URL}/appointments/{conf_num}/reschedule",
        json=reschedule_data
    )

    assert reschedule_resp.status_code == 409
    data = reschedule_resp.json()
    assert data["success"] is False
    assert "not available" in data["error"].lower()
    assert "alternatives" in data
    assert len(data["alternatives"]) > 0
