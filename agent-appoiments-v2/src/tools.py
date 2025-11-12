"""Agent tools with @tool decorator (LangChain 1.0 pattern).

Best Practices:
- Use @tool decorator from langchain_core.tools
- Full type hints for args and return
- Descriptive docstrings (LLM reads these!)
- Return strings (LLM-friendly format)

v1.2 Updates:
- Validation tools now use caching for 100x performance improvement
"""
import re
import json
import requests
from typing import Optional
from langchain_core.tools import tool
from src import config
from src.cache import validation_cache


@tool
def validate_email_tool(email: str) -> str:
    """
    Validate email address format (OPTIMIZED v1.2).

    Performance: < 1ms with cache, < 10ms without.
    No LLM calls - pure regex validation.

    Checks for:
    - @ symbol present
    - Domain with TLD
    - Valid characters only

    Args:
        email: Email address to validate

    Returns:
        Validation result message

    Example:
        >>> validate_email_tool.invoke({"email": "user@example.com"})
        "✅ Email 'user@example.com' is valid."
    """
    is_valid, message = validation_cache.validate_email(email)
    # Convert emoji-based messages to bracket notation for consistency
    if is_valid:
        return f"[VALID] Email '{email}' is valid."
    else:
        return f"[INVALID] Email '{email}' is not valid. Please provide a valid email (e.g., name@example.com)."


@tool
def validate_phone_tool(phone: str) -> str:
    """
    Validate phone number (OPTIMIZED v1.2).

    Performance: < 1ms with cache, < 10ms without.
    No LLM calls - pure regex validation.

    Ignores formatting characters (spaces, hyphens, parentheses).
    Counts only numeric digits.

    Args:
        phone: Phone number to validate

    Returns:
        Validation result message
    """
    is_valid, message = validation_cache.validate_phone(phone)
    # Convert emoji-based messages to bracket notation for consistency
    if is_valid:
        return f"[VALID] Phone '{phone}' is valid."
    else:
        return f"[INVALID] Phone '{phone}' is not valid. Please provide at least 7 digits."


@tool
def get_services_tool() -> str:
    """
    Get list of available services from the API.

    Use this at the START of the conversation to show available services.
    No parameters needed.

    Returns:
        Formatted list of services with IDs, names, and durations
    """
    try:
        response = requests.get(
            f"{config.MOCK_API_BASE_URL}/services",
            timeout=5
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            return "[ERROR] Failed to fetch services"

        services = data.get("services", [])
        if not services:
            return "[ERROR] No services available"

        # Format for LLM
        result = "[SERVICES] Available services:\n"
        for service in services:
            result += (
                f"- {service['name']} "
                f"(ID: {service['id']}, Duration: {service['duration_minutes']} min)\n"
            )

        return result

    except requests.exceptions.RequestException as e:
        return f"[ERROR] Could not connect to API: {str(e)}"
    except Exception as e:
        return f"[ERROR] Unexpected error: {str(e)}"


@tool
def get_availability_tool(service_id: str, date_from: Optional[str] = None) -> str:
    """
    Get available time slots for a specific service.

    Use this AFTER the user has selected a service to show available times.

    Args:
        service_id: Service ID (e.g., 'srv-001')
        date_from: Optional start date in YYYY-MM-DD format (defaults to today)

    Returns:
        Formatted list of available time slots with dates and times
    """
    try:
        params = {"service_id": service_id}
        if date_from:
            params["date_from"] = date_from

        response = requests.get(
            f"{config.MOCK_API_BASE_URL}/availability",
            params=params,
            timeout=5
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            error = data.get("error", "Unknown error")
            return f"[ERROR] {error}"

        slots = data.get("available_slots", [])
        if not slots:
            return "[ERROR] No available slots found for this service"

        service = data.get("service", {})
        location = data.get("location", {})
        provider = data.get("assigned_person", {})

        # Format for LLM (show first 10 slots to avoid overwhelming)
        result = f"[AVAILABILITY] Found {len(slots)} available slots for {service['name']}:\n\n"
        result += f"Provider: {provider['name']}\n"
        result += f"Location: {location['name']}, {location['address']}\n\n"
        result += "Available times (showing first 10):\n"

        for i, slot in enumerate(slots[:10]):
            result += (
                f"{i+1}. {slot['day']}, {slot['date']} "
                f"at {slot['start_time']} - {slot['end_time']}\n"
            )

        if len(slots) > 10:
            result += f"\n... and {len(slots) - 10} more slots available"

        return result

    except requests.exceptions.RequestException as e:
        return f"[ERROR] Could not connect to API: {str(e)}"
    except Exception as e:
        return f"[ERROR] Unexpected error: {str(e)}"


@tool
def create_appointment_tool(
    service_id: str,
    date: str,
    start_time: str,
    client_name: str,
    client_email: str,
    client_phone: str
) -> str:
    """
    Create an appointment booking.

    IMPORTANT: Call this ONLY AFTER:
    1. Getting user confirmation
    2. Validating email with validate_email_tool
    3. Validating phone with validate_phone_tool

    Args:
        service_id: Service ID (e.g., 'srv-001')
        date: Appointment date in YYYY-MM-DD format
        start_time: Start time in HH:MM format (e.g., '14:30')
        client_name: Client's full name
        client_email: Client's email (already validated)
        client_phone: Client's phone (already validated)

    Returns:
        Confirmation message with appointment details and confirmation number
    """
    try:
        payload = {
            "service_id": service_id,
            "date": date,
            "start_time": start_time,
            "client": {
                "name": client_name,
                "email": client_email,
                "phone": client_phone
            }
        }

        response = requests.post(
            f"{config.MOCK_API_BASE_URL}/appointments",
            json=payload,
            timeout=5
        )

        data = response.json()

        if not data.get("success"):
            error = data.get("error", "Unknown error")

            # If slot not available, show alternatives
            if "not available" in error.lower() and "alternatives" in data:
                alternatives = data.get("alternatives", [])
                result = f"[ERROR] {error}\n\nAlternative slots:\n"
                for i, alt in enumerate(alternatives[:5]):
                    result += (
                        f"{i+1}. {alt['day']}, {alt['date']} "
                        f"at {alt['start_time']} - {alt['end_time']}\n"
                    )
                return result

            return f"[ERROR] {error}"

        # Success
        appointment = data.get("appointment", {})
        message = data.get("message", "")

        result = f"[SUCCESS] {message}\n\n"
        result += "📋 APPOINTMENT DETAILS:\n"
        result += f"Confirmation: {appointment['confirmation_number']}\n"
        result += f"Service: {appointment['service_name']}\n"
        result += f"Date: {appointment['date']}\n"
        result += f"Time: {appointment['start_time']} - {appointment['end_time']}\n"
        result += f"Provider: {appointment['assigned_person']['name']}\n"
        result += f"Location: {appointment['location']['name']}\n"
        result += f"Client: {appointment['client']['name']}\n"
        result += f"Email: {appointment['client']['email']}\n"
        result += f"Phone: {appointment['client']['phone']}\n"

        return result

    except requests.exceptions.RequestException as e:
        return f"[ERROR] Could not connect to API: {str(e)}"
    except Exception as e:
        return f"[ERROR] Unexpected error: {str(e)}"
