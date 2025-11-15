"""Mock API for appointment booking system.

Flask server with realistic endpoints for:
- Services listing
- Availability checking
- Appointment creation

Run with: python mock_api.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import random
import re
from typing import Optional
from src import config
from src.config_manager import ConfigManager
from src.org_config import OrganizationConfig

app = Flask(__name__)
CORS(app)

# In-memory storage
appointments = []
appointment_counter = 1000

# Organization config manager (v1.5)
org_manager = ConfigManager()


def get_org_config(request_obj) -> Optional[OrganizationConfig]:
    """
    Get organization config from request header.

    Args:
        request_obj: Flask request object

    Returns:
        OrganizationConfig if X-Org-ID header present and valid, None otherwise
    """
    org_id = request_obj.headers.get('X-Org-ID')

    if not org_id:
        return None

    try:
        return org_manager.load_config(org_id)
    except FileNotFoundError:
        return None


def generate_time_slots(service_id, date_from=None):
    """Generate available time slots based on operating hours.

    Args:
        service_id: Service ID to generate slots for
        date_from: Start date (YYYY-MM-DD format), defaults to today

    Returns:
        List of available time slots with date, start_time, end_time
    """
    slots = []

    # Get service duration
    service = next((s for s in config.SERVICES if s["id"] == service_id), None)
    if not service:
        return []

    # Start from today or specified date
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if date_from:
        try:
            start_date = datetime.strptime(date_from, "%Y-%m-%d")
        except ValueError:
            pass

    # OPTIMIZATION: Pre-build set of booked slots for O(1) lookup
    booked_slots = {
        (apt["date"], apt["start_time"], apt["service_id"])
        for apt in appointments
        if apt.get("status") != "cancelled"
    }

    # Generate slots for next 30 days (configurable in config.py)
    for day_offset in range(config.AVAILABILITY_DAYS_RANGE):
        current_date = start_date + timedelta(days=day_offset)
        day_name = current_date.strftime("%A").lower()

        # Check if day is in operating hours
        if day_name not in config.OPERATING_HOURS["days"]:
            continue

        # Skip past dates
        if current_date < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            continue

        # Parse operating hours
        start_time = datetime.strptime(config.OPERATING_HOURS["start_time"], "%H:%M")
        end_time = datetime.strptime(config.OPERATING_HOURS["end_time"], "%H:%M")

        # Lunch break
        lunch_start = datetime.strptime(
            config.OPERATING_HOURS.get("lunch_break", {}).get("start", "13:00"),
            "%H:%M"
        )
        lunch_end = datetime.strptime(
            config.OPERATING_HOURS.get("lunch_break", {}).get("end", "14:00"),
            "%H:%M"
        )

        # Generate time slots
        current_time = start_time
        while current_time < end_time:
            # Skip lunch break
            if lunch_start <= current_time < lunch_end:
                current_time += timedelta(
                    minutes=config.OPERATING_HOURS["slot_duration_minutes"]
                )
                continue

            slot_datetime = current_date.replace(
                hour=current_time.hour,
                minute=current_time.minute
            )

            # Skip past times for today
            if slot_datetime > datetime.now():
                # OPTIMIZED: O(1) lookup instead of O(n) iteration
                slot_key = (
                    current_date.strftime("%Y-%m-%d"),
                    current_time.strftime("%H:%M"),
                    service_id
                )
                is_booked = slot_key in booked_slots

                if not is_booked:
                    end_slot_time = current_time + timedelta(
                        minutes=service["duration_minutes"]
                    )
                    slots.append({
                        "date": current_date.strftime("%Y-%m-%d"),
                        "day": current_date.strftime("%A"),
                        "start_time": current_time.strftime("%H:%M"),
                        "end_time": end_slot_time.strftime("%H:%M")
                    })

            current_time += timedelta(
                minutes=config.OPERATING_HOURS["slot_duration_minutes"]
            )

    return slots


def validate_email(email):
    """Validate email format using regex."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone):
    """Validate phone format (at least 7 digits)."""
    digits = re.sub(r'[^\d]', '', phone)
    return len(digits) >= 7


@app.route('/services', methods=['GET'])
def get_services():
    """GET /services - List all available services.

    Supports organization-specific services via X-Org-ID header (v1.5).
    """
    # Check for org-specific config
    org_config = get_org_config(request)

    if org_config:
        # Return org-specific active services
        active_services = org_config.get_active_services()
        services_list = [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "duration_minutes": s.duration_minutes,
                "price": s.price
            }
            for s in active_services
        ]

        response_data = {
            "success": True,
            "services": services_list,
            "total": len(services_list),
            "org_id": org_config.org_id
        }
        if org_config.org_name:
            response_data["org_name"] = org_config.org_name

        return jsonify(response_data)

    # Default: return config.SERVICES
    return jsonify({
        "success": True,
        "services": config.SERVICES,
        "total": len(config.SERVICES)
    })


@app.route('/availability', methods=['GET'])
def get_availability():
    """GET /availability?service_id=srv-001&date_from=2025-01-15

    Get available time slots for a specific service.
    """
    service_id = request.args.get('service_id')
    date_from = request.args.get('date_from')

    if not service_id:
        return jsonify({
            "success": False,
            "error": "service_id parameter is required"
        }), 400

    # Check if service exists
    service = next((s for s in config.SERVICES if s["id"] == service_id), None)
    if not service:
        return jsonify({
            "success": False,
            "error": f"Service '{service_id}' not found"
        }), 404

    slots = generate_time_slots(service_id, date_from)

    return jsonify({
        "success": True,
        "service": service,
        "available_slots": slots,
        "total_slots": len(slots),
        "assigned_person": config.ASSIGNED_PERSON,
        "location": config.LOCATION
    })


@app.route('/appointments', methods=['POST'])
def create_appointment():
    """POST /appointments - Create a new appointment.

    Expected JSON body:
    {
        "service_id": "srv-001",
        "date": "2025-01-15",
        "start_time": "10:00",
        "client": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-1234567"
        }
    }
    """
    global appointment_counter

    data = request.json
    if not data:
        return jsonify({
            "success": False,
            "error": "Request body is required"
        }), 400

    # Validate required fields
    required_fields = ['service_id', 'date', 'start_time', 'client']
    for field in required_fields:
        if field not in data:
            return jsonify({
                "success": False,
                "error": f"Missing required field: {field}"
            }), 400

    # Validate client data
    client = data['client']
    required_client_fields = ['name', 'email', 'phone']
    for field in required_client_fields:
        if field not in client:
            return jsonify({
                "success": False,
                "error": f"Client missing required field: {field}"
            }), 400

    # Validate email
    if not validate_email(client['email']):
        return jsonify({
            "success": False,
            "error": "Invalid email format. Please provide a valid email (e.g., name@example.com)"
        }), 400

    # Validate phone
    if not validate_phone(client['phone']):
        return jsonify({
            "success": False,
            "error": "Invalid phone number. Please provide at least 7 digits"
        }), 400

    # Validate service exists
    service = next((s for s in config.SERVICES if s["id"] == data['service_id']), None)
    if not service:
        return jsonify({
            "success": False,
            "error": f"Service '{data['service_id']}' not found"
        }), 404

    # Validate date format and is in future
    try:
        appointment_date = datetime.strptime(data['date'], "%Y-%m-%d")
        if appointment_date.date() < datetime.now().date():
            return jsonify({
                "success": False,
                "error": "Appointment date must be today or in the future"
            }), 400
    except ValueError:
        return jsonify({
            "success": False,
            "error": "Invalid date format. Use YYYY-MM-DD"
        }), 400

    # Validate time format
    try:
        datetime.strptime(data['start_time'], "%H:%M")
    except ValueError:
        return jsonify({
            "success": False,
            "error": "Invalid time format. Use HH:MM (e.g., 14:30)"
        }), 400

    # Check if slot is still available
    available_slots = generate_time_slots(data['service_id'])
    slot_available = any(
        slot["date"] == data['date'] and
        slot["start_time"] == data['start_time']
        for slot in available_slots
    )

    if not slot_available:
        # Get alternatives
        alternatives = [
            s for s in available_slots
            if s["date"] >= data['date']
        ][:5]
        return jsonify({
            "success": False,
            "error": "This time slot is no longer available",
            "alternatives": alternatives
        }), 409  # Conflict

    # Create appointment
    appointment_counter += 1
    confirmation_number = f"APPT-{appointment_counter}"

    # Calculate end time
    start_time = datetime.strptime(data['start_time'], "%H:%M")
    end_time = start_time + timedelta(minutes=service['duration_minutes'])

    appointment = {
        "confirmation_number": confirmation_number,
        "client": client,
        "service_id": data['service_id'],
        "service_name": service['name'],
        "date": data['date'],
        "start_time": data['start_time'],
        "end_time": end_time.strftime("%H:%M"),
        "duration_minutes": service['duration_minutes'],
        "assigned_person": config.ASSIGNED_PERSON,
        "location": config.LOCATION,
        "status": "confirmed",
        "created_at": datetime.now().isoformat()
    }

    appointments.append(appointment)

    return jsonify({
        "success": True,
        "appointment": appointment,
        "message": f"Appointment confirmed! Confirmation number: {confirmation_number}"
    }), 201


@app.route('/appointments/<confirmation_number>', methods=['GET'])
def get_appointment(confirmation_number):
    """GET /appointments/APPT-1001 - Get appointment by confirmation number."""
    appointment = next(
        (apt for apt in appointments if apt["confirmation_number"] == confirmation_number),
        None
    )

    if not appointment:
        return jsonify({
            "success": False,
            "error": f"Appointment '{confirmation_number}' not found"
        }), 404

    return jsonify({
        "success": True,
        "appointment": appointment
    })


@app.route('/appointments/<confirmation_number>', methods=['PATCH'])
def cancel_appointment(confirmation_number):
    """PATCH /appointments/APPT-1001 - Cancel appointment (change status, don't delete).

    Important: Cancelling does NOT delete the appointment, it only changes status.
    """
    appointment = next(
        (apt for apt in appointments if apt["confirmation_number"] == confirmation_number),
        None
    )

    if not appointment:
        return jsonify({
            "success": False,
            "error": f"Appointment '{confirmation_number}' not found"
        }), 404

    # Check if already cancelled
    if appointment.get("status") == "cancelled":
        return jsonify({
            "success": False,
            "error": f"Appointment {confirmation_number} is already cancelled"
        }), 400

    # Update status to cancelled (don't delete)
    appointment["status"] = "cancelled"
    appointment["cancelled_at"] = datetime.now().isoformat()

    return jsonify({
        "success": True,
        "message": f"Appointment {confirmation_number} has been cancelled",
        "appointment": appointment
    })


@app.route('/appointments/<confirmation_number>/reschedule', methods=['PUT'])
def reschedule_appointment(confirmation_number):
    """PUT /appointments/APPT-1001/reschedule - Reschedule appointment to new date/time.

    Preserves client information and service, only updates date/time.

    Request body:
    {
        "date": "2025-11-20",
        "start_time": "14:00"
    }
    """
    appointment = next(
        (apt for apt in appointments if apt["confirmation_number"] == confirmation_number),
        None
    )

    if not appointment:
        return jsonify({
            "success": False,
            "error": f"Appointment '{confirmation_number}' not found"
        }), 404

    # Check if cancelled
    if appointment.get("status") == "cancelled":
        return jsonify({
            "success": False,
            "error": f"Cannot reschedule cancelled appointment {confirmation_number}"
        }), 400

    # Get new date/time from request
    data = request.json
    if not data or "date" not in data or "start_time" not in data:
        return jsonify({
            "success": False,
            "error": "Missing required fields: date, start_time"
        }), 400

    new_date = data["date"]
    new_start_time = data["start_time"]

    # Validate new date format
    try:
        new_date_obj = datetime.strptime(new_date, "%Y-%m-%d")
        if new_date_obj.date() < datetime.now().date():
            return jsonify({
                "success": False,
                "error": "New date must be today or in the future"
            }), 400
    except ValueError:
        return jsonify({
            "success": False,
            "error": "Invalid date format. Use YYYY-MM-DD"
        }), 400

    # Validate new time format
    try:
        datetime.strptime(new_start_time, "%H:%M")
    except ValueError:
        return jsonify({
            "success": False,
            "error": "Invalid time format. Use HH:MM"
        }), 400

    # Check if new slot is available
    service_id = appointment["service_id"]
    available_slots = generate_time_slots(service_id)

    slot_available = any(
        slot["date"] == new_date and
        slot["start_time"] == new_start_time
        for slot in available_slots
    )

    if not slot_available:
        # Get alternatives
        alternatives = [
            s for s in available_slots
            if s["date"] >= new_date
        ][:5]
        return jsonify({
            "success": False,
            "error": "This time slot is not available",
            "alternatives": alternatives
        }), 409

    # Get service for duration calculation
    service = next((s for s in config.SERVICES if s["id"] == service_id), None)
    start_time_obj = datetime.strptime(new_start_time, "%H:%M")
    end_time_obj = start_time_obj + timedelta(minutes=service['duration_minutes'])

    # Update appointment
    appointment["date"] = new_date
    appointment["start_time"] = new_start_time
    appointment["end_time"] = end_time_obj.strftime("%H:%M")
    appointment["rescheduled_at"] = datetime.now().isoformat()

    return jsonify({
        "success": True,
        "message": f"Appointment {confirmation_number} has been rescheduled",
        "appointment": appointment
    })


@app.route('/appointments', methods=['GET'])
def list_appointments():
    """GET /appointments - List all appointments (for debugging)."""
    return jsonify({
        "success": True,
        "appointments": appointments,
        "total": len(appointments)
    })


@app.route('/health', methods=['GET'])
def health_check():
    """GET /health - Health check endpoint."""
    return jsonify({
        "success": True,
        "status": "healthy",
        "total_appointments": len(appointments),
        "timestamp": datetime.now().isoformat()
    })


def print_startup_info():
    """Print server startup information."""
    print("=" * 70)
    print("🚀 MOCK API SERVER")
    print("=" * 70)
    print(f"\n📍 Server: http://localhost:{config.MOCK_API_PORT}")
    print(f"📅 Services: {len(config.SERVICES)}")
    for service in config.SERVICES:
        print(f"   - {service['name']} ({service['duration_minutes']} min)")
    print(f"\n🏥 Provider: {config.ASSIGNED_PERSON['name']}")
    print(f"📍 Location: {config.LOCATION['name']}")
    print(f"   Address: {config.LOCATION['address']}")
    print(f"\n⏰ Operating Hours:")
    print(f"   Days: {', '.join(config.OPERATING_HOURS['days']).title()}")
    print(f"   Time: {config.OPERATING_HOURS['start_time']} - {config.OPERATING_HOURS['end_time']}")
    print(f"   Slots: {config.OPERATING_HOURS['slot_duration_minutes']} minutes each")

    print("\n📡 Endpoints:")
    print("   GET   /services                     - List services")
    print("   GET   /availability?service_id=...  - Get time slots")
    print("   POST  /appointments                 - Create appointment")
    print("   GET   /appointments/<conf_num>      - Get appointment")
    print("   PATCH /appointments/<conf_num>      - Cancel appointment (v1.2)")
    print("   PUT   /appointments/<conf_num>/reschedule - Reschedule appointment (v1.3)")
    print("   GET   /appointments                 - List all (debug)")
    print("   GET   /health                       - Health check")

    print("\n✅ Server ready! Waiting for requests...")
    print("=" * 70)


if __name__ == '__main__':
    print_startup_info()
    app.run(
        debug=True,
        port=config.MOCK_API_PORT,
        host='0.0.0.0'
    )
