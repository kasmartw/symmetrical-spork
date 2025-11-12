"""State schema for appointment booking agent.

Best Practices (2025):
- TypedDict for lightweight state schemas
- Annotated with add_messages for message accumulation
- Keep state minimal and explicit
- Use Enums for discrete states
"""
from enum import Enum
from typing import TypedDict, Annotated, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ConversationState(str, Enum):
    """
    Discrete conversation states.

    State machine is unidirectional with one allowed path.
    Each state represents a specific data collection step.
    """
    COLLECT_SERVICE = "collect_service"
    SHOW_AVAILABILITY = "show_availability"
    COLLECT_DATE = "collect_date"
    COLLECT_TIME = "collect_time"
    COLLECT_NAME = "collect_name"
    COLLECT_EMAIL = "collect_email"
    COLLECT_PHONE = "collect_phone"
    SHOW_SUMMARY = "show_summary"
    CONFIRM = "confirm"
    CREATE_APPOINTMENT = "create_appointment"
    COMPLETE = "complete"


class CollectedData(TypedDict, total=False):
    """
    Structured data collected during conversation.

    total=False allows partial data during collection.
    All fields are optional until completion.
    """
    service_id: Optional[str]
    service_name: Optional[str]
    date: Optional[str]  # ISO format: YYYY-MM-DD
    start_time: Optional[str]  # 24h format: HH:MM
    end_time: Optional[str]
    client_name: Optional[str]
    client_email: Optional[str]
    client_phone: Optional[str]


class AppointmentState(TypedDict):
    """
    Main state for the appointment booking graph.

    Best Practice: Keep state boring and typed.
    - messages: Accumulate with add_messages reducer
    - current_state: Explicit state tracking
    - collected_data: Structured, validated data
    - available_slots: Transient API data

    Pattern from: LangGraph Best Practices (Swarnendu De, 2025)
    """
    messages: Annotated[list[BaseMessage], add_messages]
    current_state: ConversationState
    collected_data: CollectedData
    available_slots: list  # Temporary storage for API responses


# Type alias for clarity
State = AppointmentState
