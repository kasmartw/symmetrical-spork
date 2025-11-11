"""
Configuration file for appointment booking system.
All configurable data centralized here - no need to modify code.
"""

SERVICES = [
    {"id": "srv-001", "name": "General Consultation", "duration_minutes": 30},
    {"id": "srv-002", "name": "Specialized Consultation", "duration_minutes": 60},
]

ASSIGNED_PERSON = {
    "name": "Dr. Garcia",
    "type": "doctor"
}

LOCATION = {
    "name": "Downtown Office",
    "address": "123 Main Street, Downtown"
}

OPERATING_HOURS = {
    "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "start_time": "09:00",
    "end_time": "18:00",
    "slot_duration_minutes": 30
}

# API Configuration
MOCK_API_BASE_URL = "http://localhost:5000"
MOCK_API_PORT = 5000
