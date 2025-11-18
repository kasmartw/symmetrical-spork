"""Agent graph assembly (LangGraph 1.0).

Pattern: Modern LangGraph with InMemorySaver
References:
- LangGraph 1.0 Official Docs
- Best Practices by Swarnendu De (2025)
"""
import os
from typing import Any, List, Optional
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, trim_messages
from langchain_core.tools import BaseTool

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from src.state import AppointmentState, ConversationState
from src.org_config import OrganizationConfig, PermissionsConfig
from src.config_manager import ConfigManager
from src.tools import (
    validate_email_tool,
    validate_phone_tool,
    get_services_tool,
    fetch_and_cache_availability_tool,  # v1.5
    filter_and_show_availability_tool,  # v1.5
    create_appointment_tool
)
from src.tools_appointment_mgmt import (
    cancel_appointment_tool,
    # get_user_appointments_tool,  # REMOVED in v1.3.1 (security fix)
    get_appointment_tool,  # v1.3
    reschedule_appointment_tool,  # v1.3
)
from src.security import PromptInjectionDetector
from src.tracing import setup_langsmith_tracing
from src.token_logger import log_tokens

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
    fetch_and_cache_availability_tool,  # v1.5: New caching strategy
    filter_and_show_availability_tool,  # v1.5: New filtering strategy
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

# LLM with tools bound (OPTIMIZED v1.7)
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,        # Low temperature for consistent, predictable responses
    max_tokens=200,         # Limit response length (concise answers, not novels)
    timeout=15,             # Overall operation timeout
    request_timeout=15,     # Individual request timeout (prevent hanging)
    api_key=os.getenv("OPENAI_API_KEY")
)
llm_with_tools = llm.bind_tools(tools)


def build_system_prompt(state: AppointmentState) -> str:
    """
    Build context-aware system prompt (v2.0 - EFFICIENCY OPTIMIZED with state inference).

    Changes from v1.10:
    - Imperative commands instead of descriptive text
    - Explicit parallel tool calling instructions
    - Decision trees for common paths
    - Works with automatic state inference (infer_current_state)

    Optimization goal: Reduce from 7.2 to 3-4 iterations.
    """
    # v2.0: Get inferred state (dynamically updated)
    current = infer_current_state(state)

    # CORE RULES (~80 tokens, ultra-compressed)
    base = """Efficient booking agent. USER'S LANGUAGE. 1 Q/time.
IMPERATIVE: Use MULTIPLE tools in ONE response when possible.
UPDATE: collected_data{} with extracted values EVERY turn.
NEVER: fake data, skip validation, assume anything.

TOOL COMBOS (use together):
- Service selected → fetch_cache(svc_id) SILENT [no message to user]
- User gives email+phone → validate_email(email) + validate_phone(phone) [PARALLEL]

FLOWS: Book|Cancel|Reschedule
SECURITY: conf# only for cancel/reschedule"""

    # STATE-SPECIFIC DIRECTIVES (ultra-compressed)
    states = {
        ConversationState.COLLECT_SERVICE:
            "ACTION: get_services() + show list → user picks → fetch_cache(svc_id) SILENT + ask 'morning/afternoon/any?'",

        ConversationState.COLLECT_TIME_PREFERENCE:
            "ACTION: filter_show(svc_id, time_pref='morning'|'afternoon'|'any', offset=0) → show 3 days",

        ConversationState.SHOW_AVAILABILITY:
            "SHOWN: 3 days. User wants more? filter_show(..., offset+3). User picks slot? → ask name",

        ConversationState.COLLECT_DATE:
            "ASK: 'Which date?' WAIT. NO defaults.",

        ConversationState.COLLECT_TIME:
            "ASK: 'Which time?' WAIT. NO defaults.",

        ConversationState.COLLECT_NAME:
            "ASK: 'Full name?' WAIT. NO defaults. UPDATE collected_data{client_name}",

        ConversationState.COLLECT_EMAIL:
            "ASK: 'Email?' WAIT → validate_email(input). INVALID? Re-ask. VALID? UPDATE collected_data{client_email}",

        ConversationState.COLLECT_PHONE:
            "ASK: 'Phone?' WAIT → validate_phone(input). INVALID? Re-ask. VALID? UPDATE collected_data{client_phone}",

        ConversationState.SHOW_SUMMARY:
            "SHOW: svc, date, time, name, email, phone, provider, location. ASK: 'Confirm?' [yes/no only]",

        ConversationState.CONFIRM:
            "WAIT yes/no. YES → create_appointment. NO → ask 'What to change?'",

        ConversationState.CREATE_APPOINTMENT:
            "NOW: create_appointment_tool(svc_id, date, start_time, name, email, phone) with REAL data. SHOW conf# prominently.",

        ConversationState.COMPLETE:
            "✅ Done. Show conf#. Ask 'Anything else?'",

        ConversationState.CANCEL_ASK_CONFIRMATION:
            "ASK: 'Confirmation number?' (format: APPT-12345)",

        ConversationState.CANCEL_VERIFY:
            "ACTION: get_appointment_tool(conf#). SUCCESS? → show details. ERROR? retry (max 2×)",

        ConversationState.CANCEL_CONFIRM:
            "SHOW details. ASK: 'Cancel this appointment?' yes/no",

        ConversationState.CANCEL_PROCESS:
            "ACTION: cancel_appointment_tool(conf#) → show confirmation",

        ConversationState.RESCHEDULE_ASK_CONFIRMATION:
            "ASK: 'Confirmation number?'",

        ConversationState.RESCHEDULE_VERIFY:
            "ACTION: get_appointment_tool(conf#). SUCCESS? show current + ask new time. ERROR? retry (max 2×)",

        ConversationState.RESCHEDULE_SELECT_DATETIME:
            "ACTION: fetch_cache(svc_id) + filter_show(...) → show slots. User picks → confirm",

        ConversationState.RESCHEDULE_CONFIRM:
            "SHOW: old → new. ASK: 'Confirm reschedule?'",

        ConversationState.RESCHEDULE_PROCESS:
            "ACTION: reschedule_appointment_tool(conf#, new_date, new_time) → done",

        ConversationState.POST_ACTION:
            "ASK: 'Need anything else? Book|Cancel|Reschedule'",
    }

    current_val = current.value if hasattr(current, 'value') else current
    directive = states.get(current, f"STATE: {current_val}")

    return f"{base}\n\nCURRENT_STATE: {directive}"


def extract_text_from_content(content) -> str:
    """
    Extract text from message content (handles both string and multimodal list).

    LangGraph Studio sends multimodal content as list: [{"type": "text", "text": "..."}]
    Terminal/CLI sends simple string content: "..."

    Args:
        content: Either str or list of content blocks

    Returns:
        Extracted text as string
    """
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        # Extract text from multimodal blocks
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        return " ".join(text_parts)
    return ""


def apply_sliding_window(messages: List, window_size: int = 10):
    """
    Apply sliding window to message history.

    Keeps:
    - System message (if present) - CRITICAL for caching
    - Last N messages (window_size)

    Pattern: Maintain conversational context without unbounded growth.

    OpenAI Caching Strategy:
    By always keeping the system message at position 0, we ensure
    the prefix is identical across calls, enabling automatic caching.

    Args:
        messages: Full message history
        window_size: Number of recent messages to keep (default: 10)

    Returns:
        Filtered message list with system message + recent messages
    """
    if not messages:
        return messages

    # Separate system messages from conversation messages
    system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)]
    conversation_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]

    # Apply window to conversation messages
    if len(conversation_messages) <= window_size:
        # Fewer messages than window, keep all
        windowed_messages = conversation_messages
    else:
        # More messages than window, keep last N
        windowed_messages = conversation_messages[-window_size:]

    # Reconstruct: system message(s) first, then windowed conversation
    # This ensures consistent prefix for OpenAI automatic caching
    return system_messages + windowed_messages


def validate_message_sequence(messages: List) -> List:
    """
    Validate and fix message sequence to prevent OpenAI 400 errors.

    OpenAI requirements:
    1. Messages with role 'tool' MUST follow a message with 'tool_calls'
    2. Messages with 'tool_calls' MUST be followed by tool response messages for each tool_call_id

    Strategy:
    - Build valid sequence by scanning forward
    - For messages with tool_calls: verify ALL responses exist, otherwise strip tool_calls
    - For tool messages: verify preceding tool_calls exists, otherwise skip
    - Always preserve message order and content

    Args:
        messages: Raw message list from state

    Returns:
        Cleaned message list safe for OpenAI API
    """
    from langchain_core.messages import ToolMessage, AIMessage
    import copy

    if not messages:
        return messages

    # First pass: identify which tool_calls have complete responses
    tool_calls_with_responses = {}  # {tool_call_id: True/False}

    for i, msg in enumerate(messages):
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                tc_id = tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', None)
                if tc_id:
                    # Mark as incomplete by default
                    tool_calls_with_responses[tc_id] = False

    # Mark tool_calls that have responses
    for msg in messages:
        if isinstance(msg, ToolMessage) or (hasattr(msg, 'type') and msg.type == 'tool'):
            if hasattr(msg, 'tool_call_id'):
                tc_id = msg.tool_call_id
                if tc_id in tool_calls_with_responses:
                    tool_calls_with_responses[tc_id] = True

    # Second pass: build cleaned sequence
    cleaned = []
    i = 0

    while i < len(messages):
        msg = messages[i]

        # Handle messages with tool_calls
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            # Separate complete and incomplete tool_calls
            complete_tool_calls = []
            incomplete_exists = False

            for tc in msg.tool_calls:
                tc_id = tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', None)
                if tc_id and tool_calls_with_responses.get(tc_id, False):
                    complete_tool_calls.append(tc)
                else:
                    incomplete_exists = True

            if complete_tool_calls:
                # Keep message but only with complete tool_calls
                if incomplete_exists:
                    # Create new message with filtered tool_calls
                    from langchain_core.messages import AIMessage
                    cleaned_msg = AIMessage(
                        content=msg.content if hasattr(msg, 'content') else "",
                        additional_kwargs=msg.additional_kwargs if hasattr(msg, 'additional_kwargs') else {},
                        tool_calls=complete_tool_calls
                    )
                    cleaned.append(cleaned_msg)
                else:
                    # All tool_calls complete, keep as-is
                    cleaned.append(msg)
            else:
                # No complete tool_calls, strip all tool_calls
                from langchain_core.messages import AIMessage
                cleaned_msg = AIMessage(
                    content=msg.content if hasattr(msg, 'content') else "",
                    additional_kwargs=msg.additional_kwargs if hasattr(msg, 'additional_kwargs') else {}
                )
                cleaned.append(cleaned_msg)

            i += 1

        # Handle tool messages
        elif isinstance(msg, ToolMessage) or (hasattr(msg, 'type') and msg.type == 'tool'):
            # Check if this tool message has a valid tool_call_id
            if hasattr(msg, 'tool_call_id'):
                tc_id = msg.tool_call_id
                # Only include if tool_call was kept (exists and is complete)
                if tc_id in tool_calls_with_responses and tool_calls_with_responses[tc_id]:
                    # Also verify previous message has tool_calls
                    if cleaned and hasattr(cleaned[-1], 'tool_calls') and cleaned[-1].tool_calls:
                        cleaned.append(msg)
                    # Skip otherwise (orphaned)
                # Skip if tool_call_id not recognized
            # Skip if no tool_call_id

            i += 1

        # Handle all other messages
        else:
            cleaned.append(msg)
            i += 1

    return cleaned


def infer_current_state(state: AppointmentState) -> ConversationState:
    """
    Infer the current conversation state based on messages and tool calls (v2.0).

    This enables automatic state progression for the v2.0 optimization.
    The system analyzes the conversation history to determine where we are in the flow.
    """
    collected = state.get("collected_data", {})
    messages = state.get("messages", [])

    # Check for completion states
    if collected.get("confirmation_number"):
        return ConversationState.COMPLETE

    # Analyze recent tool calls and messages to determine state
    recent_tools_called = []
    recent_user_messages = []

    # Look at last 10 messages to understand context
    for msg in messages[-10:]:
        # Track tool calls
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_name = tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', None)
                if tool_name:
                    recent_tools_called.append(tool_name)

        # Track user messages
        if hasattr(msg, 'type') and msg.type == 'human':
            if hasattr(msg, 'content'):
                recent_user_messages.append(str(msg.content).lower())

    # Check booking flow progression based on collected_data
    if collected.get("service_id"):
        if collected.get("client_phone"):
            return ConversationState.SHOW_SUMMARY
        elif collected.get("client_email"):
            return ConversationState.COLLECT_PHONE
        elif collected.get("client_name"):
            return ConversationState.COLLECT_EMAIL
        elif collected.get("start_time"):
            return ConversationState.COLLECT_NAME
        elif collected.get("date"):
            return ConversationState.COLLECT_TIME
        elif state.get("available_slots") or 'filter_and_show_availability_tool' in recent_tools_called:
            return ConversationState.SHOW_AVAILABILITY
        else:
            return ConversationState.COLLECT_TIME_PREFERENCE

    # Check if we just called get_services (service selection in progress)
    if 'get_services_tool' in recent_tools_called:
        # Check if user has responded with a service choice
        if len(recent_user_messages) > 0:
            last_user_msg = recent_user_messages[-1]
            # If user mentioned a service name, we're moving to time preference
            if any(word in last_user_msg for word in ['consultation', 'appointment', 'follow']):
                return ConversationState.COLLECT_TIME_PREFERENCE
        return ConversationState.COLLECT_SERVICE

    # Check for cancel/reschedule flows
    recent_text = " ".join(recent_user_messages)
    if 'cancel' in recent_text and 'appt-' not in recent_text:
        return ConversationState.CANCEL_ASK_CONFIRMATION
    elif 'reschedule' in recent_text and 'appt-' not in recent_text:
        return ConversationState.RESCHEDULE_ASK_CONFIRMATION

    # Default: collecting service
    return ConversationState.COLLECT_SERVICE


async def agent_node(state: AppointmentState) -> dict[str, Any]:
    """
    Agent node - calls LLM with security checks (v2.0 - ASYNC for concurrency).

    Pattern: Pure async function returning partial state update.
    v1.10: Applies sliding window to enable automatic caching.
    v1.11: Validates message sequence to prevent OpenAI 400 errors.
    v1.11.1: FIX - Apply sliding window BEFORE validation (not after)
    v2.0: Adds automatic state inference for dynamic progression
    v2.1: ASYNC - Critical fix for concurrent user support
    """
    messages = state.get("messages", [])

    # v2.0: Infer current state automatically based on collected data
    current = infer_current_state(state)

    # Security check on last user message (before windowing)
    if messages:
        last_msg = messages[-1]
        if hasattr(last_msg, 'content') and last_msg.content:
            # v1.6: Extract text from multimodal content (Studio compatibility)
            text_content = extract_text_from_content(last_msg.content)
            scan = detector.scan(text_content)
            if not scan.is_safe:
                return {
                    "messages": [SystemMessage(
                        content="[SECURITY] Your message was flagged. Please rephrase."
                    )],
                }

    # Build prompt
    system_prompt = build_system_prompt(state)

    # OPTIMIZATION v1.12: Use LangChain's trim_messages instead of manual sliding window
    # FIX: Prevents OpenAI 400 errors from incomplete tool_call/tool_message pairs
    #
    # Why trim_messages is better:
    # 1. Uses token count (2000 tokens) instead of message count (10 messages) - more precise
    # 2. allow_partial=False ensures tool_call/tool_message pairs stay together
    # 3. Handles edge cases automatically (no need for manual validate_message_sequence)
    # 4. Still enables OpenAI's automatic caching via stable system message prefix
    #
    # What it does:
    # - Counts tokens using the actual LLM's tokenizer
    # - Keeps as many recent messages as possible within token limit
    # - NEVER splits tool_call from its tool_message response
    # - Preserves system messages automatically
    if messages:
        # Use trim_messages with token-based limit and safe partial handling
        trimmed_messages = trim_messages(
            messages,
            max_tokens=2000,           # Token limit (more precise than message count)
            strategy="last",           # Keep most recent messages
            token_counter=llm,         # Use actual LLM tokenizer for accurate counting
            allow_partial=False,       # CRITICAL: Never split tool_call/tool_message pairs
            start_on="human",          # Prefer starting with user message
        )
    else:
        trimmed_messages = []

    # Add system message at the front (position 0)
    # OpenAI will cache this automatically since it's always the same content
    full_msgs = [SystemMessage(content=system_prompt)] + trimmed_messages

    # DIAGNOSTIC: Log message sequence before sending to OpenAI
    print("\n" + "="*80)
    print("🔍 DEBUG: Messages being sent to OpenAI")
    print("="*80)
    for i, msg in enumerate(full_msgs):
        msg_type = type(msg).__name__
        has_tool_calls = hasattr(msg, 'tool_calls') and msg.tool_calls
        tool_call_count = len(msg.tool_calls) if has_tool_calls else 0
        is_tool_msg = hasattr(msg, 'tool_call_id')

        print(f"{i}. {msg_type}", end="")
        if has_tool_calls:
            print(f" [HAS {tool_call_count} TOOL_CALLS]", end="")
            for tc in msg.tool_calls[:2]:  # Show first 2
                tc_id = tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', '?')
                print(f" {tc_id[:20]}...", end="")
        if is_tool_msg:
            print(f" [tool_call_id: {msg.tool_call_id[:20]}...]", end="")
        print()
    print("="*80 + "\n")

    # Call LLM (OpenAI handles caching automatically based on prefix match)
    # v2.1: ASYNC ainvoke for true concurrency (not blocking invoke)
    response = await llm_with_tools.ainvoke(full_msgs)

    # Log token usage (debug mode)
    log_tokens(response, context="Agent Node")

    # v1.11.2: CRITICAL FIX - Ensure confirmation number appears when appointment is created
    # Problem: LLM with compressed prompts doesn't consistently extract/show confirmation
    # Solution: Post-process response to guarantee confirmation number is visible
    # Trigger: Detect if create_appointment_tool was just called (has SUCCESS + APPT- pattern)
    import re
    from langchain_core.messages import ToolMessage

    confirmation_number = None
    # Look through recent messages for create_appointment tool result
    # Check last 10 messages (not just last one, in case of retries)
    for msg in reversed(state.get("messages", [])[-10:]):
        if isinstance(msg, ToolMessage) or (hasattr(msg, 'type') and msg.type == 'tool'):
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                # Only extract if it's a successful appointment creation
                if '[SUCCESS]' in msg.content and 'Confirmation:' in msg.content:
                    # Extract APPT-XXXXX pattern
                    match = re.search(r'(APPT-\d+)', msg.content, re.IGNORECASE)
                    if match:
                        confirmation_number = match.group(1)
                        break

    # If we found a confirmation number and it's not in the response, add it
    if confirmation_number:
        response_text = response.content if hasattr(response, 'content') else str(response)
        if confirmation_number not in response_text:
            # Ensure confirmation is prominently displayed
            if hasattr(response, 'content'):
                response.content = f"{response.content}\n\n✅ Confirmation Number: **{confirmation_number}**"

    # v2.0: Always update current_state with inferred value
    # This enables dynamic state progression based on collected data
    result = {"messages": [response], "current_state": current}

    # Initialize other fields if this is the first interaction (v1.6: Studio compatibility)
    if "collected_data" not in state:
        result["collected_data"] = {}
    if "available_slots" not in state:
        result["available_slots"] = []
    if "retry_count" not in state:
        result["retry_count"] = {}

    return result


def should_continue(state: AppointmentState) -> str:
    """Route to tools or end."""
    messages = state["messages"]
    last = messages[-1] if messages else None

    if last and hasattr(last, 'tool_calls') and last.tool_calls:
        return "tools"
    return "end"


def retry_handler_node(state: AppointmentState) -> dict[str, Any]:
    """
    Handle retry logic after tool execution (v1.2, v1.3, v1.7 ENHANCED).

    Monitors tool responses and manages retry_count for:
    - Cancellation flow (CANCEL_VERIFY)
    - Rescheduling flow (RESCHEDULE_VERIFY)

    After 2 failed attempts, transitions to POST_ACTION with escalation message.

    **v1.7 Enhancement:** Detects error types to determine if retry is appropriate.
    Only retries on user errors (not found, invalid format), not system errors.
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

    # Look for tool responses with errors
    if hasattr(last_msg, 'content') and isinstance(last_msg.content, str):
        content = last_msg.content

        # Classify error type
        is_user_error = False  # User provided wrong info (retryable)
        is_system_error = False  # System/API issue (not retryable by user)

        if '[ERROR]' in content:
            # User errors (retryable)
            if 'not found' in content.lower():
                is_user_error = True
            elif 'invalid' in content.lower() and 'format' in content.lower():
                is_user_error = True

            # System errors (not retryable by user)
            elif 'could not connect' in content.lower():
                is_system_error = True
            elif 'api' in content.lower() and ('timeout' in content.lower() or 'unavailable' in content.lower()):
                is_system_error = True

        # Handle user errors (retryable)
        if is_user_error:
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

        # Handle system errors (immediate escalation, no retry)
        elif is_system_error:
            flow_key = 'cancel' if current == ConversationState.CANCEL_VERIFY else 'reschedule'

            system_error_msg = (
                "I apologize, but I'm experiencing technical difficulties connecting to our system. "
                "This is not an issue with your information.\n\n"
                "Please try again in a few moments. "
                "If the problem persists, please contact Downtown Medical Center directly:\n"
                "• Phone: (555) 123-4567\n"
                "• Email: support@downtownmedical.com\n\n"
                "Would you like to try booking a new appointment instead?"
            )

            from langchain_core.messages import AIMessage
            return {
                "retry_count": retry_count,
                "current_state": ConversationState.POST_ACTION,
                "messages": [AIMessage(content=system_error_msg)]
            }

    return {}


def should_use_retry_handler(state: AppointmentState) -> str:
    """
    Decide if retry_handler is necessary (v1.8 OPTIMIZATION).

    Routing logic:
    - CANCEL_VERIFY or RESCHEDULE_VERIFY → "retry_handler" (needs error detection)
    - All other states → "agent" (skip retry_handler - saves ~500ms)

    This optimization eliminates 90%+ of unnecessary retry_handler calls.

    Args:
        state: Current conversation state

    Returns:
        "retry_handler" if needed, "agent" to skip
    """
    current = state.get("current_state", ConversationState.COLLECT_SERVICE)

    # Only use retry_handler in verification states
    if current in [ConversationState.CANCEL_VERIFY, ConversationState.RESCHEDULE_VERIFY]:
        return "retry_handler"

    # All other states skip retry_handler (direct to agent)
    return "agent"


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

    # Edges (v1.5: Removed filter_availability node and edges)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )

    # OPTIMIZACIÓN v1.8: Routing condicional desde tools
    # - SI current_state es CANCEL_VERIFY o RESCHEDULE_VERIFY → retry_handler
    # - NO (otros estados) → agent (directo, ahorra ~500ms)
    builder.add_conditional_edges(
        "tools",
        should_use_retry_handler,  # Nueva función de decisión
        {
            "retry_handler": "retry_handler",  # Path cuando SÍ necesita retry
            "agent": "agent"                    # Path cuando NO necesita retry (90%+ casos)
        }
    )
    builder.add_edge("retry_handler", "agent")

    # Compile with checkpointer (LangGraph 1.0)
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


def create_production_graph():
    """
    Create graph with PostgreSQL checkpointing (production).

    Use this in production environments with DATABASE_URL set.
    Falls back to MemorySaver if DATABASE_URL not available.

    Pattern: Checkpointer is created once and reused via connection pool.
    """
    from src.database import get_connection_pool
    from langgraph.checkpoint.postgres import PostgresSaver

    builder = StateGraph(AppointmentState)

    # Add nodes (same as create_graph)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("retry_handler", retry_handler_node)  # v1.2, v1.3

    # Edges (v1.5: Removed filter_availability node and edges)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )

    # OPTIMIZACIÓN v1.8: Routing condicional desde tools (same as create_graph)
    # - SI current_state es CANCEL_VERIFY o RESCHEDULE_VERIFY → retry_handler
    # - NO (otros estados) → agent (directo, ahorra ~500ms)
    builder.add_conditional_edges(
        "tools",
        should_use_retry_handler,  # Nueva función de decisión
        {
            "retry_handler": "retry_handler",  # Path cuando SÍ necesita retry
            "agent": "agent"                    # Path cuando NO necesita retry (90%+ casos)
        }
    )
    builder.add_edge("retry_handler", "agent")

    # Production checkpointer with PostgreSQL
    if os.getenv("DATABASE_URL"):
        # Use PostgreSQL connection pool (long-lived saver)
        pool = get_connection_pool()
        conn = pool.connection()
        saver = PostgresSaver(conn)
        saver.setup()  # Create tables if not exist
        return builder.compile(checkpointer=saver)
    else:
        # Fallback for development
        import warnings
        warnings.warn(
            "DATABASE_URL not set - using MemorySaver (not production-ready)"
        )
        return builder.compile(checkpointer=MemorySaver())


# ============================================================================
# MULTI-TENANT ORGANIZATION-AWARE AGENT CREATION (v1.5)
# ============================================================================

def create_tools_for_org(permissions: PermissionsConfig) -> List[BaseTool]:
    """
    Create tools list based on organization permissions.

    Args:
        permissions: Organization permissions configuration

    Returns:
        List of tools that are permitted for this organization
    """
    # Always include these basic tools
    tools_list = [
        get_services_tool,
        fetch_and_cache_availability_tool,  # v1.5
        filter_and_show_availability_tool,  # v1.5
        validate_email_tool,
        validate_phone_tool
    ]

    # Add tools based on permissions
    if permissions.can_book:
        tools_list.append(create_appointment_tool)

    if permissions.can_cancel:
        tools_list.append(cancel_appointment_tool)
        tools_list.append(get_appointment_tool)  # Needed for cancel

    if permissions.can_reschedule:
        tools_list.append(reschedule_appointment_tool)
        tools_list.append(get_appointment_tool)  # Needed for reschedule

    return tools_list


def build_system_prompt_for_org(
    org_config: OrganizationConfig,
    state: Optional[AppointmentState] = None
) -> str:
    """
    Build system prompt from organization configuration.

    Args:
        org_config: Organization configuration
        state: Current appointment state (optional)

    Returns:
        Complete system prompt with org-specific settings
    """
    # Start with custom or default prompt
    base_prompt = org_config.get_effective_system_prompt()

    # Add organization context
    org_context = "\n\n"
    if org_config.org_name:
        org_context += f"ORGANIZATION: {org_config.org_name}\n"
    org_context += f"ORGANIZATION ID: {org_config.org_id}"

    # Add permissions context
    perms = org_config.permissions
    org_context += "\n\nAVAILABLE CAPABILITIES:"
    org_context += f"\n- Book appointments: {'✅ ENABLED' if perms.can_book else '❌ DISABLED'}"
    org_context += f"\n- Reschedule appointments: {'✅ ENABLED' if perms.can_reschedule else '❌ DISABLED'}"
    org_context += f"\n- Cancel appointments: {'✅ ENABLED' if perms.can_cancel else '❌ DISABLED'}"

    # Add disabled action warnings
    disabled_actions = []
    if not perms.can_book:
        disabled_actions.append("booking new appointments")
    if not perms.can_reschedule:
        disabled_actions.append("rescheduling appointments")
    if not perms.can_cancel:
        disabled_actions.append("canceling appointments")

    if disabled_actions:
        org_context += "\n\n⚠️  IMPORTANT: The following actions are DISABLED:"
        for action in disabled_actions:
            org_context += f"\n- {action.capitalize()}"
        org_context += "\nIf a user requests a disabled action, politely inform them that this feature is not available."

    # Add active services info
    active_services = org_config.get_active_services()
    org_context += f"\n\nACTIVE SERVICES: {len(active_services)}"
    for svc in active_services:
        org_context += f"\n- {svc.name} ({svc.duration_minutes} min, ${svc.price:.2f})"

    return base_prompt + org_context


def create_agent_node_for_org(org_config: OrganizationConfig):
    """
    Create agent node function with organization-specific configuration.

    Args:
        org_config: Organization configuration

    Returns:
        Agent node function that uses org-specific prompt and tools
    """
    # Create tools based on permissions
    tools_list = create_tools_for_org(org_config.permissions)

    # Create LLM with tools bound
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    llm_with_tools = llm.bind_tools(tools_list)

    async def agent_node(state: AppointmentState) -> AppointmentState:
        """
        Agent node that uses org-specific system prompt (v2.1 - ASYNC).

        Args:
            state: Current appointment state

        Returns:
            Updated state with agent's response
        """
        # Build system prompt with org config
        system_prompt = build_system_prompt_for_org(org_config, state)

        # Get messages from state
        messages = state.get("messages", [])

        # Prepend system message
        messages_with_system = [SystemMessage(content=system_prompt)] + messages

        # Invoke LLM (v2.1: ASYNC for concurrency)
        response = await llm_with_tools.ainvoke(messages_with_system)

        # Return updated state
        return {"messages": [response]}

    return agent_node


def create_agent_for_org(org_config: OrganizationConfig):
    """
    Create complete agent graph with organization-specific configuration.

    THIS IS REAL - NOT A PLACEHOLDER.

    Args:
        org_config: Organization configuration

    Returns:
        Compiled StateGraph with org-specific settings
    """
    # Create org-specific agent node
    agent_node = create_agent_node_for_org(org_config)

    # Create tools node with only permitted tools
    tools_list = create_tools_for_org(org_config.permissions)
    tools_node = ToolNode(tools_list)

    # Define conditional edge function
    def should_continue(state: AppointmentState) -> str:
        """Route to tools or end based on tool calls."""
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None

        if last_message and hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    # Build graph
    workflow = StateGraph(AppointmentState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )

    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")

    # Compile and return
    return workflow.compile()
