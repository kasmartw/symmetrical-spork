"""
Prebuilt agent using create_react_agent (v2.0 - EVALUATION).

This is the RECOMMENDED starting point before custom optimization.
LangGraph's prebuilt agent includes battle-tested optimizations.

Evaluation criteria:
- ✅ Meets functional requirements?
- ✅ Latency competitive with custom?
- ✅ Handles all flows (booking, cancel, reschedule)?
- ✅ Compatible with existing state?

If YES to all → Use this. If NO → Continue with custom optimization.
"""
import os
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Import existing tools
from src.tools import (
    validate_email_tool,
    validate_phone_tool,
    get_services_tool,
    fetch_and_cache_availability_tool,
    filter_and_show_availability_tool,
    create_appointment_tool
)
from src.tools_appointment_mgmt import (
    cancel_appointment_tool,
    get_appointment_tool,
    reschedule_appointment_tool,
)

load_dotenv()

# Simplified state for prebuilt agent
class PrebuiltAgentState(TypedDict):
    """
    State compatible with create_react_agent (LangGraph v1.0).

    NOTE: Prebuilt agent doesn't support custom state fields like current_state.
    All logic must be in system prompt.

    Required fields for LangGraph v1.0:
    - messages: Conversation history
    - remaining_steps: Max iterations remaining (used for recursion control)
    """
    messages: Annotated[list, add_messages]
    remaining_steps: int  # Required by LangGraph v1.0


def build_prebuilt_system_prompt() -> str:
    """
    Single comprehensive prompt for prebuilt agent.

    Must encode ALL state logic since we can't use dynamic current_state.
    This is the main trade-off vs custom implementation.
    """
    return """You are an efficient appointment booking assistant.

**CORE EFFICIENCY RULES:**
- Respond in user's language
- Ask ONE question at a time
- Use MULTIPLE tools in PARALLEL whenever possible
- NEVER use fake/default data
- Complete booking in 2-3 turns (not 7+)

**PARALLEL TOOL USAGE (CRITICAL FOR SPEED):**
- User selects service → fetch_and_cache(svc_id) + ask time preference [BOTH IN SAME RESPONSE]
- User gives "email@test.com and 555-1234" → validate_email() + validate_phone() [BOTH IN SAME RESPONSE]
- When showing availability and user picks slot → CREATE appointment directly [NO EXTRA CONFIRMATION STEP]

**BOOKING FLOW (STREAMLINED):**
1. get_services() → user picks service
2. fetch_and_cache(svc_id) SILENTLY (no message to user) + ask "morning, afternoon, or any time?"
3. filter_and_show(svc_id, time_pref, offset=0) → show 3 days of slots
4. User picks date/time → ask full name
5. Ask email → validate_email() → if INVALID re-ask immediately
6. Ask phone → validate_phone() → if INVALID re-ask immediately
7. Show summary (service, date, time, name, email, phone) → ask "Confirm? (yes/no)"
8. User confirms → create_appointment_tool(ALL DATA) → show confirmation number prominently
9. Done → ask "Anything else?"

**CANCEL FLOW:**
1. Ask for confirmation number (format: APPT-12345)
2. get_appointment_tool(conf#) → show details
3. Ask "Cancel this appointment? (yes/no)"
4. User confirms → cancel_appointment_tool(conf#) → done

**RESCHEDULE FLOW:**
1. Ask for confirmation number
2. get_appointment_tool(conf#) → show current appointment
3. fetch_and_cache(svc_id) + filter_and_show() → show new slots
4. User picks new date/time → show old vs new
5. Ask "Confirm reschedule?"
6. User confirms → reschedule_appointment_tool(conf#, new_date, new_time) → done

**SECURITY:**
- ONLY use confirmation numbers for cancel/reschedule
- NEVER look up appointments by email or phone (security risk)

**EFFICIENCY IMPERATIVE:**
Your goal is to complete each conversation in 2-3 agent turns (not 7+).
Use parallel tools aggressively. Skip unnecessary confirmation steps."""


def create_prebuilt_graph():
    """
    Create agent using LangGraph's optimized create_react_agent.

    This is the RECOMMENDED approach before custom optimization.

    Returns:
        Compiled prebuilt agent graph
    """
    # Create LLM with parallel tools enabled
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=200,
        timeout=15,
        request_timeout=15,
        api_key=os.getenv("OPENAI_API_KEY"),
        model_kwargs={
            "parallel_tool_calls": True  # ← CRITICAL for efficiency
        }
    )

    # Assemble tools list
    tools = [
        # Booking tools
        get_services_tool,
        fetch_and_cache_availability_tool,
        filter_and_show_availability_tool,
        validate_email_tool,
        validate_phone_tool,
        create_appointment_tool,
        # Management tools
        cancel_appointment_tool,
        get_appointment_tool,
        reschedule_appointment_tool,
    ]

    # Build system prompt
    system_prompt = build_prebuilt_system_prompt()

    # Create prebuilt agent with optimizations (LangGraph v1.0 API)
    graph = create_react_agent(
        model=llm,
        tools=tools,
        state_schema=PrebuiltAgentState,
        prompt=system_prompt,  # v1.0: use 'prompt' instead of 'state_modifier'
        checkpointer=MemorySaver(),
    )

    return graph
