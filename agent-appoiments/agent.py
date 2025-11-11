"""
Appointment Booking Agent using LangGraph.
Conversational agent that helps users book appointments step by step.
"""

import os
import json
import re
import requests
from datetime import datetime, timedelta
from typing import TypedDict, Annotated, Sequence
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

import config

# Load environment variables
load_dotenv()

# Verify API key
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("⚠️  OPENAI_API_KEY not found in environment variables. Please create a .env file with your API key.")


# ============================================================================
# AGENT STATE
# ============================================================================

class AgentState(TypedDict):
    """State for the appointment booking agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    context: dict


# ============================================================================
# TOOLS - Functions the agent can call
# ============================================================================

@tool
def get_services() -> str:
    """
    Get the list of available services that can be booked.
    Use this tool when the user wants to see what services are available.
    """
    try:
        response = requests.get(f"{config.MOCK_API_BASE_URL}/services", timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            services = data.get("services", [])
            result = "📋 Available Services:\n\n"
            for service in services:
                result += f"• {service['name']} ({service['duration_minutes']} minutes)\n"
                result += f"  ID: {service['id']}\n\n"
            return result
        else:
            return "❌ Error: Could not retrieve services."
    except Exception as e:
        return f"❌ Error connecting to the booking system: {str(e)}\nPlease try again in a moment."


@tool
def get_availability(service_id: str, date_from: str = None) -> str:
    """
    Get available time slots for a specific service.

    Args:
        service_id: The ID of the service (e.g., 'srv-001')
        date_from: Optional start date in YYYY-MM-DD format
    """
    try:
        params = {"service_id": service_id}
        if date_from:
            params["date_from"] = date_from

        response = requests.get(
            f"{config.MOCK_API_BASE_URL}/availability",
            params=params,
            timeout=5
        )
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            slots = data.get("available_slots", [])
            service = data.get("service", {})

            if not slots:
                return "❌ No available slots found for this service in the next 7 days."

            result = f"📅 Available slots for {service.get('name')}:\n\n"

            # Group slots by date
            slots_by_date = {}
            for slot in slots:
                date = slot["date"]
                if date not in slots_by_date:
                    slots_by_date[date] = []
                slots_by_date[date].append(slot)

            # Format output
            for date, date_slots in list(slots_by_date.items())[:5]:  # Show max 5 days
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                result += f"📅 {date_obj.strftime('%A, %B %d, %Y')}:\n"
                for slot in date_slots[:4]:  # Show max 4 slots per day
                    result += f"   • {slot['start_time']} - {slot['end_time']}\n"
                result += "\n"

            return result
        else:
            return f"❌ Error: {data.get('error', 'Could not retrieve availability')}"
    except Exception as e:
        return f"❌ Error connecting to the booking system: {str(e)}\nPlease try again in a moment."


@tool
def create_appointment(
    service_id: str,
    date: str,
    start_time: str,
    client_name: str,
    client_email: str,
    client_phone: str
) -> str:
    """
    Create a new appointment with all the collected information.

    Args:
        service_id: The ID of the service (e.g., 'srv-001')
        date: Appointment date in YYYY-MM-DD format
        start_time: Start time in HH:MM format (24-hour)
        client_name: Client's full name
        client_email: Client's email address
        client_phone: Client's phone number
    """
    try:
        payload = {
            "service_id": service_id,
            "date": date,
            "start_time": start_time,
            "client": {
                "name": client_name,
                "email": client_email,
                "phone": client_phone
            }
        }

        response = requests.post(
            f"{config.MOCK_API_BASE_URL}/appointments",
            json=payload,
            timeout=5
        )

        data = response.json()

        if response.status_code == 201 and data.get("success"):
            appointment = data.get("appointment", {})
            return json.dumps({
                "success": True,
                "confirmation_number": appointment.get("confirmation_number"),
                "service_name": appointment.get("service_name"),
                "date": appointment.get("date"),
                "start_time": appointment.get("start_time"),
                "end_time": appointment.get("end_time"),
                "assigned_person": appointment.get("assigned_person"),
                "location": appointment.get("location")
            })
        else:
            error_data = {
                "success": False,
                "error": data.get("error", "Unknown error"),
                "alternatives": data.get("alternatives", [])
            }
            return json.dumps(error_data)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Error connecting to the booking system: {str(e)}"
        })


@tool
def validate_email(email: str) -> str:
    """
    Validate if an email address has correct format.

    Args:
        email: Email address to validate
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    is_valid = re.match(pattern, email) is not None

    if is_valid:
        return f"✅ Email '{email}' is valid."
    else:
        return f"❌ Email '{email}' is not valid. Please provide a valid email address (e.g., name@example.com)."


@tool
def validate_phone(phone: str) -> str:
    """
    Validate if a phone number has correct format (at least 7 digits).

    Args:
        phone: Phone number to validate
    """
    digits = re.sub(r'[^\d]', '', phone)
    is_valid = len(digits) >= 7

    if is_valid:
        return f"✅ Phone number '{phone}' is valid."
    else:
        return f"❌ Phone number '{phone}' is not valid. Please provide at least 7 digits."


# ============================================================================
# AGENT SETUP
# ============================================================================

# System prompt for the agent
SYSTEM_PROMPT = """You are a friendly and helpful appointment booking assistant. Your job is to help users book appointments by collecting the necessary information step by step.

**YOUR PERSONALITY:**
- Friendly, warm, and professional
- Use emojis moderately: 📅 ⏰ 👤 📍 📧 📞 ✅ ❌
- Keep responses short and clear
- Ask ONE question at a time

**CONVERSATION FLOW:**
1. Detect when user wants to book an appointment
2. Show available services using get_services tool
3. Once service is selected, show availability using get_availability tool
4. Collect date from the available slots
5. Collect time from the available slots
6. Collect client's full name
7. Collect and validate client's email using validate_email tool
8. Collect and validate client's phone using validate_phone tool
9. Show a complete summary with ALL details including assigned person and location
10. Ask for confirmation
11. Create appointment using create_appointment tool
12. Show confirmation number

**SUMMARY FORMAT (step 9):**
Show this before asking for confirmation:

✅ APPOINTMENT SUMMARY:

📋 Service: [service name]
📅 Date: [day, month date, year]
⏰ Time: [start time] - [end time]
👤 With: [assigned person name from response]
📍 Location: [location name and address from response]

CLIENT INFORMATION:
👤 Name: [client name]
📧 Email: [client email]
📞 Phone: [client phone]

**IMPORTANT RULES:**
- ALWAYS ask ONE question at a time
- ALWAYS validate email and phone before creating appointment
- ALWAYS show the complete summary before creating the appointment
- If slot is unavailable, immediately offer alternatives
- If validation fails, explain the correct format with an example
- Never show technical errors to the user
- Keep context of what information you've already collected
- Be patient and friendly even if user makes mistakes

**AVAILABLE TOOLS:**
- get_services: Get list of available services
- get_availability: Get available time slots for a service
- create_appointment: Create the appointment (use ONLY after showing summary and getting confirmation)
- validate_email: Validate email format
- validate_phone: Validate phone format

Start by greeting the user and asking how you can help them!
"""

# Initialize the LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    api_key=os.getenv("OPENAI_API_KEY")
)

# Create tools list
tools = [
    get_services,
    get_availability,
    create_appointment,
    validate_email,
    validate_phone
]

# Bind tools to the model
llm_with_tools = llm.bind_tools(tools)


# ============================================================================
# AGENT LOGIC
# ============================================================================

def should_continue(state: AgentState) -> str:
    """Determine if the agent should continue or end."""
    messages = state["messages"]
    last_message = messages[-1]

    # If the last message is from the AI and has tool calls, continue to tools
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"

    # Otherwise, end
    return "end"


def call_model(state: AgentState) -> dict:
    """Call the LLM with the current state."""
    messages = state["messages"]

    # Add system prompt as first message if not present
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}


# ============================================================================
# BUILD GRAPH
# ============================================================================

def create_agent_graph():
    """Create the LangGraph workflow for the appointment booking agent."""

    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )

    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")

    # Compile the graph
    return workflow.compile()


# ============================================================================
# MAIN CONVERSATION LOOP
# ============================================================================

def main():
    """Run the appointment booking agent."""
    print("=" * 60)
    print("🤖 APPOINTMENT BOOKING AGENT")
    print("=" * 60)
    print(f"📍 Location: {config.LOCATION['name']}")
    print(f"👤 Assigned Person: {config.ASSIGNED_PERSON['name']}")
    print(f"⏰ Hours: {config.OPERATING_HOURS['start_time']} - {config.OPERATING_HOURS['end_time']}")
    print("=" * 60)
    print("\nType 'quit' or 'exit' to end the conversation.\n")

    # Create the agent graph
    agent_graph = create_agent_graph()

    # Print initial greeting
    print("\n🤖 Agent: Hi! 👋 I'm here to help you book an appointment. How can I assist you today?\n")

    # Initialize conversation state with a greeting message
    conversation_state = {
        "messages": [AIMessage(content="Hi! 👋 I'm here to help you book an appointment. How can I assist you today?")],
        "context": {}
    }

    # Main conversation loop
    while True:
        try:
            # Get user input
            user_input = input("👤 You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                print("\n👋 Thank you for using our booking system. Goodbye!\n")
                break

            # Add user message to state
            conversation_state["messages"].append(HumanMessage(content=user_input))

            # Invoke the agent
            response = agent_graph.invoke(conversation_state)

            # Update state with response
            conversation_state["messages"] = response["messages"]

            # Print the last AI message
            last_message = response["messages"][-1]
            if isinstance(last_message, AIMessage) and last_message.content:
                print(f"\n🤖 Agent: {last_message.content}\n")

        except KeyboardInterrupt:
            print("\n\n👋 Conversation interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n⚠️  An error occurred: {str(e)}\n")
            print("Let's try again.\n")


if __name__ == "__main__":
    main()
