# APPOINTMENT BOOKING AGENT - LOGICAL SPECIFICATION

## OBJECTIVE
Build a conversational AI agent that helps users book appointments through natural language interaction, collecting necessary information step-by-step and creating appointments via a mock API.

---

## CORE CONCEPT

**What the system does:**
1. User expresses intent to book an appointment
2. Agent asks questions ONE at a time to collect 6 required pieces of information
3. Agent shows complete summary including system-assigned data
4. User confirms
5. System creates appointment and returns confirmation number

**Key principle:** The agent guides the conversation, asking one question at a time, validating progressively, and always showing a complete summary before final confirmation.

---

## SYSTEM ARCHITECTURE

### 3-Layer Architecture:

```
LAYER 1: CONVERSATIONAL AGENT (agent.py)
├── NLP Engine: Understands user intent and extracts data
├── State Manager: Tracks conversation progress and collected data
├── Tools: 5 functions that can be called
└── Flow Controller: Decides what to ask next

LAYER 2: MOCK API (mock_api.py)
├── Service catalog
├── Availability generator
└── Appointment creator

LAYER 3: CONFIGURATION (config.py)
├── Services list (agnostic)
├── Assigned person (fixed for all appointments)
└── Location (fixed for all appointments)
```

---

## DATA FLOW

### INPUT (Collected from User):
1. **Service** - Which service they want
2. **Date** - Preferred date from available options
3. **Time** - Preferred time from available slots
4. **Name** - Full name
5. **Email** - Email address (validated)
6. **Phone** - Phone number (validated)

### SYSTEM-PROVIDED (Not asked to user):
7. **Assigned Person** - Always the same (from config)
8. **Location** - Always the same (from config)

### OUTPUT (To User):
- Confirmation number
- Complete appointment details

---

## STATE MACHINE LOGIC

The conversation follows this state sequence:

```
START
  ↓ [detect intent]
COLLECT_SERVICE
  ↓ [service selected]
SHOW_AVAILABILITY
  ↓ [show options]
COLLECT_DATE
  ↓ [date valid]
COLLECT_TIME
  ↓ [time valid & available]
COLLECT_NAME
  ↓ [name provided]
COLLECT_EMAIL
  ↓ [email valid]
COLLECT_PHONE
  ↓ [phone valid]
SHOW_SUMMARY
  ↓ [user reviews]
CONFIRM
  ↓ [user confirms]
CREATE_APPOINTMENT
  ↓ [API success]
COMPLETE
```

**Important:** At each validation failure, stay in same state and re-ask with helpful guidance.

---

## AGENT TOOLS (Functions)

The agent has access to 5 tools:

### 1. get_services()
**Purpose:** Retrieve list of available services
**When to call:** When user wants to book or asks what's available
**Returns:** Formatted list of services with IDs and durations

### 2. get_availability(service_id)
**Purpose:** Get available time slots for a service
**When to call:** After service is selected
**Returns:** List of dates and times grouped by day

### 3. create_appointment(service_id, date, time, name, email, phone)
**Purpose:** Create the appointment
**When to call:** ONLY after showing summary and getting confirmation
**Returns:** Confirmation number and complete appointment details

### 4. validate_email(email)
**Purpose:** Check if email format is correct
**When to call:** When user provides email, before accepting it
**Returns:** Valid/Invalid with guidance if invalid

### 5. validate_phone(phone)
**Purpose:** Check if phone has minimum 7 digits
**When to call:** When user provides phone, before accepting it
**Returns:** Valid/Invalid with guidance if invalid

---

## VALIDATION RULES

### Email Validation:
- Must contain `@`
- Must contain `.` after `@`
- Regex: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`
- If invalid: Explain and give example (name@example.com)

### Phone Validation:
- Must have at least 7 numeric digits
- Hyphens and spaces allowed but ignored
- If invalid: Explain minimum length requirement

### Date Validation:
- Must be a future date (not today, not past)
- Must be in available slots
- If unavailable: Offer alternative dates immediately

### Time Validation:
- Must be in available slots for selected date
- If unavailable: Offer alternative times immediately

### Service Validation:
- Must be in the services list
- If invalid: Show available services

---

## CONVERSATIONAL RULES

### Agent Personality:
- Friendly and warm
- Professional but not robotic
- Uses emojis moderately: 📅 ⏰ 👤 📍 📧 📞 ✅ ❌
- Never technical or cold

### Conversation Guidelines:
1. **One question at a time** - Never ask multiple questions in one message
2. **Progressive validation** - Validate each piece of data immediately
3. **Helpful errors** - If something is wrong, explain why and how to fix it
4. **Offer alternatives** - If unavailable, immediately suggest other options
5. **Always summarize** - Before creating, show complete summary
6. **Include system data** - Summary must show assigned person and location

### Message Format:
```
Short, clear messages
Use emojis for visual structure
Lists with bullet points when showing options
Clear formatting in summary
```

---

## SUMMARY FORMAT (Critical Step)

Before creating appointment, ALWAYS show this exact structure:

```
📋 APPOINTMENT SUMMARY

✅ Service: [service name]
📅 Date: [Full day, month date, year]
⏰ Time: [start time] - [end time] ([duration] minutes)
👤 With: [assigned person name]
📍 Location: [location name]
    [location address]

CLIENT INFORMATION:
👤 Name: [client name]
📧 Email: [client email]
📞 Phone: [client phone]

Confirm this appointment? (Yes/No)
```

**Why this matters:** User needs to see ALL details including who they'll meet with and where, even though they didn't choose these.

---

## ERROR HANDLING LOGIC

### Slot Becomes Unavailable (Race Condition):
```
IF create_appointment fails with "slot unavailable"
THEN:
  1. Apologize for inconvenience
  2. Call get_availability again
  3. Offer 2-3 alternative times
  4. Return to COLLECT_TIME state
```

### API Connection Error:
```
IF any API call fails with connection error
THEN:
  1. Show friendly error message
  2. Suggest trying again in a moment
  3. Do NOT show technical details
  4. Keep collected data in state
```

### Validation Failure:
```
IF email/phone validation fails
THEN:
  1. Explain what's wrong
  2. Show correct format example
  3. Re-ask for the same data
  4. Stay in same state
```

---

## CONTEXT MANAGEMENT

The agent maintains context in this structure:

```json
{
  "current_state": "COLLECT_TIME",
  "collected_data": {
    "service_id": "srv-001",
    "service_name": "General Consultation",
    "date": "2024-11-15",
    "time": null,
    "client_name": null,
    "client_email": null,
    "client_phone": null
  },
  "available_slots": [...],
  "last_question": "What time would you prefer?"
}
```

**Rules:**
- Never lose collected data
- Track which state we're in
- Remember what was last asked
- Store available slots to reference them

---

## MOCK API CONTRACT

### GET /services
```
Response: {
  "success": true,
  "services": [
    {
      "id": "srv-001",
      "name": "General Consultation",
      "duration_minutes": 30
    }
  ]
}
```

### GET /availability?service_id=srv-001
```
Response: {
  "success": true,
  "service": {...},
  "available_slots": [
    {
      "date": "2024-11-15",
      "start_time": "09:00",
      "end_time": "09:30"
    }
  ]
}
```

### POST /appointments
```
Request: {
  "service_id": "srv-001",
  "date": "2024-11-15",
  "start_time": "09:00",
  "client": {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "555-1234"
  }
}

Success Response (201): {
  "success": true,
  "appointment": {
    "confirmation_number": "APPT-1234",
    "service_name": "General Consultation",
    "date": "2024-11-15",
    "start_time": "09:00",
    "end_time": "09:30",
    "assigned_person": {
      "name": "Dr. Garcia"
    },
    "location": {
      "name": "Downtown Office",
      "address": "123 Main Street"
    }
  }
}

Error Response (400): {
  "success": false,
  "error": "Slot no longer available",
  "alternatives": [...]
}
```

---

## DECISION TREE

At each message from user, the agent must:

```
1. Determine current state
2. Extract relevant data from user message
3. IF data extraction successful:
     a. Validate data
     b. IF valid:
          - Store in context
          - Move to next state
          - Ask next question
     c. IF invalid:
          - Explain error
          - Stay in same state
          - Re-ask
4. IF data extraction failed:
     - Ask clarifying question
     - Stay in same state
5. IF user wants to cancel/modify:
     - Allow it gracefully
     - Return to appropriate state
```

---

## SUCCESS CRITERIA

The agent is working correctly when:

✅ User can complete booking with natural conversation
✅ Each question is asked separately, not bundled
✅ Validations happen immediately and give helpful feedback
✅ Summary shows all 8 data points before creating
✅ Confirmation number is provided after creation
✅ Errors are handled with friendly messages and alternatives
✅ User can see assigned person and location without asking

---

## IMPORTANT CONSTRAINTS

### What Agent MUST do:
- Ask one question at a time
- Validate progressively
- Show complete summary before creating
- Include assigned person and location in summary
- Provide helpful error messages
- Offer alternatives when something is unavailable

### What Agent MUST NOT do:
- Ask about assigned person or location
- Create appointment without confirmation
- Show technical error messages
- Ask multiple questions in one turn
- Skip validation
- Skip summary step

---

## CONFIGURATION (Agnostic Design)

The system is designed to work for ANY business by changing only config.py:

**For a medical clinic:**
- Services: Consultations, checkups
- Assigned person: Doctor name
- Location: Clinic address

**For a hair salon:**
- Services: Haircut, coloring
- Assigned person: Stylist name
- Location: Salon address

**For a law office:**
- Services: Consultation, document review
- Assigned person: Attorney name
- Location: Office address

The agent's logic never changes, only the configuration.

---

## EXECUTION FLOW EXAMPLE

```
User: "I need an appointment"
Agent: [Detects intent] "Hi! I'll help you book. [Calls get_services] What service? • General Consultation • Specialized Consultation"

User: "General consultation"
Agent: [Stores service] [Calls get_availability] "Perfect! Available: 📅 Wednesday 13: 9:00, 10:30 📅 Friday 15: 3:00 Which works for you?"

User: "Friday at 3"
Agent: [Stores date and time] "Great! Friday at 3:00 PM ✅ Your full name?"

User: "John Smith"
Agent: [Stores name] "Perfect John. Your email?"

User: "john@example.com"
Agent: [Calls validate_email] [Valid] "Thanks 📧 Your phone?"

User: "555-1234"
Agent: [Calls validate_phone] [Valid] "Excellent! 📋 SUMMARY: [shows complete summary with 8 data points] Confirm?"

User: "Yes"
Agent: [Calls create_appointment] [Success] "Done! ✅ Appointment confirmed. Number: APPT-1234"
```

---

## KEY INSIGHTS FOR AI IMPLEMENTATION

1. **State is everything** - The current state determines what question to ask next
2. **Validation before progression** - Never move to next state without validating current data
3. **Tools are not optional** - Always call the appropriate tool for each action
4. **Summary is mandatory** - Never skip showing the complete summary
5. **One question rule** - Breaking this confuses users
6. **System data is fixed** - Person and location come from config, not from slots or user
7. **Error recovery** - Always offer a path forward when something fails

---

This specification defines the complete logical behavior of the appointment booking agent. Any AI implementing this should follow these rules precisely to create a smooth, user-friendly booking experience.
