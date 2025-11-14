"""Tools for appointment management: cancellation and rescheduling (v1.2, v1.3)."""
import requests
from langchain_core.tools import tool
from src import config


@tool
def cancel_appointment_tool(confirmation_number: str) -> str:
    """
    Cancel appointment. Call AFTER user confirms cancellation.
    SECURITY: Only accepts confirmation number (NO email lookup).
    Returns [SUCCESS] or [ERROR]. System auto-escalates after 2 failures.
    """
    try:
        response = requests.patch(
            f"{config.MOCK_API_BASE_URL}/appointments/{confirmation_number}",
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            appointment = data.get("appointment", {})
            return (
                f"[SUCCESS] Appointment {confirmation_number} has been cancelled.\n"
                f"Service: {appointment.get('service_name', 'N/A')}\n"
                f"Date: {appointment.get('date', 'N/A')} at {appointment.get('start_time', 'N/A')}\n"
                f"Status: {appointment.get('status', 'N/A')}"
            )
        elif response.status_code == 404:
            return f"[ERROR] Appointment {confirmation_number} not found."
        elif response.status_code == 400:
            # Already cancelled
            data = response.json()
            error = data.get("error", "Appointment already cancelled")
            return f"[ERROR] {error}"
        else:
            return "[ERROR] Error cancelling appointment. Please try again."

    except Exception as e:
        return f"[ERROR] Could not connect to booking system: {str(e)}"


@tool
def get_user_appointments_tool(email: str) -> str:
    """
    Get appointments for a user by email.

    Args:
        email: User's email address

    Returns:
        List of appointments
    """
    try:
        response = requests.get(
            f"{config.MOCK_API_BASE_URL}/appointments",
            params={"email": email},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            appointments = data.get("appointments", [])

            if not appointments:
                return "[ERROR] No appointments found for this email."

            result = "[APPOINTMENTS] Your appointments:\n\n"
            for apt in appointments:
                result += f"• {apt['confirmation_number']}\n"
                result += f"  Service: {apt['service_name']}\n"
                result += f"  Date: {apt['date']} at {apt['start_time']}\n\n"

            return result
        else:
            return "[ERROR] Error retrieving appointments."

    except Exception as e:
        return f"[ERROR] Could not connect to booking system: {str(e)}"


@tool
def get_appointment_tool(confirmation_number: str) -> str:
    """
    Get appointment details for rescheduling. Call IMMEDIATELY after user provides confirmation number.
    SECURITY: Only accepts confirmation number (NO email lookup).
    Returns [APPOINTMENT] with current details or [ERROR]. System auto-escalates after 2 failures.
    """
    try:
        response = requests.get(
            f"{config.MOCK_API_BASE_URL}/appointments/{confirmation_number}",
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            appointment = data.get("appointment", {})
            return (
                f"[APPOINTMENT] Current appointment details:\n"
                f"Confirmation: {appointment.get('confirmation_number', 'N/A')}\n"
                f"Service: {appointment.get('service_name', 'N/A')}\n"
                f"Date: {appointment.get('date', 'N/A')} at {appointment.get('start_time', 'N/A')}\n"
                f"Client: {appointment.get('client', {}).get('name', 'N/A')}\n"
                f"Status: {appointment.get('status', 'N/A')}"
            )
        elif response.status_code == 404:
            return f"[ERROR] Appointment {confirmation_number} not found."
        else:
            return "[ERROR] Error retrieving appointment. Please try again."

    except Exception as e:
        return f"[ERROR] Could not connect to booking system: {str(e)}"


@tool
def reschedule_appointment_tool(
    confirmation_number: str,
    new_date: str,
    new_start_time: str
) -> str:
    """
    Reschedule appointment. Call ONLY AFTER user confirms AND selects new date/time.
    Client info preserved automatically (NO need to ask again).
    new_date: YYYY-MM-DD, new_start_time: HH:MM (24-hour).
    Returns [SUCCESS] with updated details or [ERROR].
    """
    try:
        payload = {
            "date": new_date,
            "start_time": new_start_time
        }

        response = requests.put(
            f"{config.MOCK_API_BASE_URL}/appointments/{confirmation_number}/reschedule",
            json=payload,
            timeout=5
        )

        data = response.json()

        if response.status_code == 200:
            appointment = data.get("appointment", {})
            return (
                f"[SUCCESS] Appointment {confirmation_number} has been rescheduled.\n"
                f"Service: {appointment.get('service_name', 'N/A')}\n"
                f"New Date: {appointment.get('date', 'N/A')} at {appointment.get('start_time', 'N/A')}\n"
                f"Status: {appointment.get('status', 'N/A')}"
            )
        elif response.status_code == 404:
            return f"[ERROR] Appointment {confirmation_number} not found."
        elif response.status_code == 400:
            error = data.get("error", "Cannot reschedule this appointment")
            return f"[ERROR] {error}"
        elif response.status_code == 409:
            # Slot not available, show alternatives
            error = data.get("error", "Slot not available")
            alternatives = data.get("alternatives", [])
            result = f"[ERROR] {error}\n\nAlternative slots:\n"
            for i, alt in enumerate(alternatives[:5], 1):
                result += (
                    f"{i}. {alt['day']}, {alt['date']} "
                    f"at {alt['start_time']} - {alt['end_time']}\n"
                )
            return result
        else:
            return "[ERROR] Error rescheduling appointment. Please try again."

    except Exception as e:
        return f"[ERROR] Could not connect to booking system: {str(e)}"
