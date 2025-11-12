"""Configuration for appointment booking system.

All business logic centralized here - modify as needed without touching code.
"""

SERVICES = [
    {"id": "srv-001", "name": "General Consultation", "duration_minutes": 30},
    {"id": "srv-002", "name": "Specialized Consultation", "duration_minutes": 60},
    {"id": "srv-003", "name": "Follow-up Appointment", "duration_minutes": 20},
]

ASSIGNED_PERSON = {
    "name": "Dr. Garcia",
    "type": "doctor",
    "specialization": "General Practice"
}

LOCATION = {
    "name": "Downtown Medical Center",
    "address": "123 Main Street, Downtown",
    "city": "Springfield",
    "phone": "555-0100"
}

OPERATING_HOURS = {
    "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "start_time": "09:00",
    "end_time": "18:00",
    "slot_duration_minutes": 30,
    "lunch_break": {
        "start": "13:00",
        "end": "14:00"
    }
}

# API Configuration
MOCK_API_BASE_URL = "http://localhost:5000"
MOCK_API_PORT = 5000
