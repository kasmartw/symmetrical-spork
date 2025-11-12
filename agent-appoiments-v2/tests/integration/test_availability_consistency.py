"""Integration test for availability consistency.

Tests that availability is deterministic and consistent:
- Same slots returned across multiple calls
- Booked slots are removed from availability
- Cancelled appointments free up slots
"""
import pytest
import requests
from src import config


BASE_URL = config.MOCK_API_BASE_URL


def test_availability_is_consistent():
    """Test that calling availability multiple times returns the same slots."""
    service_id = "srv-001"

    # Call availability 3 times
    response1 = requests.get(f"{BASE_URL}/availability", params={"service_id": service_id})
    response2 = requests.get(f"{BASE_URL}/availability", params={"service_id": service_id})
    response3 = requests.get(f"{BASE_URL}/availability", params={"service_id": service_id})

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response3.status_code == 200

    slots1 = response1.json()["available_slots"]
    slots2 = response2.json()["available_slots"]
    slots3 = response3.json()["available_slots"]

    # All calls should return identical slots
    assert len(slots1) == len(slots2) == len(slots3)
    assert slots1 == slots2 == slots3

    # Verify first 5 slots are identical
    first_5_slots_1 = [f"{s['date']} {s['start_time']}" for s in slots1[:5]]
    first_5_slots_2 = [f"{s['date']} {s['start_time']}" for s in slots2[:5]]
    first_5_slots_3 = [f"{s['date']} {s['start_time']}" for s in slots3[:5]]

    assert first_5_slots_1 == first_5_slots_2 == first_5_slots_3


def test_booked_slot_removed_from_availability():
    """Test that booking a slot removes it from availability."""
    service_id = "srv-002"

    # Get initial availability
    initial_response = requests.get(f"{BASE_URL}/availability", params={"service_id": service_id})
    initial_slots = initial_response.json()["available_slots"]
    initial_count = len(initial_slots)

    # Get first available slot
    first_slot = initial_slots[0]
    slot_date = first_slot["date"]
    slot_time = first_slot["start_time"]

    # Book the first slot
    booking_data = {
        "service_id": service_id,
        "date": slot_date,
        "start_time": slot_time,
        "client": {
            "name": "Test Consistency",
            "email": "testconsist@example.com",
            "phone": "1234567890"
        }
    }

    booking_response = requests.post(f"{BASE_URL}/appointments", json=booking_data)
    assert booking_response.status_code == 201

    # Get availability again
    after_response = requests.get(f"{BASE_URL}/availability", params={"service_id": service_id})
    after_slots = after_response.json()["available_slots"]
    after_count = len(after_slots)

    # Should have one less slot
    assert after_count == initial_count - 1

    # Booked slot should not be in availability
    booked_slot_key = f"{slot_date} {slot_time}"
    after_slot_keys = [f"{s['date']} {s['start_time']}" for s in after_slots]
    assert booked_slot_key not in after_slot_keys


def test_cancelled_slot_returns_to_availability():
    """Test that cancelling an appointment makes the slot available again."""
    service_id = "srv-003"

    # Get initial availability
    initial_response = requests.get(f"{BASE_URL}/availability", params={"service_id": service_id})
    initial_slots = initial_response.json()["available_slots"]
    initial_count = len(initial_slots)
    first_slot = initial_slots[0]

    # Book a slot
    booking_data = {
        "service_id": service_id,
        "date": first_slot["date"],
        "start_time": first_slot["start_time"],
        "client": {
            "name": "Test Cancel Return",
            "email": "testcancelreturn@example.com",
            "phone": "9876543210"
        }
    }

    booking_response = requests.post(f"{BASE_URL}/appointments", json=booking_data)
    confirmation_number = booking_response.json()["appointment"]["confirmation_number"]

    # Verify slot is removed
    after_booking = requests.get(f"{BASE_URL}/availability", params={"service_id": service_id})
    after_booking_count = len(after_booking.json()["available_slots"])
    assert after_booking_count == initial_count - 1

    # Cancel the appointment
    cancel_response = requests.patch(f"{BASE_URL}/appointments/{confirmation_number}")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["appointment"]["status"] == "cancelled"

    # Verify slot returns to availability
    after_cancel = requests.get(f"{BASE_URL}/availability", params={"service_id": service_id})
    after_cancel_slots = after_cancel.json()["available_slots"]
    after_cancel_count = len(after_cancel_slots)

    # Should be back to original count
    assert after_cancel_count == initial_count

    # Original slot should be available again
    cancelled_slot_key = f"{first_slot['date']} {first_slot['start_time']}"
    after_cancel_keys = [f"{s['date']} {s['start_time']}" for s in after_cancel_slots]
    assert cancelled_slot_key in after_cancel_keys


def test_shown_slot_is_actually_available():
    """Test that any slot shown in availability can actually be booked.

    This is the critical test for the bug fix - ensures users don't see
    'available' slots that fail when they try to book them.
    """
    service_id = "srv-001"

    # Get availability
    availability_response = requests.get(f"{BASE_URL}/availability", params={"service_id": service_id})
    slots = availability_response.json()["available_slots"]

    # Pick a random slot (let's use the 5th one)
    test_slot_index = min(4, len(slots) - 1)  # 5th slot or last if fewer
    test_slot = slots[test_slot_index]

    # Try to book it immediately
    booking_data = {
        "service_id": service_id,
        "date": test_slot["date"],
        "start_time": test_slot["start_time"],
        "client": {
            "name": "Test Shown Available",
            "email": "testshownavail@example.com",
            "phone": "5554443333"
        }
    }

    booking_response = requests.post(f"{BASE_URL}/appointments", json=booking_data)

    # Should succeed (this would fail with random availability)
    assert booking_response.status_code == 201, \
        f"Slot shown as available ({test_slot['date']} {test_slot['start_time']}) " \
        f"but booking failed: {booking_response.json()}"

    assert booking_response.json()["success"] is True
