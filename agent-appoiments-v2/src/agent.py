"""Agent graph assembly (LangGraph 1.0).

Pattern: Modern LangGraph with InMemorySaver
References:
- LangGraph 1.0 Official Docs
- Best Practices by Swarnendu De (2025)
"""
import os
from typing import Any
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from src.state import AppointmentState, ConversationState
from src.tools import (
    validate_email_tool,
    validate_phone_tool,
    get_services_tool,
    get_availability_tool,
    create_appointment_tool
)
from src.tools_cancellation import (
    cancel_appointment_tool,
    get_user_appointments_tool
)
from src.security import PromptInjectionDetector
from src.tracing import setup_langsmith_tracing

# Load environment
load_dotenv()

# Setup LangSmith tracing (v1.2)
setup_langsmith_tracing()

# Security (use_ml_scanner=False to avoid false positives with Spanish)
# Pattern matching and base64 checks still active
detector = PromptInjectionDetector(threshold=0.9, use_ml_scanner=False)

# Tools list
tools = [
    # Booking tools
    get_services_tool,
    get_availability_tool,
    validate_email_tool,
    validate_phone_tool,
    create_appointment_tool,
    # Cancellation tools (v1.2)
    cancel_appointment_tool,
    get_user_appointments_tool,
]

# LLM with tools bound
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    api_key=os.getenv("OPENAI_API_KEY")
)
llm_with_tools = llm.bind_tools(tools)


def build_system_prompt(state: AppointmentState) -> str:
    """Build context-aware system prompt."""
    current = state["current_state"]

    base = """You are a friendly assistant for booking and cancelling appointments at Downtown Medical Center.

IMPORTANT: Respond in the SAME LANGUAGE the user speaks to you (Spanish, English, etc).

AVAILABLE FLOWS:
1. BOOKING - Schedule new appointment (11 steps)
2. CANCELLATION - Cancel existing appointment (4 steps)
3. POST-ACTION - Options menu after completing action

RULES:
✅ Ask ONE thing at a time
✅ Use available tools
✅ Be friendly and professional
✅ Validate data before confirming

TOOLS:
- get_services_tool() - List services
- get_availability_tool(service_id, date_from) - View schedules
- validate_email_tool(email) - Validate email
- validate_phone_tool(phone) - Validate phone
- create_appointment_tool(...) - Create appointment
- cancel_appointment_tool(confirmation_number) - Cancel appointment
- get_user_appointments_tool(email) - Find appointments by email
"""

    state_prompts = {
        ConversationState.COLLECT_SERVICE: (
            "\nCURRENT STATE: COLLECT_SERVICE\n"
            "ACTION: If not done yet, call get_services_tool() to show available services.\n"
            "Then ask user which service they want."
        ),
        ConversationState.SHOW_AVAILABILITY: (
            "\nCURRENT STATE: SHOW_AVAILABILITY\n"
            "ACTION: Call get_availability_tool with the selected service_id.\n"
            "Show user the available time slots."
        ),
        ConversationState.COLLECT_DATE: (
            "\nCURRENT STATE: COLLECT_DATE\n"
            "ACTION: Ask user to choose a date from the available slots shown."
        ),
        ConversationState.COLLECT_TIME: (
            "\nCURRENT STATE: COLLECT_TIME\n"
            "ACTION: Ask user to choose a time from the available slots for their selected date."
        ),
        ConversationState.COLLECT_NAME: (
            "\nCURRENT STATE: COLLECT_NAME\n"
            "ACTION: Ask for user's full name."
        ),
        ConversationState.COLLECT_EMAIL: (
            "\nCURRENT STATE: COLLECT_EMAIL\n"
            "ACTION: Ask for email, then MUST call validate_email_tool(email) before proceeding."
        ),
        ConversationState.COLLECT_PHONE: (
            "\nCURRENT STATE: COLLECT_PHONE\n"
            "ACTION: Ask for phone, then MUST call validate_phone_tool(phone) before proceeding."
        ),
        ConversationState.SHOW_SUMMARY: (
            "\nCURRENT STATE: SHOW_SUMMARY\n"
            "ACTION: Show complete summary with:\n"
            "- Service name\n"
            "- Date and time\n"
            "- Client name, email, phone\n"
            "- Provider and location\n"
            "Ask user to confirm (yes/no)."
        ),
        ConversationState.CONFIRM: (
            "\nCURRENT STATE: CONFIRM\n"
            "ACTION: Wait for user confirmation (yes/no).\n"
            "If yes → proceed to create\n"
            "If no → ask what to change"
        ),
        ConversationState.CREATE_APPOINTMENT: (
            "\nCURRENT STATE: CREATE_APPOINTMENT\n"
            "ACTION: Call create_appointment_tool with all collected data:\n"
            "- service_id\n"
            "- date (YYYY-MM-DD)\n"
            "- start_time (HH:MM)\n"
            "- client_name\n"
            "- client_email\n"
            "- client_phone"
        ),
        ConversationState.COMPLETE: (
            "\nCURRENT STATE: COMPLETE\n"
            "ACTION: Show confirmation number and thank user.\n"
            "Wish them a great day!"
        ),

        # Cancellation states (v1.2)
        ConversationState.CANCEL_ASK_CONFIRMATION: (
            "\nCURRENT STATE: CANCEL_ASK_CONFIRMATION\n"
            "ACTION: Ask user for their confirmation number (e.g., APPT-1234)"
        ),
        ConversationState.CANCEL_VERIFY: (
            "\nCURRENT STATE: CANCEL_VERIFY\n"
            "ACTION: Call cancel_appointment_tool(confirmation_number) to verify appointment"
        ),
        ConversationState.CANCEL_CONFIRM: (
            "\nCURRENT STATE: CANCEL_CONFIRM\n"
            "ACTION: Ask 'Are you sure you want to cancel this appointment?'"
        ),
        ConversationState.CANCEL_PROCESS: (
            "\nCURRENT STATE: CANCEL_PROCESS\n"
            "ACTION: Execute cancellation with cancel_appointment_tool"
        ),
        ConversationState.POST_ACTION: (
            "\nCURRENT STATE: POST_ACTION\n"
            "ACTION: Ask 'Need anything else? I can help you book an appointment or cancel another.'"
        ),
    }

    # Handle both enum and string values
    current_value = current.value if hasattr(current, 'value') else current
    instruction = state_prompts.get(current, f"\nCURRENT STATE: {current_value}")

    return base + instruction


def agent_node(state: AppointmentState) -> dict[str, Any]:
    """
    Agent node - calls LLM with security checks.

    Pattern: Pure function returning partial state update.
    """
    messages = state["messages"]
    current = state["current_state"]

    # Security check on last user message
    if messages:
        last_msg = messages[-1]
        if hasattr(last_msg, 'content') and last_msg.content:
            scan = detector.scan(last_msg.content)
            if not scan.is_safe:
                return {
                    "messages": [SystemMessage(
                        content="[SECURITY] Your message was flagged. Please rephrase."
                    )],
                }

    # Build prompt
    system_prompt = build_system_prompt(state)
    full_msgs = [SystemMessage(content=system_prompt)] + list(messages)

    # Call LLM
    response = llm_with_tools.invoke(full_msgs)

    return {"messages": [response]}


def should_continue(state: AppointmentState) -> str:
    """Route to tools or end."""
    messages = state["messages"]
    last = messages[-1] if messages else None

    if last and hasattr(last, 'tool_calls') and last.tool_calls:
        return "tools"
    return "end"


def create_graph():
    """
    Create appointment booking graph (LangGraph 1.0).

    Pattern:
    - StateGraph with TypedDict state
    - MemorySaver for checkpointing (InMemorySaver deprecated)
    - START/END constants
    - ToolNode for tool execution

    Returns:
        Compiled graph with checkpointer
    """
    builder = StateGraph(AppointmentState)

    # Add nodes
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools))

    # Edges
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )
    builder.add_edge("tools", "agent")

    # Compile with checkpointer (LangGraph 1.0)
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


def create_production_graph():
    """
    Create graph with PostgreSQL checkpointing (production).

    Use this in production environments with DATABASE_URL set.
    Falls back to MemorySaver if DATABASE_URL not available.
    """
    from src.database import get_postgres_saver

    builder = StateGraph(AppointmentState)

    # Add nodes (same as create_graph)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools))

    # Edges
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )
    builder.add_edge("tools", "agent")

    # Production checkpointer
    if os.getenv("DATABASE_URL"):
        with get_postgres_saver() as saver:
            saver.setup()  # Create tables
            return builder.compile(checkpointer=saver)
    else:
        # Fallback for development
        return builder.compile(checkpointer=MemorySaver())
