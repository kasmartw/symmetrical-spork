"""Agent tools with @tool decorator (LangChain 1.0 pattern).

Best Practices:
- Use @tool decorator from langchain_core.tools
- Full type hints for args and return
- Descriptive docstrings (LLM reads these!)
- Return strings (LLM-friendly format)

v1.2 Updates:
- Validation tools now use caching for 100x performance improvement

v1.5 Updates:
- New availability caching strategy with fetch + filter pattern
- Replaced get_availability_tool with fetch_and_cache + filter_and_show
"""
import re
import json
import requests
from datetime import datetime
from typing import Optional
from langchain_core.tools import tool
from src import config
from src.cache import validation_cache, availability_cache


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
def fetch_and_cache_availability_tool(service_id: str) -> str:
    """
    Fetch 30 days of availability and cache it (v1.5 NEW).

    This tool fetches availability from the API and stores it in cache.
    It does NOT show slots to the user - use filter_and_show_availability_tool for that.

    Use this IMMEDIATELY after user selects a service.

    Args:
        service_id: Service ID (e.g., 'srv-001')

    Returns:
        Success message with count of slots found (does not show actual slots)
    """
    try:
        # Use datetime.now() to get current date
        date_from = datetime.now().strftime("%Y-%m-%d")

        params = {
            "service_id": service_id,
            "date_from": date_from
        }

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

        # Cache the results
        availability_cache.set(
            service_id=service_id,
            slots=slots,
            service=service,
            location=location,
            assigned_person=provider
        )

        return (
            f"[SUCCESS] Fetched and cached {len(slots)} available slots for {service['name']}. "
            f"Now use filter_and_show_availability_tool to show slots to user."
        )

    except requests.exceptions.RequestException as e:
        return f"[ERROR] Could not connect to API: {str(e)}"
    except Exception as e:
        return f"[ERROR] Unexpected error: {str(e)}"


@tool
def filter_and_show_availability_tool(
    service_id: str,
    time_preference: str = "any",
    offset: int = 0
) -> str:
    """
    Filter and show 3 days of availability from cache with time filtering (v1.5 UPDATED).

    This tool reads from cache, FILTERS BY TIME PREFERENCE, and shows the user
    3 days with availability that match the preference, with max 4 slots per day.

    IMPORTANT: This tool MUST be called with time_preference from user's response.

    Use this AFTER user responds to time preference question.

    Args:
        service_id: Service ID (e.g., 'srv-001')
        time_preference: Time preference - "morning", "afternoon", or "any"
        offset: Number of days to skip (default 0). Increment by 3 to show next batch.

    Returns:
        Formatted availability for 3 days with max 4 slots per day (filtered by time)
    """
    try:
        # Get from cache
        cached_data = availability_cache.get(service_id)

        if not cached_data:
            return (
                "[ERROR] No cached availability found. "
                "Please call fetch_and_cache_availability_tool first."
            )

        slots = cached_data["slots"]
        service = cached_data["service"]
        location = cached_data["location"]
        provider = cached_data["assigned_person"]

        if not slots:
            return "[ERROR] No available slots found"

        # STEP 1: FILTER BY TIME PREFERENCE (CRITICAL!)
        filtered_slots = []
        if time_preference == "morning":
            # Morning: before 12:00 PM
            for slot in slots:
                hour = int(slot["start_time"].split(":")[0])
                if hour < 12:
                    filtered_slots.append(slot)
        elif time_preference == "afternoon":
            # Afternoon: 12:00 PM and after
            for slot in slots:
                hour = int(slot["start_time"].split(":")[0])
                if hour >= 12:
                    filtered_slots.append(slot)
        else:
            # "any" - no filter
            filtered_slots = slots

        if not filtered_slots:
            return f"[INFO] No {time_preference} slots available. Would you like to see all times instead?"

        # STEP 2: Group filtered slots by date
        slots_by_date = {}
        for slot in filtered_slots:
            date = slot["date"]
            if date not in slots_by_date:
                slots_by_date[date] = []
            slots_by_date[date].append(slot)

        # Get sorted dates (only dates that have slots after filtering)
        sorted_dates = sorted(slots_by_date.keys())

        # STEP 3: Apply offset and get next 3 days with availability
        dates_to_show = sorted_dates[offset:offset + 3]

        if not dates_to_show:
            return f"[INFO] No more {time_preference} dates available."

        # STEP 4: Format result
        filter_label = f" ({time_preference} times)" if time_preference != "any" else ""
        result = f"[AVAILABILITY] Available times for {service['name']}{filter_label}:\n\n"
        result += f"Provider: {provider['name']}\n"
        result += f"Location: {location['name']}, {location['address']}\n\n"

        for date in dates_to_show:
            date_slots = slots_by_date[date][:4]  # Max 4 slots per day

            # Get day name from first slot
            day_name = date_slots[0]["day"]

            result += f"\n📅 {day_name}, {date}:\n"
            for i, slot in enumerate(date_slots):
                # Convert to 12-hour format
                start_time_24 = datetime.strptime(slot["start_time"], "%H:%M")
                end_time_24 = datetime.strptime(slot["end_time"], "%H:%M")
                start_time_12 = start_time_24.strftime("%I:%M %p").lstrip("0")
                end_time_12 = end_time_24.strftime("%I:%M %p").lstrip("0")

                result += f"  {i+1}. {start_time_12} - {end_time_12}\n"

        # Check if there are more dates available
        remaining_dates = len(sorted_dates) - (offset + len(dates_to_show))
        if remaining_dates > 0:
            result += f"\n💡 {remaining_dates} more days available with {time_preference} slots. "
            result += f"To see more, call this tool again with offset={offset + 3}"
        else:
            result += f"\n✅ These are all available {time_preference} dates."

        return result

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
