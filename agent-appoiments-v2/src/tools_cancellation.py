"""Tools for cancellation and rescheduling (v1.2)."""
import requests
from langchain_core.tools import tool
from src import config


@tool
def cancel_appointment_tool(confirmation_number: str) -> str:
    """
    Cancel an appointment by confirmation number.

    Args:
        confirmation_number: Appointment confirmation number (e.g., APPT-1234)

    Returns:
        Cancellation confirmation message
    """
    try:
        response = requests.delete(
            f"{config.MOCK_API_BASE_URL}/appointments/{confirmation_number}",
            timeout=5
        )

        if response.status_code == 200:
            return f"[SUCCESS] Appointment {confirmation_number} has been cancelled."
        elif response.status_code == 404:
            return f"[ERROR] Appointment {confirmation_number} not found."
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
