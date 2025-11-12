"""Unit tests for rescheduling tools."""
import pytest
from unittest.mock import Mock, patch
from src.tools_appointment_mgmt import (
    get_appointment_tool,
    reschedule_appointment_tool
)


def test_get_appointment_tool_success():
    """Test successful appointment retrieval."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "appointment": {
            "confirmation_number": "APPT-1234",
            "service_name": "General Consultation",
            "date": "2025-11-15",
            "start_time": "10:00",
            "client": {"name": "Test User"},
            "status": "confirmed"
        }
    }

    with patch('requests.get', return_value=mock_response):
        result = get_appointment_tool.invoke({"confirmation_number": "APPT-1234"})

    assert "[APPOINTMENT]" in result
    assert "APPT-1234" in result
    assert "General Consultation" in result
    assert "2025-11-15" in result
    assert "10:00" in result
    assert "confirmed" in result


def test_get_appointment_tool_not_found():
    """Test appointment not found."""
    mock_response = Mock()
    mock_response.status_code = 404

    with patch('requests.get', return_value=mock_response):
        result = get_appointment_tool.invoke({"confirmation_number": "APPT-9999"})

    assert "[ERROR]" in result
    assert "not found" in result.lower()


def test_reschedule_appointment_tool_success():
    """Test successful rescheduling."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "message": "Appointment rescheduled",
        "appointment": {
            "confirmation_number": "APPT-1234",
            "service_name": "General Consultation",
            "date": "2025-11-20",
            "start_time": "14:00",
            "status": "confirmed"
        }
    }

    with patch('requests.put', return_value=mock_response):
        result = reschedule_appointment_tool.invoke({
            "confirmation_number": "APPT-1234",
            "new_date": "2025-11-20",
            "new_start_time": "14:00"
        })

    assert "[SUCCESS]" in result
    assert "APPT-1234" in result
    assert "2025-11-20" in result
    assert "14:00" in result


def test_reschedule_appointment_tool_slot_unavailable():
    """Test rescheduling to unavailable slot returns alternatives."""
    mock_response = Mock()
    mock_response.status_code = 409
    mock_response.json.return_value = {
        "success": False,
        "error": "Slot not available",
        "alternatives": [
            {"date": "2025-11-20", "start_time": "15:00", "day": "Wednesday", "end_time": "15:30"},
            {"date": "2025-11-20", "start_time": "16:00", "day": "Wednesday", "end_time": "16:30"}
        ]
    }

    with patch('requests.put', return_value=mock_response):
        result = reschedule_appointment_tool.invoke({
            "confirmation_number": "APPT-1234",
            "new_date": "2025-11-20",
            "new_start_time": "14:00"
        })

    assert "[ERROR]" in result
    assert "not available" in result.lower()
    assert "Alternative" in result
    assert "15:00" in result
    assert "16:00" in result
