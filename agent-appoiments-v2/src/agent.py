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
from src.security import PromptInjectionDetector

# Load environment
load_dotenv()

# Security (use_ml_scanner=False to avoid false positives with Spanish)
# Pattern matching and base64 checks still active
detector = PromptInjectionDetector(threshold=0.9, use_ml_scanner=False)

# Tools list
tools = [
    get_services_tool,
    get_availability_tool,
    validate_email_tool,
    validate_phone_tool,
    create_appointment_tool,
]

# LLM with tools bound
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    api_key=os.getenv("OPENAI_API_KEY")
)
llm_with_tools = llm.bind_tools(tools)


def build_system_prompt(state: AppointmentState) -> str:
    """Build context-aware system prompt with complete booking flow."""
    current = state["current_state"]

    base = """You are a friendly appointment booking assistant for Downtown Medical Center.

CONVERSATION FLOW (follow this exact order):
1. GREETING - Welcome user and call get_services_tool to show available services
2. COLLECT_SERVICE - User selects service, then call get_availability_tool
3. COLLECT_DATE - User chooses a date from available slots
4. COLLECT_TIME - User chooses a time from available slots
5. COLLECT_NAME - Ask for user's full name
6. COLLECT_EMAIL - Ask for email and call validate_email_tool
7. COLLECT_PHONE - Ask for phone and call validate_phone_tool
8. SHOW_SUMMARY - Present complete summary for confirmation
9. CONFIRM - Wait for user to confirm (yes/no)
10. CREATE_APPOINTMENT - Call create_appointment_tool with all data
11. COMPLETE - Show confirmation number and thank user

RULES:
✅ Ask ONE question at a time
✅ ALWAYS use get_services_tool first to show services
✅ ALWAYS use get_availability_tool after service selection
✅ ALWAYS validate email with validate_email_tool
✅ ALWAYS validate phone with validate_phone_tool
✅ ALWAYS show summary before confirmation
✅ Only create appointment after user confirms "yes"
✅ Be friendly and professional

AVAILABLE TOOLS:
- get_services_tool() - Get list of services (use at start)
- get_availability_tool(service_id, date_from) - Get time slots
- validate_email_tool(email) - Validate email format
- validate_phone_tool(phone) - Validate phone number
- create_appointment_tool(service_id, date, start_time, name, email, phone)
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
    }

    instruction = state_prompts.get(current, f"\nCURRENT STATE: {current.value}")
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
