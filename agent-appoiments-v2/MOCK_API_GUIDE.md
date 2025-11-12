# 🎯 Mock API Implementation Guide

## Overview

This document explains the mock API implementation for `agent-appoiments-v2`, which simulates a real appointment booking backend.

---

## What Changed?

### New Files Added

1. **`src/config.py`** - Business logic configuration
   - Services (consultations types)
   - Operating hours
   - Provider information
   - Location details
   - API settings

2. **`mock_api.py`** - Flask REST API server
   - GET /services
   - GET /availability
   - POST /appointments
   - GET /health
   - In-memory storage

3. **`run_mock_api.sh`** - Convenience script to start server

4. **`QUICKSTART.md`** - Complete user guide

5. **`MOCK_API_GUIDE.md`** - This technical guide

### Modified Files

1. **`src/tools.py`** - Added 3 new tools:
   - `get_services_tool()` - Fetch services from API
   - `get_availability_tool(service_id, date_from)` - Get time slots
   - `create_appointment_tool(...)` - Create booking

2. **`src/agent.py`** - Updated to use new tools:
   - Added tools to imports
   - Added to tools list
   - Enhanced system prompt with full workflow

3. **`tests/unit/test_api_tools.py`** - NEW: 11 tests for API tools

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                      │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
            ┌─────────────────────────────┐
            │       chat_cli.py           │
            │   (Interactive Terminal)    │
            └──────────────┬──────────────┘
                           │
                           ▼
            ┌─────────────────────────────┐
            │      src/agent.py           │
            │  (LangGraph + GPT-4 Mini)   │
            │   - State machine           │
            │   - Security checks         │
            │   - Tool orchestration      │
            └──────────────┬──────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
    ┌───────────────────┐   ┌────────────────────┐
    │  Validation Tools │   │   API Tools        │
    │  - validate_email │   │  - get_services    │
    │  - validate_phone │   │  - get_availability│
    └───────────────────┘   │  - create_appt     │
                            └────────┬───────────┘
                                     │
                                     │ HTTP Requests
                                     ▼
                          ┌──────────────────────┐
                          │   mock_api.py        │
                          │  (Flask Server)      │
                          │  localhost:5000      │
                          │                      │
                          │  Endpoints:          │
                          │  - /services         │
                          │  - /availability     │
                          │  - /appointments     │
                          │  - /health           │
                          │                      │
                          │  Storage:            │
                          │  - In-memory list    │
                          │  - Resets on restart │
                          └──────┬───────────────┘
                                 │
                                 ▼
                          ┌──────────────┐
                          │  src/config.py│
                          │  (Business    │
                          │   Logic)      │
                          └───────────────┘
```

---

## API Endpoints

### 1. GET /services

List all available services.

**Request:**
```bash
curl http://localhost:5000/services
```

**Response:**
```json
{
  "success": true,
  "services": [
    {
      "id": "srv-001",
      "name": "General Consultation",
      "duration_minutes": 30
    },
    {
      "id": "srv-002",
      "name": "Specialized Consultation",
      "duration_minutes": 60
    },
    {
      "id": "srv-003",
      "name": "Follow-up Appointment",
      "duration_minutes": 20
    }
  ],
  "total": 3
}
```

---

### 2. GET /availability

Get available time slots for a service.

**Parameters:**
- `service_id` (required) - Service ID (e.g., "srv-001")
- `date_from` (optional) - Start date in YYYY-MM-DD format (defaults to today)

**Request:**
```bash
curl "http://localhost:5000/availability?service_id=srv-001&date_from=2025-11-12"
```

**Response:**
```json
{
  "success": true,
  "service": {
    "id": "srv-001",
    "name": "General Consultation",
    "duration_minutes": 30
  },
  "available_slots": [
    {
      "date": "2025-11-12",
      "day": "Tuesday",
      "start_time": "09:00",
      "end_time": "09:30"
    },
    {
      "date": "2025-11-12",
      "day": "Tuesday",
      "start_time": "09:30",
      "end_time": "10:00"
    }
  ],
  "total_slots": 42,
  "assigned_person": {
    "name": "Dr. Garcia",
    "type": "doctor",
    "specialization": "General Practice"
  },
  "location": {
    "name": "Downtown Medical Center",
    "address": "123 Main Street, Downtown",
    "city": "Springfield",
    "phone": "555-0100"
  }
}
```

---

### 3. POST /appointments

Create a new appointment.

**Request Body:**
```json
{
  "service_id": "srv-001",
  "date": "2025-11-12",
  "start_time": "10:00",
  "client": {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "555-1234567"
  }
}
```

**Success Response (201):**
```json
{
  "success": true,
  "appointment": {
    "confirmation_number": "APPT-1001",
    "service_id": "srv-001",
    "service_name": "General Consultation",
    "date": "2025-11-12",
    "start_time": "10:00",
    "end_time": "10:30",
    "duration_minutes": 30,
    "client": {
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "555-1234567"
    },
    "assigned_person": {
      "name": "Dr. Garcia",
      "type": "doctor",
      "specialization": "General Practice"
    },
    "location": {
      "name": "Downtown Medical Center",
      "address": "123 Main Street, Downtown",
      "city": "Springfield",
      "phone": "555-0100"
    },
    "status": "confirmed",
    "created_at": "2025-11-12T10:15:30.123Z"
  },
  "message": "Appointment confirmed! Confirmation number: APPT-1001"
}
```

**Error Response - Slot Unavailable (409):**
```json
{
  "success": false,
  "error": "This time slot is no longer available",
  "alternatives": [
    {
      "date": "2025-11-12",
      "day": "Tuesday",
      "start_time": "11:00",
      "end_time": "11:30"
    }
  ]
}
```

**Error Response - Invalid Email (400):**
```json
{
  "success": false,
  "error": "Invalid email format. Please provide a valid email (e.g., name@example.com)"
}
```

---

### 4. GET /health

Health check endpoint.

**Request:**
```bash
curl http://localhost:5000/health
```

**Response:**
```json
{
  "success": true,
  "status": "healthy",
  "total_appointments": 3,
  "timestamp": "2025-11-12T10:30:00.000Z"
}
```

---

## Configuration (src/config.py)

All business logic is centralized and can be modified without code changes:

```python
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

MOCK_API_BASE_URL = "http://localhost:5000"
MOCK_API_PORT = 5000
```

---

## Conversation Flow

The agent follows this state machine:

```
1. GREETING
   └─> calls get_services_tool()
       └─> Shows available services

2. COLLECT_SERVICE
   └─> User selects service
       └─> calls get_availability_tool(service_id)
           └─> Shows available time slots

3. COLLECT_DATE
   └─> User chooses date

4. COLLECT_TIME
   └─> User chooses time

5. COLLECT_NAME
   └─> User provides name

6. COLLECT_EMAIL
   └─> User provides email
       └─> calls validate_email_tool(email)

7. COLLECT_PHONE
   └─> User provides phone
       └─> calls validate_phone_tool(phone)

8. SHOW_SUMMARY
   └─> Display all collected data

9. CONFIRM
   └─> User confirms (yes/no)
       └─> If yes:
           └─> calls create_appointment_tool(...)
               └─> Shows confirmation number

10. COMPLETE
    └─> Thank user
```

---

## Running the System

### Terminal 1: Start Mock API

```bash
cd agent-appoiments-v2
source venv/bin/activate
python mock_api.py
# or: ./run_mock_api.sh
```

### Terminal 2: Run Agent

```bash
cd agent-appoiments-v2
source venv/bin/activate
python chat_cli.py
```

---

## Testing

### Unit Tests

All API tools have comprehensive unit tests:

```bash
# Run only API tools tests
pytest tests/unit/test_api_tools.py -v

# All unit tests
pytest tests/unit -v
```

**Test Coverage:**
- ✅ get_services_tool: 3 tests
- ✅ get_availability_tool: 4 tests
- ✅ create_appointment_tool: 4 tests
- **Total: 11 new tests**

### Manual Testing

```bash
# Start mock API
python mock_api.py

# In another terminal, test endpoints:
curl http://localhost:5000/services
curl "http://localhost:5000/availability?service_id=srv-001"
curl http://localhost:5000/health

# Create appointment
curl -X POST http://localhost:5000/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "srv-001",
    "date": "2025-11-15",
    "start_time": "10:00",
    "client": {
      "name": "Test User",
      "email": "test@example.com",
      "phone": "555-1234567"
    }
  }'
```

---

## Key Features

### 1. Realistic Slot Generation

- Generates slots for next 14 days
- Respects operating hours (Mon-Fri, 9am-6pm)
- Excludes lunch break (1pm-2pm)
- 75% availability (simulates realistic booking)
- Slot duration: 30 minutes

### 2. Validation

**API-Level:**
- Email format validation (regex)
- Phone number validation (≥7 digits)
- Service existence check
- Date format validation (YYYY-MM-DD)
- Time format validation (HH:MM)
- Slot availability check

**Agent-Level (before API call):**
- Email validation via validate_email_tool
- Phone validation via validate_phone_tool

### 3. Error Handling

- Connection errors → Graceful error messages
- Missing parameters → HTTP 400 with details
- Invalid service → HTTP 404
- Slot unavailable → HTTP 409 with alternatives
- All errors return JSON with `success: false`

---

## Comparison: v1 vs v2

| Feature | v1 (agent-appoiments) | v2 (agent-appoiments-v2) |
|---------|----------------------|-------------------------|
| **Mock API** | ✅ Flask server | ✅ Enhanced Flask server |
| **Config** | ✅ config.py | ✅ config.py (improved) |
| **API Tools** | ✅ 3 tools | ✅ 5 tools (added 3 new) |
| **Tests** | ❌ No tests | ✅ 11 comprehensive tests |
| **Security** | ❌ None | ✅ 3-layer detection |
| **State Machine** | ❌ Informal | ✅ Formal with guards |
| **Documentation** | ⚠️ Basic | ✅ Complete (4 docs) |
| **LangGraph** | ⚠️ 0.x | ✅ 1.0+ (modern) |
| **Production Ready** | ❌ No | ✅ PostgreSQL support |

---

## Customization

### Add a New Service

Edit `src/config.py`:

```python
SERVICES = [
    {"id": "srv-001", "name": "General Consultation", "duration_minutes": 30},
    {"id": "srv-004", "name": "Physical Therapy", "duration_minutes": 45},  # NEW
]
```

Restart mock API. No code changes needed!

### Change Operating Hours

Edit `src/config.py`:

```python
OPERATING_HOURS = {
    "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],  # Added Saturday
    "start_time": "08:00",  # Earlier start
    "end_time": "20:00",    # Later end
    "slot_duration_minutes": 15,  # Shorter slots
    "lunch_break": {
        "start": "12:00",
        "end": "13:00"
    }
}
```

### Change Provider/Location

Edit `src/config.py`:

```python
ASSIGNED_PERSON = {
    "name": "Dr. Smith",
    "type": "dentist",
    "specialization": "Orthodontics"
}

LOCATION = {
    "name": "Uptown Dental Clinic",
    "address": "456 Oak Avenue, Uptown",
    "city": "Springfield",
    "phone": "555-0200"
}
```

---

## Troubleshooting

### Mock API won't start

**Error:** `Address already in use`

```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Or change port in config.py
MOCK_API_PORT = 5001
```

### Agent can't connect to API

**Error:** `[ERROR] Could not connect to API`

```bash
# Verify API is running
curl http://localhost:5000/health

# Check API logs in Terminal 1
# Restart if needed:
python mock_api.py
```

### Tests failing

```bash
# Clear pytest cache
rm -rf .pytest_cache __pycache__ tests/__pycache__

# Reinstall
pip install -e ".[dev]"

# Run tests
pytest tests/unit -v
```

---

## Future Enhancements

Potential improvements:

1. **Persistent Storage**
   - Replace in-memory list with SQLite
   - Or use the existing PostgresSaver

2. **Authentication**
   - Add API key authentication
   - JWT tokens for production

3. **Rate Limiting**
   - Prevent API abuse
   - Flask-Limiter integration

4. **Real Integrations**
   - Google Calendar API
   - Twilio for SMS confirmations
   - SendGrid for email notifications

5. **Advanced Features**
   - Appointment cancellation
   - Rescheduling
   - Multiple providers
   - Waitlist management

---

## Resources

- **Main README:** `README.md`
- **Quick Start:** `QUICKSTART.md`
- **Testing Guide:** `TESTING_GUIDE.md`
- **Chat Instructions:** `CHAT_INSTRUCTIONS.md`
- **Project Instructions:** `CLAUDE.md`

---

**Questions?** Check the documentation or test the system with `python chat_cli.py`!
