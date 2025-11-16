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
from langchain_core.messages import SystemMessage
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
    Build context-aware system prompt (v1.10 - Optimized for automatic caching).

    OpenAI Automatic Caching Strategy:
    - OpenAI caches the longest common prefix of your messages array
    - No configuration needed - it's automatic and transparent
    - Our job: Make the system prompt IDENTICAL across calls within same state

    What we do:
    1. System prompt depends ONLY on current_state (not messages, time, etc.)
    2. Messages are handled separately via sliding window
    3. Each conversation state has a deterministic, stable prompt
    4. OpenAI sees identical prefix → automatic cache hit

    Cache effectiveness:
    - Same conversation state = cache hit (fast)
    - Different conversation state = cache miss (expected)
    - Typical conversation: 70-80% cache hit rate

    v1.9: ~154 tokens (down from 1,100)
    v1.10: ~90 tokens (target) + automatic caching
    """
    current = state.get("current_state", ConversationState.COLLECT_SERVICE)

    # ULTRA-COMPRESSED BASE (~60 tokens, down from 174)
    # Strategy: Remove ALL redundancy, use extreme abbreviations, single-line format
    base = """Friendly appt assistant. User's lang. 1 Q/time.
FLOWS: Book|Cancel|Reschedule
TOOLS: get_services→list, fetch_cache(svc)→30d silent, filter_show(svc,time,off)→3d, validate_email/phone, create(…), cancel(conf#), get_appt(conf#), reschedule(conf#,dt,tm)
SEC: conf# only"""

    # ULTRA-CONDENSED STATES (15-30 tokens each, down from 30-50)
    states = {
        ConversationState.COLLECT_SERVICE:
            "get_services→pick→fetch_cache(svc_id) silent→ask time pref",

        ConversationState.COLLECT_TIME_PREFERENCE:
            "Parse morn|aft|any→filter_show(svc,pref,0)",

        ConversationState.SHOW_AVAILABILITY:
            "3d shown. more→filter_show(…,off+3)",

        ConversationState.COLLECT_DATE:
            "Ask date from slots",

        ConversationState.COLLECT_TIME:
            "Ask time from date",

        ConversationState.COLLECT_NAME:
            "Ask name",

        ConversationState.COLLECT_EMAIL:
            "Ask email→validate",

        ConversationState.COLLECT_PHONE:
            "Ask phone→validate",

        ConversationState.SHOW_SUMMARY:
            "Show svc,dt,tm,name,email,phone,provider,loc→confirm?",

        ConversationState.CONFIRM:
            "Wait y/n. y→create. n→ask change",

        ConversationState.CREATE_APPOINTMENT:
            "create(svc_id,dt,tm,name,email,phone)",

        ConversationState.COMPLETE:
            "Show conf#, thank",

        ConversationState.CANCEL_ASK_CONFIRMATION:
            "Ask conf# only",

        ConversationState.CANCEL_VERIFY:
            "cancel(conf#). ERR→verify (2x→escalate)",

        ConversationState.CANCEL_CONFIRM:
            "Sure cancel?",

        ConversationState.CANCEL_PROCESS:
            "cancel(conf#)",

        ConversationState.RESCHEDULE_ASK_CONFIRMATION:
            "Ask conf# only",

        ConversationState.RESCHEDULE_VERIFY:
            "get_appt(conf#)→show. ERR→verify (2x→escalate)",

        ConversationState.RESCHEDULE_SELECT_DATETIME:
            "Ask new dt/tm. get_avail(svc). Show. Keep client info",

        ConversationState.RESCHEDULE_CONFIRM:
            "Old→New. Confirm. Keep info",

        ConversationState.RESCHEDULE_PROCESS:
            "reschedule(conf#,dt,tm). Info preserved",

        ConversationState.POST_ACTION:
            "Else? Book|Cancel|Reschedule",
    }

    current_val = current.value if hasattr(current, 'value') else current
    inst = states.get(current, f"S:{current_val}")

    return f"{base}\nNOW: {inst}"


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


def agent_node(state: AppointmentState) -> dict[str, Any]:
    """
    Agent node - calls LLM with security checks.

    Pattern: Pure function returning partial state update.
    v1.10: Applies sliding window to enable automatic caching.
    """
    messages = state.get("messages", [])
    # Handle initialization from Studio (v1.6: Fix for Studio compatibility)
    current = state.get("current_state", ConversationState.COLLECT_SERVICE)

    # Security check on last user message
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

    # OPTIMIZATION v1.10: Apply sliding window BEFORE adding system message
    # This keeps context bounded while maintaining conversation coherence
    # CRITICAL: Window ensures we don't send too many messages, but we still
    # need to add the system prompt fresh each time (OpenAI caches it automatically)
    windowed_messages = apply_sliding_window(messages, window_size=10)

    # Add system message at the front (position 0)
    # OpenAI will cache this automatically since it's always the same content
    full_msgs = [SystemMessage(content=system_prompt)] + windowed_messages

    # Call LLM (OpenAI handles caching automatically based on prefix match)
    response = llm_with_tools.invoke(full_msgs)

    # Log token usage (debug mode)
    log_tokens(response, context="Agent Node")

    # Initialize state if this is the first interaction (v1.6: Studio compatibility)
    result = {"messages": [response]}
    if "current_state" not in state:
        result["current_state"] = ConversationState.COLLECT_SERVICE
        result["collected_data"] = {}
        result["available_slots"] = []
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
    """
    from src.database import get_postgres_saver

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

    # Production checkpointer
    if os.getenv("DATABASE_URL"):
        with get_postgres_saver() as saver:
            saver.setup()  # Create tables
            return builder.compile(checkpointer=saver)
    else:
        # Fallback for development
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

    def agent_node(state: AppointmentState) -> AppointmentState:
        """
        Agent node that uses org-specific system prompt.

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

        # Invoke LLM
        response = llm_with_tools.invoke(messages_with_system)

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
