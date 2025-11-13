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
from src.tools_appointment_mgmt import (
    cancel_appointment_tool,
    # get_user_appointments_tool,  # REMOVED in v1.3.1 (security fix)
    get_appointment_tool,  # v1.3
    reschedule_appointment_tool,  # v1.3
)
from src.availability import TimeFilter, TimeOfDay  # v1.4
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
    # SECURITY FIX (v1.3.1): Removed get_user_appointments_tool
    # Reason: Prevents unauthorized access via email lookup in rescheduling flow
    # Users MUST use confirmation number for cancellation/rescheduling
    # get_user_appointments_tool,  # REMOVED
    # Rescheduling tools (v1.3)
    get_appointment_tool,
    reschedule_appointment_tool,
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

    base = """You are a friendly assistant for booking, cancelling, and rescheduling appointments at Downtown Medical Center.

IMPORTANT: Respond in the SAME LANGUAGE the user speaks to you (Spanish, English, etc).

AVAILABLE FLOWS:
1. BOOKING - Schedule new appointment (11 steps)
2. CANCELLATION - Cancel existing appointment (4 steps)
3. RESCHEDULING - Change appointment date/time (5 steps)
4. POST-ACTION - Options menu after completing action

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
- get_appointment_tool(confirmation_number) - Get appointment details (v1.3)
- reschedule_appointment_tool(confirmation_number, new_date, new_start_time) - Reschedule (v1.3)

SECURITY POLICY (v1.3.1):
🔒 Cancellation & Rescheduling require CONFIRMATION NUMBER only
🔒 NO email lookup allowed (prevents unauthorized access)
🔒 Users must have their confirmation number from booking confirmation
"""

    state_prompts = {
        ConversationState.COLLECT_SERVICE: (
            "\nCURRENT STATE: COLLECT_SERVICE\n"
            "ACTION: If services not yet shown, call get_services_tool() to show available services.\n"
            "Then ask user which service they want.\n"
            "Once user selects a service:\n"
            "1. Store service_id and service_name in collected_data\n"
            "2. Immediately ask in THE SAME RESPONSE: 'Great! Do you prefer morning appointments (before 12:00 PM) or afternoon appointments (after 12:00 PM)? Or any time works for you?'\n"
            "Wait for their time preference response before proceeding."
        ),
        ConversationState.COLLECT_TIME_PREFERENCE: (
            "\nCURRENT STATE: COLLECT_TIME_PREFERENCE\n"
            "ACTION: The user just responded with their time preference.\n"
            "Understand responses like:\n"
            "- 'morning', 'mañana', 'temprano', 'antes de mediodía' → store as 'morning'\n"
            "- 'afternoon', 'tarde', 'después de mediodía' → store as 'afternoon'\n"
            "- 'any', 'cualquiera', 'me da igual', 'any time' → store as 'any'\n"
            "Store in collected_data['time_preference'].\n"
            "Then call get_availability_tool with the service_id to show available slots."
        ),
        ConversationState.SHOW_AVAILABILITY: (
            "\nCURRENT STATE: SHOW_AVAILABILITY\n"
            "ACTION: Call get_availability_tool with the selected service_id if not already called.\n"
            "The system will automatically filter results based on time_preference.\n"
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

        # Cancellation states (v1.2, v1.3.1 security fix)
        ConversationState.CANCEL_ASK_CONFIRMATION: (
            "\nCURRENT STATE: CANCEL_ASK_CONFIRMATION\n"
            "ACTION: Ask user for their confirmation number ONLY (e.g., APPT-1234).\n"
            "SECURITY: DO NOT offer email lookup. Confirmation number is required."
        ),
        ConversationState.CANCEL_VERIFY: (
            "\nCURRENT STATE: CANCEL_VERIFY\n"
            "ACTION: Call cancel_appointment_tool(confirmation_number) to verify appointment.\n"
            "If [ERROR] appears: Ask user to verify the number and try again (system will auto-escalate after 2 failures).\n"
            "SECURITY: DO NOT use email or any other method. ONLY confirmation number.\n"
            "DO NOT manually track retry_count - the system handles this automatically."
        ),
        ConversationState.CANCEL_CONFIRM: (
            "\nCURRENT STATE: CANCEL_CONFIRM\n"
            "ACTION: Ask 'Are you sure you want to cancel this appointment?'"
        ),
        ConversationState.CANCEL_PROCESS: (
            "\nCURRENT STATE: CANCEL_PROCESS\n"
            "ACTION: Execute cancellation with cancel_appointment_tool"
        ),

        # Rescheduling states (v1.3)
        ConversationState.RESCHEDULE_ASK_CONFIRMATION: (
            "\nCURRENT STATE: RESCHEDULE_ASK_CONFIRMATION\n"
            "ACTION: Ask user for their confirmation number ONLY (e.g., APPT-1234).\n"
            "DO NOT ask for email, phone, or any other information.\n"
            "Just the confirmation number."
        ),
        ConversationState.RESCHEDULE_VERIFY: (
            "\nCURRENT STATE: RESCHEDULE_VERIFY\n"
            "ACTION: Call get_appointment_tool(confirmation_number) using the number provided.\n"
            "If [APPOINTMENT] appears: Show current details (service, date, time).\n"
            "If [ERROR] appears: Ask user to verify the number and try again (system will auto-escalate after 2 failures).\n"
            "DO NOT use email or any other method to find appointments. ONLY confirmation number.\n"
            "DO NOT manually track retry_count - the system handles this automatically."
        ),
        ConversationState.RESCHEDULE_SELECT_DATETIME: (
            "\nCURRENT STATE: RESCHEDULE_SELECT_DATETIME\n"
            "ACTION: Ask user for NEW date and time they prefer.\n"
            "Call get_availability_tool with the service_id from verified appointment.\n"
            "Show available slots and let user choose.\n"
            "DO NOT ask for email, phone, name or any client information - this is already saved."
        ),
        ConversationState.RESCHEDULE_CONFIRM: (
            "\nCURRENT STATE: RESCHEDULE_CONFIRM\n"
            "ACTION: Show summary of change:\n"
            "- Current appointment: [old date] at [old time]\n"
            "- New appointment: [new date] at [new time]\n"
            "- Service: [service name]\n"
            "Ask 'Do you confirm this change?' (Yes/No)\n"
            "DO NOT ask for any client information - it's already in the system."
        ),
        ConversationState.RESCHEDULE_PROCESS: (
            "\nCURRENT STATE: RESCHEDULE_PROCESS\n"
            "ACTION: Call reschedule_appointment_tool(confirmation_number, new_date, new_start_time).\n"
            "Use the confirmation number from RESCHEDULE_VERIFY and the new date/time from RESCHEDULE_SELECT_DATETIME.\n"
            "Client information (name, email, phone) is automatically preserved - DO NOT ask for it."
        ),

        ConversationState.POST_ACTION: (
            "\nCURRENT STATE: POST_ACTION\n"
            "ACTION: Ask 'Need anything else? I can help you:\n"
            "- Book an appointment\n"
            "- Cancel an appointment\n"
            "- Reschedule an appointment'"
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


def parse_slots_from_response(response: str) -> list:
    """
    Parse availability slots from tool response string (v1.4).

    Args:
        response: Tool response containing [AVAILABILITY] formatted slots

    Returns:
        List of slot dicts: [{"date": "...", "day": "...", "start_time": "...", "end_time": "..."}]
    """
    import re

    slots = []

    # Pattern: "1. Monday, 2025-11-13 at 09:00 - 09:30"
    pattern = r'(\d+)\.\s+(\w+),\s+([\d-]+)\s+at\s+([\d:]+)\s+-\s+([\d:]+)'
    matches = re.findall(pattern, response)

    for match in matches:
        _, day, date, start_time, end_time = match
        slots.append({
            "date": date,
            "day": day,
            "start_time": start_time,
            "end_time": end_time
        })

    return slots


def should_continue(state: AppointmentState) -> str:
    """Route to tools or end."""
    messages = state["messages"]
    last = messages[-1] if messages else None

    if last and hasattr(last, 'tool_calls') and last.tool_calls:
        return "tools"
    return "end"


def retry_handler_node(state: AppointmentState) -> dict[str, Any]:
    """
    Handle retry logic after tool execution (v1.2, v1.3).

    Monitors tool responses and manages retry_count for:
    - Cancellation flow (CANCEL_VERIFY)
    - Rescheduling flow (RESCHEDULE_VERIFY)

    After 2 failed attempts, transitions to POST_ACTION with escalation message.
    """
    messages = state["messages"]
    current = state["current_state"]
    retry_count = state.get("retry_count", {}).copy()

    # Only process in verification states
    if current not in [ConversationState.CANCEL_VERIFY, ConversationState.RESCHEDULE_VERIFY]:
        return {}

    # Check last message for tool response
    if not messages:
        return {}

    last_msg = messages[-1]

    # Look for tool responses with [ERROR]
    if hasattr(last_msg, 'content') and isinstance(last_msg.content, str):
        content = last_msg.content

        # Detect error in tool response
        if '[ERROR]' in content and 'not found' in content.lower():
            # Determine flow type
            flow_key = 'cancel' if current == ConversationState.CANCEL_VERIFY else 'reschedule'

            # Initialize retry count if not exists
            if flow_key not in retry_count:
                retry_count[flow_key] = 0

            # Increment retry count
            retry_count[flow_key] += 1

            # Check if we've exceeded max retries (2)
            if retry_count[flow_key] >= 2:
                # Escalate to POST_ACTION with helpful guidance
                if flow_key == 'reschedule':
                    escalation_msg = (
                        "I apologize, I cannot find your appointment after multiple attempts. "
                        "To reschedule your appointment, you'll need your confirmation number. "
                        "You can find it in:\n"
                        "• Your booking confirmation email\n"
                        "• Any text messages from us\n\n"
                        "If you can't locate it, please contact Downtown Medical Center directly "
                        "or speak with our support team for assistance.\n\n"
                        "Would you like to book a new appointment instead?"
                    )
                else:  # cancellation
                    escalation_msg = (
                        "I apologize, I cannot find your appointment after multiple attempts. "
                        "To cancel your appointment, you'll need your confirmation number. "
                        "You can find it in:\n"
                        "• Your booking confirmation email\n"
                        "• Any text messages from us\n\n"
                        "If you can't locate it, please contact Downtown Medical Center directly "
                        "or speak with our support team for assistance.\n\n"
                        "Would you like to book a new appointment instead?"
                    )

                from langchain_core.messages import AIMessage
                return {
                    "retry_count": retry_count,
                    "current_state": ConversationState.POST_ACTION,
                    "messages": [AIMessage(content=escalation_msg)]
                }
            else:
                # Still have retries left
                return {"retry_count": retry_count}

    return {}


def filter_availability_node(state: AppointmentState) -> dict[str, Any]:
    """
    Filter availability results based on time preference (v1.4).

    Runs after tools node when:
    - current_state is SHOW_AVAILABILITY
    - time_preference is set
    - last tool call was get_availability_tool

    Returns:
        Partial state update with filtered availability message
    """
    messages = state["messages"]
    preference = state.get("collected_data", {}).get("time_preference")

    # Only filter if we have preference and preference is not 'any'
    if not preference or preference == "any":
        return {}

    if not messages:
        return {}

    last_msg = messages[-1]

    # Check if this is a tool response from get_availability_tool
    if not (hasattr(last_msg, 'content') and
            isinstance(last_msg.content, str) and
            '[AVAILABILITY]' in last_msg.content):
        return {}

    # Parse slots from tool response
    slots = parse_slots_from_response(last_msg.content)

    if not slots:
        return {}

    # Apply time filter
    time_filter = TimeFilter()
    preference_enum = TimeOfDay.MORNING if preference == "morning" else TimeOfDay.AFTERNOON

    filtered_slots = time_filter.filter_by_time_of_day(slots, preference_enum)
    filtered_slots = time_filter.limit_to_next_days(filtered_slots, max_days=3)

    # Handle no results
    from langchain_core.messages import ToolMessage

    if not filtered_slots:
        no_results_msg = (
            f"[INFO] No {preference} slots available for this service. "
            f"Would you like to see all available times instead? "
            f"(You can also change your time preference)"
        )

        # Get tool_call_id from last message if it's a ToolMessage
        tool_call_id = getattr(last_msg, 'tool_call_id', 'filter_availability')

        return {
            "messages": [ToolMessage(
                content=no_results_msg,
                tool_call_id=tool_call_id
            )]
        }

    # Format filtered results
    formatted = time_filter.format_slots_grouped(filtered_slots)

    # Add context about filtering
    filtered_response = (
        f"[AVAILABILITY] Showing {preference} appointments:\n\n"
        f"{formatted}\n\n"
        f"(Filtered for {preference} times. Want to see all times? Just ask!)"
    )

    # Get tool_call_id from last message
    tool_call_id = getattr(last_msg, 'tool_call_id', 'filter_availability')

    # Replace last message with filtered version
    return {
        "messages": [ToolMessage(
            content=filtered_response,
            tool_call_id=tool_call_id
        )]
    }


def should_filter_availability(state: AppointmentState) -> str:
    """
    Route to filter availability or skip (v1.4).

    Returns:
        "filter" if we should apply time filtering, "skip" otherwise
    """
    current = state["current_state"]
    preference = state.get("collected_data", {}).get("time_preference")
    messages = state["messages"]

    # Only filter if showing availability with preference set (not 'any')
    if (current == ConversationState.SHOW_AVAILABILITY and
        preference and preference != "any" and
        messages and len(messages) > 0):

        last_msg = messages[-1]
        # Check if last message contains availability data
        if (hasattr(last_msg, 'content') and
            isinstance(last_msg.content, str) and
            '[AVAILABILITY]' in last_msg.content):
            return "filter"

    return "skip"


def create_graph():
    """
    Create appointment booking graph (LangGraph 1.0).

    Pattern:
    - StateGraph with TypedDict state
    - MemorySaver for checkpointing (InMemorySaver deprecated)
    - START/END constants
    - ToolNode for tool execution
    - retry_handler for automatic retry logic (v1.2, v1.3)

    Returns:
        Compiled graph with checkpointer
    """
    builder = StateGraph(AppointmentState)

    # Add nodes
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("retry_handler", retry_handler_node)  # v1.2, v1.3
    builder.add_node("filter_availability", filter_availability_node)  # v1.4

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
    # After tools, check for retry logic
    builder.add_edge("tools", "retry_handler")

    # After retry_handler, conditionally filter availability (v1.4)
    builder.add_conditional_edges(
        "retry_handler",
        should_filter_availability,
        {
            "filter": "filter_availability",
            "skip": "agent",
        }
    )

    # After filtering, return to agent
    builder.add_edge("filter_availability", "agent")

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
    builder.add_node("retry_handler", retry_handler_node)  # v1.2, v1.3
    builder.add_node("filter_availability", filter_availability_node)  # v1.4

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
    # After tools, check for retry logic
    builder.add_edge("tools", "retry_handler")

    # After retry_handler, conditionally filter availability (v1.4)
    builder.add_conditional_edges(
        "retry_handler",
        should_filter_availability,
        {
            "filter": "filter_availability",
            "skip": "agent",
        }
    )

    # After filtering, return to agent
    builder.add_edge("filter_availability", "agent")

    # Production checkpointer
    if os.getenv("DATABASE_URL"):
        with get_postgres_saver() as saver:
            saver.setup()  # Create tables
            return builder.compile(checkpointer=saver)
    else:
        # Fallback for development
        return builder.compile(checkpointer=MemorySaver())
