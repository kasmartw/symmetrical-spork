# 🚀 Quick Start Guide - Agent v2 with Mock API

## Overview

This guide shows you how to run the appointment booking agent with the mock API server.

---

## Prerequisites

- Python 3.10+
- OpenAI API Key
- Two terminal windows

---

## Setup (One-Time)

### 1. Install Dependencies

```bash
cd agent-appoiments-v2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -e ".[dev]"
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your OpenAI API key
nano .env  # or vim, code, etc.
```

Add your key:
```
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
```

---

## Running the System

You need **TWO terminals** running simultaneously:

### Terminal 1: Mock API Server

```bash
cd agent-appoiments-v2
source venv/bin/activate

# Option 1: Using script
./run_mock_api.sh

# Option 2: Direct Python
python mock_api.py
```

**Expected output:**
```
======================================================================
🚀 MOCK API SERVER
======================================================================

📍 Server: http://localhost:5000
📅 Services: 3
   - General Consultation (30 min)
   - Specialized Consultation (60 min)
   - Follow-up Appointment (20 min)

🏥 Provider: Dr. Garcia
📍 Location: Downtown Medical Center
   Address: 123 Main Street, Downtown

⏰ Operating Hours:
   Days: Monday, Tuesday, Wednesday, Thursday, Friday
   Time: 09:00 - 18:00
   Slots: 30 minutes each

📡 Endpoints:
   GET  /services                     - List services
   GET  /availability?service_id=...  - Get time slots
   POST /appointments                 - Create appointment
   GET  /health                       - Health check

✅ Server ready! Waiting for requests...
======================================================================
```

**Keep this terminal running!**

---

### Terminal 2: Chat with Agent

```bash
cd agent-appoiments-v2
source venv/bin/activate

# Run chat CLI
python chat_cli.py
```

**Expected output:**
```
======================================================================
🤖  APPOINTMENT BOOKING AGENT - Interactive Chat CLI
======================================================================

Commands:
  /quit or /exit  - Exit the chat
  /state          - Show current state
  /data           - Show collected data
  /clear          - Start new conversation
  /help           - Show this help

======================================================================

🔄 Initializing agent...
✅ Agent ready!

💬 Start chatting! (Type /help for commands)

👤 You:
```

---

## Example Conversation

```
👤 You: Hello, I need an appointment

🔧 [Agent is using tools...]
   Calling: get_services_tool

🤖 Agent: Hello! I'd be happy to help you book an appointment.

         We offer the following services:

         1. General Consultation (30 min)
         2. Specialized Consultation (60 min)
         3. Follow-up Appointment (20 min)

         Which service would you like to book?

👤 You: General consultation please

🔧 [Agent is using tools...]
   Calling: get_availability_tool

🤖 Agent: Great! I found several available slots for General Consultation:

         Provider: Dr. Garcia
         Location: Downtown Medical Center, 123 Main Street

         Available times:
         1. Monday, 2025-11-11 at 09:00 - 09:30
         2. Monday, 2025-11-11 at 09:30 - 10:00
         3. Monday, 2025-11-11 at 10:00 - 10:30
         ...

         Which date and time works for you?

👤 You: Monday at 10:00

🤖 Agent: Perfect! What's your full name?

👤 You: John Doe

🤖 Agent: Thank you, John! Could you please provide your email address?

👤 You: john@example.com

🔧 [Agent is using tools...]
   Calling: validate_email_tool

🤖 Agent: Great! Your email has been validated.
         Now, could you please provide your phone number?

👤 You: 555-1234567

🔧 [Agent is using tools...]
   Calling: validate_phone_tool

🤖 Agent: Perfect! Let me confirm your appointment details:

         📋 APPOINTMENT SUMMARY
         Service: General Consultation
         Date: 2025-11-11
         Time: 10:00 - 10:30
         Provider: Dr. Garcia
         Location: Downtown Medical Center
         Name: John Doe
         Email: john@example.com
         Phone: 555-1234567

         Is this correct? (yes/no)

👤 You: yes

🔧 [Agent is using tools...]
   Calling: create_appointment_tool

🤖 Agent: ✅ Appointment confirmed! Confirmation number: APPT-1001

         📋 APPOINTMENT DETAILS:
         Confirmation: APPT-1001
         Service: General Consultation
         Date: 2025-11-11
         Time: 10:00 - 10:30
         Provider: Dr. Garcia
         Location: Downtown Medical Center
         Client: John Doe
         Email: john@example.com
         Phone: 555-1234567

         Thank you for booking with us! We look forward to seeing you. 🎉

👤 You: /quit

👋 Goodbye!
```

---

## Available Commands During Chat

| Command | Description |
|---------|-------------|
| `/quit` or `/exit` | Exit the chat |
| `/state` | Show current conversation state |
| `/data` | Show collected appointment data |
| `/clear` | Start a new conversation |
| `/help` | Show help message |

---

## Testing the API Directly

You can test the mock API with curl:

```bash
# Get services
curl http://localhost:5000/services

# Get availability
curl "http://localhost:5000/availability?service_id=srv-001"

# Health check
curl http://localhost:5000/health
```

---

## Troubleshooting

### Mock API won't start

**Error:** `Address already in use`

**Solution:** Port 5000 is already taken. Kill the existing process:
```bash
lsof -ti:5000 | xargs kill -9
```

---

### Chat CLI can't connect to API

**Error:** `[ERROR] Could not connect to API`

**Solution:** Make sure mock API is running in Terminal 1:
```bash
# Check if API is running
curl http://localhost:5000/health

# If not, start it:
python mock_api.py
```

---

### Agent gives validation errors

**Error:** `[INVALID] Email ... is not valid`

**Cause:** Email/phone validation failed

**Solution:** Provide valid format:
- Email: `user@example.com`
- Phone: At least 7 digits (can include spaces/hyphens)

---

## Running Tests

```bash
# All tests
pytest

# Only unit tests (including new API tools tests)
pytest tests/unit -v

# Only integration tests
pytest tests/integration -v

# With coverage
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

---

## Configuration

Edit `src/config.py` to customize:

- **Services:** Add/remove/modify services
- **Operating Hours:** Change business hours
- **Location:** Update office details
- **Provider:** Change assigned doctor/professional

No code changes needed - just edit the config!

---

## Architecture

```
┌─────────────┐           ┌─────────────┐
│   Chat CLI  │◄─────────►│  Mock API   │
│             │   HTTP    │             │
│  (Terminal) │ requests  │  (Terminal) │
│             │           │             │
│  Agent +    │           │  Flask +    │
│  LangGraph  │           │  In-Memory  │
│  GPT-4      │           │  Storage    │
└─────────────┘           └─────────────┘
      │                         │
      │                         │
      ▼                         ▼
  LangChain                 Business
   Tools                    Logic
   Security                 (config.py)
```

---

## Next Steps

1. **Customize services** in `src/config.py`
2. **Add new tools** in `src/tools.py`
3. **Modify system prompt** in `src/agent.py`
4. **Write tests** for new features

---

## Resources

- Full documentation: `README.md`
- Testing guide: `TESTING_GUIDE.md`
- Chat instructions: `CHAT_INSTRUCTIONS.md`
- Project instructions: `CLAUDE.md`

---

**Questions?** Check the documentation or run `/help` in the chat CLI.
