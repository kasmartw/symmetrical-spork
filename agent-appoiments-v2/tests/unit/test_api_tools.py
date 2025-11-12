"""Unit tests for API tools.

Tests API integration tools without actually calling the mock API.
Uses mocking to simulate API responses.
"""
import pytest
import requests
from unittest.mock import patch, Mock
from src.tools import (
    get_services_tool,
    get_availability_tool,
    create_appointment_tool
)


class TestGetServicesTool:
    """Tests for get_services_tool."""

    @patch('src.tools.requests.get')
    def test_get_services_success(self, mock_get):
        """Test successful service retrieval."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "services": [
                {"id": "srv-001", "name": "General Consultation", "duration_minutes": 30},
                {"id": "srv-002", "name": "Specialized Consultation", "duration_minutes": 60},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Invoke tool
        result = get_services_tool.invoke({})

        # Assertions
        assert "[SERVICES]" in result
        assert "General Consultation" in result
        assert "srv-001" in result
        assert "30 min" in result
        mock_get.assert_called_once()

    @patch('src.tools.requests.get')
    def test_get_services_api_error(self, mock_get):
        """Test API connection error."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection refused")

        result = get_services_tool.invoke({})

        assert "[ERROR]" in result
        assert ("Could not connect" in result or "Unexpected error" in result)

    @patch('src.tools.requests.get')
    def test_get_services_empty_response(self, mock_get):
        """Test empty services list."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "services": []
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = get_services_tool.invoke({})

        assert "[ERROR]" in result
        assert "No services available" in result


class TestGetAvailabilityTool:
    """Tests for get_availability_tool."""

    @patch('src.tools.requests.get')
    def test_get_availability_success(self, mock_get):
        """Test successful availability retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "service": {"id": "srv-001", "name": "General Consultation"},
            "location": {"name": "Downtown", "address": "123 Main St"},
            "assigned_person": {"name": "Dr. Garcia"},
            "available_slots": [
                {"date": "2025-01-15", "day": "Monday", "start_time": "10:00", "end_time": "10:30"},
                {"date": "2025-01-15", "day": "Monday", "start_time": "11:00", "end_time": "11:30"},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = get_availability_tool.invoke({"service_id": "srv-001"})

        assert "[AVAILABILITY]" in result
        assert "General Consultation" in result
        assert "Dr. Garcia" in result
        assert "Monday, 2025-01-15" in result
        assert "10:00" in result

    @patch('src.tools.requests.get')
    def test_get_availability_with_date_from(self, mock_get):
        """Test availability with date_from parameter."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "service": {"id": "srv-001", "name": "General"},
            "location": {"name": "Downtown", "address": "123"},
            "assigned_person": {"name": "Dr. Garcia"},
            "available_slots": [
                {"date": "2025-01-20", "day": "Friday", "start_time": "14:00", "end_time": "14:30"}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = get_availability_tool.invoke({
            "service_id": "srv-001",
            "date_from": "2025-01-20"
        })

        assert "[AVAILABILITY]" in result
        assert "2025-01-20" in result
        # Check that date_from was passed to API
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs['params']['date_from'] == "2025-01-20"

    @patch('src.tools.requests.get')
    def test_get_availability_no_slots(self, mock_get):
        """Test when no slots are available."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "service": {"id": "srv-001", "name": "General"},
            "location": {"name": "Downtown", "address": "123"},
            "assigned_person": {"name": "Dr. Garcia"},
            "available_slots": []
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = get_availability_tool.invoke({"service_id": "srv-001"})

        assert "[ERROR]" in result
        assert "No available slots" in result

    @patch('src.tools.requests.get')
    def test_get_availability_service_not_found(self, mock_get):
        """Test with invalid service ID."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": False,
            "error": "Service 'invalid' not found"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = get_availability_tool.invoke({"service_id": "invalid"})

        assert "[ERROR]" in result
        assert "not found" in result


class TestCreateAppointmentTool:
    """Tests for create_appointment_tool."""

    @patch('src.tools.requests.post')
    def test_create_appointment_success(self, mock_post):
        """Test successful appointment creation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "message": "Appointment confirmed!",
            "appointment": {
                "confirmation_number": "APPT-1001",
                "service_name": "General Consultation",
                "date": "2025-01-15",
                "start_time": "10:00",
                "end_time": "10:30",
                "assigned_person": {"name": "Dr. Garcia"},
                "location": {"name": "Downtown"},
                "client": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "phone": "555-1234567"
                }
            }
        }
        mock_post.return_value = mock_response

        result = create_appointment_tool.invoke({
            "service_id": "srv-001",
            "date": "2025-01-15",
            "start_time": "10:00",
            "client_name": "John Doe",
            "client_email": "john@example.com",
            "client_phone": "555-1234567"
        })

        assert "[SUCCESS]" in result
        assert "APPT-1001" in result
        assert "John Doe" in result
        assert "10:00" in result

        # Verify API was called with correct payload
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        assert payload['service_id'] == "srv-001"
        assert payload['date'] == "2025-01-15"
        assert payload['client']['name'] == "John Doe"

    @patch('src.tools.requests.post')
    def test_create_appointment_slot_unavailable(self, mock_post):
        """Test when time slot is no longer available."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": False,
            "error": "This time slot is no longer available",
            "alternatives": [
                {"date": "2025-01-15", "day": "Monday", "start_time": "11:00", "end_time": "11:30"},
                {"date": "2025-01-15", "day": "Monday", "start_time": "14:00", "end_time": "14:30"},
            ]
        }
        mock_post.return_value = mock_response

        result = create_appointment_tool.invoke({
            "service_id": "srv-001",
            "date": "2025-01-15",
            "start_time": "10:00",
            "client_name": "John Doe",
            "client_email": "john@example.com",
            "client_phone": "555-1234567"
        })

        assert "[ERROR]" in result
        assert "no longer available" in result.lower()
        # Check alternatives if present (depends on response structure)
        if "alternatives" in result.lower() or "alternative" in result.lower():
            assert "11:00" in result

    @patch('src.tools.requests.post')
    def test_create_appointment_invalid_email(self, mock_post):
        """Test with invalid email (API-side validation)."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": False,
            "error": "Invalid email format"
        }
        mock_post.return_value = mock_response

        result = create_appointment_tool.invoke({
            "service_id": "srv-001",
            "date": "2025-01-15",
            "start_time": "10:00",
            "client_name": "John Doe",
            "client_email": "invalid-email",
            "client_phone": "555-1234567"
        })

        assert "[ERROR]" in result
        assert "Invalid email" in result

    @patch('src.tools.requests.post')
    def test_create_appointment_api_error(self, mock_post):
        """Test API connection error."""
        mock_post.side_effect = requests.exceptions.RequestException("Connection timeout")

        result = create_appointment_tool.invoke({
            "service_id": "srv-001",
            "date": "2025-01-15",
            "start_time": "10:00",
            "client_name": "John Doe",
            "client_email": "john@example.com",
            "client_phone": "555-1234567"
        })

        assert "[ERROR]" in result
        assert ("Could not connect" in result or "Unexpected error" in result)
