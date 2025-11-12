# Rescheduling Flow Documentation (v1.3)

## Overview

Rescheduling allows users to change appointment date/time while preserving all other details (client info, service). Follows cancellation pattern with verification → selection → confirmation → process flow.

## User Experience

**Trigger Phrases:**
- English: "reschedule", "change my appointment", "move my appointment", "different time"
- Spanish: "reagendar", "cambiar mi cita", "mover mi cita", "otra fecha"

**Flow:**
1. User expresses intent → RESCHEDULE_ASK_CONFIRMATION
2. Agent asks for confirmation number
3. Agent verifies appointment and shows current details → RESCHEDULE_VERIFY
4. Agent asks for new preferred date/time, shows availability → RESCHEDULE_SELECT_DATETIME
5. User selects new slot
6. Agent shows summary (old → new) and asks confirmation → RESCHEDULE_CONFIRM
7. User confirms → Agent reschedules → RESCHEDULE_PROCESS
8. Success → POST_ACTION

## State Machine

```
RESCHEDULE_ASK_CONFIRMATION
    ↓
RESCHEDULE_VERIFY (2 failures → POST_ACTION + offer new booking)
    ↓
RESCHEDULE_SELECT_DATETIME
    ↓
RESCHEDULE_CONFIRM (user can go back to SELECT_DATETIME)
    ↓
RESCHEDULE_PROCESS
    ↓
POST_ACTION
```

## Retry Logic

- **2 attempts** to provide valid confirmation number
- **After 2 failures:**
  - Escalate: "Cannot find appointment after multiple attempts"
  - Offer new booking OR return to POST_ACTION menu

## API Endpoint

**PUT /appointments/<conf_num>/reschedule**

Request:
```json
{
  "date": "2025-11-20",
  "start_time": "14:00"
}
```

Response (success - 200):
```json
{
  "success": true,
  "message": "Appointment APPT-1234 has been rescheduled",
  "appointment": {
    "confirmation_number": "APPT-1234",
    "date": "2025-11-20",
    "start_time": "14:00",
    "status": "confirmed",
    "rescheduled_at": "2025-11-12T15:30:00"
  }
}
```

Response (slot unavailable - 409):
```json
{
  "success": false,
  "error": "This time slot is not available",
  "alternatives": [
    {"date": "2025-11-20", "start_time": "15:00", "day": "Wednesday", "end_time": "15:30"}
  ]
}
```

**Error Codes:**
- `404`: Invalid confirmation number
- `400`: Cannot reschedule (e.g., cancelled appointment)
- `409`: Slot unavailable (includes alternatives)

## Tools

### get_appointment_tool(confirmation_number)

Retrieves appointment details for verification.

Returns:
```
[APPOINTMENT] Current appointment details:
Confirmation: APPT-1234
Service: General Consultation
Date: 2025-11-15 at 10:00
Client: John Doe
Status: confirmed
```

### reschedule_appointment_tool(confirmation_number, new_date, new_start_time)

Updates appointment to new date/time.

Returns (success):
```
[SUCCESS] Appointment APPT-1234 has been rescheduled.
Service: General Consultation
New Date: 2025-11-20 at 14:00
Status: confirmed
```

Returns (slot unavailable):
```
[ERROR] This time slot is not available

Alternative slots:
1. Wednesday, 2025-11-20 at 15:00 - 15:30
2. Wednesday, 2025-11-20 at 16:00 - 16:30
```

## Testing

**Unit Tests:**
- State machine: `tests/unit/test_state_machine.py` (2 tests)
- Intent detection: `tests/unit/test_rescheduling_intent.py` (26 tests)
- Tools: `tests/unit/test_rescheduling_tools.py` (4 tests)

**Integration Tests:**
- API: `tests/integration/test_rescheduling_api.py` (4 tests)
- Flow: `tests/integration/test_rescheduling_flow.py` (3 tests)

**Manual Testing:**
```bash
# Terminal 1: Start API
python mock_api.py

# Terminal 2: Start CLI
python chat_cli.py

# Test: "quiero reagendar mi cita"
```

## Comparison: Cancellation vs Rescheduling

| Feature | Cancellation | Rescheduling |
|---------|-------------|--------------|
| States | 4 | 5 |
| Retry logic | 2 attempts | 2 attempts |
| Escalation | POST_ACTION | POST_ACTION + new booking offer |
| Data preservation | Status → cancelled | Preserves all, updates date/time |
| Tools | 2 (cancel, get_user_appointments) | 2 (get_appointment, reschedule) |

## Implementation Summary

**v1.3 Changes:**
- 5 new states + transitions
- 2 new tools (get_appointment, reschedule)
- Enhanced intent detection (bilingual patterns)
- Mock API endpoint (PUT /reschedule)
- Chat CLI routing (priority: reschedule → cancel → exit)
- System prompts for all rescheduling states
- 39 tests total (32 unit + 7 integration)
