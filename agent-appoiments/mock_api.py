"""
Mock API for appointment booking system.
Flask server with endpoints for services, availability, and appointments.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import random
import re
import config

app = Flask(__name__)
CORS(app)

# In-memory storage
appointments = []
appointment_counter = 1000


def generate_time_slots(service_id, date_from=None):
    """Generate available time slots based on operating hours."""
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
        except:
            pass

    # Generate slots for next 7 days
    for day_offset in range(7):
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

        # Generate time slots
        current_time = start_time
        while current_time < end_time:
            slot_datetime = current_date.replace(
                hour=current_time.hour,
                minute=current_time.minute
            )

            # Skip past times for today
            if slot_datetime > datetime.now():
                # Simulate 70% availability (30% randomly booked)
                is_available = random.random() < 0.7

                # Check if slot is already booked
                is_booked = any(
                    apt["date"] == current_date.strftime("%Y-%m-%d") and
                    apt["start_time"] == current_time.strftime("%H:%M") and
                    apt["service_id"] == service_id
                    for apt in appointments
                )

                if is_available and not is_booked:
                    end_slot_time = current_time + timedelta(minutes=service["duration_minutes"])
                    slots.append({
                        "date": current_date.strftime("%Y-%m-%d"),
                        "day": current_date.strftime("%A"),
                        "start_time": current_time.strftime("%H:%M"),
                        "end_time": end_slot_time.strftime("%H:%M")
                    })

            current_time += timedelta(minutes=config.OPERATING_HOURS["slot_duration_minutes"])

    return slots


def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone):
    """Validate phone format (at least 7 digits)."""
    digits = re.sub(r'[^\d]', '', phone)
    return len(digits) >= 7


@app.route('/services', methods=['GET'])
def get_services():
    """Get list of available services."""
    return jsonify({
        "success": True,
        "services": config.SERVICES
    })


@app.route('/availability', methods=['GET'])
def get_availability():
    """Get available time slots for a service."""
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
            "error": "Service not found"
        }), 404

    slots = generate_time_slots(service_id, date_from)

    return jsonify({
        "success": True,
        "service": service,
        "available_slots": slots,
        "total_slots": len(slots)
    })


@app.route('/appointments', methods=['POST'])
def create_appointment():
    """Create a new appointment."""
    global appointment_counter

    data = request.json

    # Validate required fields
    required_fields = ['client', 'service_id', 'date', 'start_time']
    for field in required_fields:
        if field not in data:
            return jsonify({
                "success": False,
                "error": f"Missing required field: {field}"
            }), 400

    # Validate client data
    client = data['client']
    if not all(k in client for k in ['name', 'email', 'phone']):
        return jsonify({
            "success": False,
            "error": "Client must include name, email, and phone"
        }), 400

    # Validate email
    if not validate_email(client['email']):
        return jsonify({
            "success": False,
            "error": "Invalid email format. Please provide a valid email address (e.g., name@example.com)"
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
            "error": "Service not found"
        }), 404

    # Validate date is in future
    try:
        appointment_date = datetime.strptime(data['date'], "%Y-%m-%d")
        if appointment_date.date() < datetime.now().date():
            return jsonify({
                "success": False,
                "error": "Appointment date must be in the future"
            }), 400
    except ValueError:
        return jsonify({
            "success": False,
            "error": "Invalid date format. Please use YYYY-MM-DD"
        }), 400

    # Check if slot is still available
    slot_available = any(
        slot["date"] == data['date'] and
        slot["start_time"] == data['start_time']
        for slot in generate_time_slots(data['service_id'])
    )

    if not slot_available:
        # Get alternatives
        alternatives = generate_time_slots(data['service_id'])[:5]
        return jsonify({
            "success": False,
            "error": "This time slot is no longer available",
            "alternatives": alternatives
        }), 400

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
        "assigned_person": config.ASSIGNED_PERSON,
        "location": config.LOCATION,
        "created_at": datetime.now().isoformat()
    }

    appointments.append(appointment)

    return jsonify({
        "success": True,
        "appointment": appointment,
        "message": f"Appointment created successfully! Confirmation number: {confirmation_number}"
    }), 201


@app.route('/appointments/<confirmation_number>', methods=['GET'])
def get_appointment(confirmation_number):
    """Get appointment details by confirmation number."""
    appointment = next(
        (apt for apt in appointments if apt["confirmation_number"] == confirmation_number),
        None
    )

    if not appointment:
        return jsonify({
            "success": False,
            "error": "Appointment not found"
        }), 404

    return jsonify({
        "success": True,
        "appointment": appointment
    })


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "success": True,
        "status": "healthy",
        "total_appointments": len(appointments)
    })


if __name__ == '__main__':
    print("🚀 Mock API Server starting...")
    print(f"📍 Running on http://localhost:{config.MOCK_API_PORT}")
    print(f"📅 Available services: {len(config.SERVICES)}")
    print(f"🏥 Assigned person: {config.ASSIGNED_PERSON['name']}")
    print(f"📍 Location: {config.LOCATION['name']}")
    print("\nEndpoints:")
    print("  GET  /services")
    print("  GET  /availability?service_id=srv-001")
    print("  POST /appointments")
    print("  GET  /health")
    print("\n✅ Server ready!")

    app.run(debug=True, port=config.MOCK_API_PORT, host='0.0.0.0')
