# 🤖 Appointment Booking Agent

A conversational AI agent built with LangGraph that helps users book appointments through natural conversation. The agent intelligently collects information, validates data, and creates appointments while providing a friendly user experience.

## ✨ Features

- **Natural Conversation Flow**: Step-by-step appointment booking through chat
- **Smart Validation**: Validates email, phone, date, and time automatically
- **Real-time Availability**: Checks and displays available time slots
- **Complete Summaries**: Shows full appointment details before confirmation
- **Error Handling**: Friendly error messages with alternative suggestions
- **LangGraph Integration**: Uses latest LangGraph for agent orchestration
- **Tool-based Architecture**: Modular tools for services, availability, and validation

## 🏗️ Architecture

```
┌─────────────────┐
│  User Interface │
└────────┬────────┘
         │
    ┌────▼─────┐
    │  Agent   │ (LangGraph + GPT-4o-mini)
    │  (agent.py) │
    └────┬─────┘
         │
    ┌────▼─────┐
    │  Tools   │ (get_services, get_availability, etc.)
    └────┬─────┘
         │
    ┌────▼─────┐
    │ Mock API │ (Flask Server)
    │ (mock_api.py) │
    └──────────┘
```

## 📋 Prerequisites

- Python 3.11 or higher
- OpenAI API key
- Internet connection

## 🚀 Quick Start

### 1. Clone or Download the Project

```bash
cd agent-appoiments
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-api-key-here
```

### 5. Start the Mock API Server

In one terminal:

```bash
python mock_api.py
```

You should see:
```
🚀 Mock API Server starting...
📍 Running on http://localhost:5000
✅ Server ready!
```

### 6. Run the Agent

In another terminal:

```bash
python agent.py
```

### 7. Start Booking!

The agent will greet you and guide you through the booking process.

Example conversation:
```
🤖 Agent: Hi! 👋 How can I help you today?

👤 You: I want to book an appointment

🤖 Agent: Great! Let me show you our available services...
```

## 🧪 Testing

Run the automated test suite:

```bash
python test_agent.py
```

This will:
1. Test individual tools (services, availability, validation)
2. Simulate a complete booking conversation
3. Verify all functionality works correctly

## 📁 Project Structure

```
agent-appoiments/
├── .env                 # Environment variables (create this)
├── .env.example         # Template for .env file
├── requirements.txt     # Python dependencies
├── config.py           # Configuration (services, hours, location)
├── mock_api.py         # Flask API server
├── agent.py            # Main LangGraph agent
├── test_agent.py       # Test suite
└── README.md           # This file
```

## ⚙️ Configuration

Edit `config.py` to customize:

### Services
```python
SERVICES = [
    {"id": "srv-001", "name": "General Consultation", "duration_minutes": 30},
    {"id": "srv-002", "name": "Specialized Consultation", "duration_minutes": 60},
]
```

### Assigned Person
```python
ASSIGNED_PERSON = {
    "name": "Dr. Garcia",
    "type": "doctor"
}
```

### Location
```python
LOCATION = {
    "name": "Downtown Office",
    "address": "123 Main Street, Downtown"
}
```

### Operating Hours
```python
OPERATING_HOURS = {
    "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "start_time": "09:00",
    "end_time": "18:00",
    "slot_duration_minutes": 30
}
```

## 🔧 API Endpoints

The Mock API provides these endpoints:

### GET /services
Returns list of available services.

### GET /availability
Query params: `service_id`, `date_from` (optional)

Returns available time slots for the next 7 days.

### POST /appointments
Create a new appointment.

Body:
```json
{
  "service_id": "srv-001",
  "date": "2024-11-15",
  "start_time": "10:00",
  "client": {
    "name": "John Smith",
    "email": "john@example.com",
    "phone": "555-1234"
  }
}
```

### GET /health
Health check endpoint.

## 🛠️ Tools Available to Agent

The agent has access to these tools:

1. **get_services()**: Retrieves available services
2. **get_availability(service_id, date_from)**: Gets available time slots
3. **create_appointment(...)**: Creates an appointment
4. **validate_email(email)**: Validates email format
5. **validate_phone(phone)**: Validates phone number

## 📝 Conversation Flow

1. **Start**: User expresses intention to book
2. **Service Selection**: Agent shows services, user chooses
3. **Availability**: Agent displays available slots
4. **Date Selection**: User picks a date
5. **Time Selection**: User picks a time
6. **Name Collection**: Agent asks for full name
7. **Email Collection**: Agent validates email
8. **Phone Collection**: Agent validates phone
9. **Summary**: Agent shows complete details
10. **Confirmation**: User confirms or modifies
11. **Creation**: Agent creates appointment
12. **Completion**: Confirmation number provided

## 🎯 Key Features

### Smart Validation
- Email must contain @ and domain
- Phone must have at least 7 digits
- Dates must be in the future
- Times must be in available slots

### Progressive Context
The agent remembers what you've said and doesn't ask twice.

### Friendly Error Handling
When errors occur, the agent explains what went wrong and how to fix it.

### Complete Summaries
Before creating, you see:
- Service details
- Date and time
- Assigned person
- Location
- Your contact information

### Alternative Suggestions
If a slot becomes unavailable, the agent immediately offers alternatives.

## 🐛 Troubleshooting

### "OPENAI_API_KEY not found"
Make sure you created `.env` file with your API key:
```
OPENAI_API_KEY=sk-your-key-here
```

### "Error connecting to the booking system"
Make sure the mock API is running:
```bash
python mock_api.py
```

### Port 5000 already in use
Edit `config.py` and change `MOCK_API_PORT` to another port (e.g., 5001).

### Agent not responding
Check your internet connection and verify your OpenAI API key is valid.

## 🔐 Security Notes

- Never commit your `.env` file to version control
- Keep your OpenAI API key secure
- The mock API stores data in memory (resets on restart)
- For production, replace mock API with real database

## 📊 Data Flow

```
User Input
    ↓
LangGraph Agent
    ↓
Tool Selection (LLM decides which tool to use)
    ↓
Tool Execution (API calls)
    ↓
Response Processing
    ↓
Natural Language Response
    ↓
User
```

## 🚀 Advanced Usage

### Custom Model
Edit `agent.py` to use a different model:
```python
llm = ChatOpenAI(
    model="gpt-4o",  # or "gpt-4", "gpt-3.5-turbo"
    temperature=0.7
)
```

### Adding New Services
Simply edit `config.py` and add to the `SERVICES` list:
```python
{"id": "srv-003", "name": "Follow-up Visit", "duration_minutes": 20}
```

### Changing Operating Hours
Edit `config.py`:
```python
OPERATING_HOURS = {
    "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
    "start_time": "08:00",
    "end_time": "20:00",
    "slot_duration_minutes": 15
}
```

## 📈 Performance

- Average response time: 1-3 seconds
- Supported concurrent users: Multiple (Flask development server)
- For production: Use gunicorn or similar WSGI server

## 🤝 Contributing

To extend this agent:

1. Add new tools in `agent.py`
2. Update the system prompt with new capabilities
3. Add corresponding API endpoints in `mock_api.py`
4. Test with `test_agent.py`

## 📄 License

This is a demonstration project for educational purposes.

## 🙏 Credits

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent orchestration
- [LangChain](https://github.com/langchain-ai/langchain) - LLM framework
- [OpenAI](https://openai.com/) - Language models
- [Flask](https://flask.palletsprojects.com/) - API server

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review the code comments
3. Run `test_agent.py` to verify setup

## 🎉 Example Session

```
🤖 Agent: Hi! 👋 I'm here to help you book an appointment. What can I do for you today?

👤 You: I need an appointment

🤖 Agent: Perfect! Let me show you our available services.
📋 Available Services:
• General Consultation (30 minutes)
• Specialized Consultation (60 minutes)

Which service would you like?

👤 You: General consultation

🤖 Agent: Great choice! Let me check availability...
📅 Available slots for General Consultation:
📅 Wednesday, November 13, 2024:
   • 09:00 - 09:30
   • 10:30 - 11:00
📅 Friday, November 15, 2024:
   • 15:00 - 15:30

Which date works for you?

👤 You: Friday at 3pm

🤖 Agent: Perfect! Friday, November 15 at 15:00 ✅
What's your full name?

👤 You: John Smith

🤖 Agent: Thanks John! What's your email address?

👤 You: john@email.com

🤖 Agent: Great! 📧 What's your phone number?

👤 You: 555-1234

🤖 Agent: Excellent! Let me show you a summary:

✅ APPOINTMENT SUMMARY:
📋 Service: General Consultation
📅 Date: Friday, November 15, 2024
⏰ Time: 15:00 - 15:30
👤 With: Dr. Garcia
📍 Location: Downtown Office, 123 Main Street

CLIENT INFORMATION:
👤 Name: John Smith
📧 Email: john@email.com
📞 Phone: 555-1234

Would you like to confirm this appointment?

👤 You: Yes

🤖 Agent: ✅ Your appointment is confirmed!
Confirmation number: APPT-1001

See you on Friday, November 15 at 3:00 PM! 🎉
```

---

Made with ❤️ using LangGraph and OpenAI
