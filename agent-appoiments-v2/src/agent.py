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
from src.tools import validate_email_tool, validate_phone_tool
from src.security import PromptInjectionDetector

# Load environment
load_dotenv()

# Security
detector = PromptInjectionDetector(threshold=0.5)

# Tools list
tools = [
    validate_email_tool,
    validate_phone_tool,
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

    base = """You are a friendly appointment booking assistant.

RULES:
- Ask ONE question at a time
- Follow the exact state sequence
- ALWAYS validate email/phone using tools
- Be friendly and professional
"""

    state_prompts = {
        ConversationState.COLLECT_EMAIL: (
            "CURRENT: Collect email.\n"
            "You MUST call validate_email_tool before accepting."
        ),
        ConversationState.COLLECT_PHONE: (
            "CURRENT: Collect phone.\n"
            "You MUST call validate_phone_tool before accepting."
        ),
    }

    instruction = state_prompts.get(current, f"CURRENT: {current.value}")
    return base + "\n" + instruction


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
