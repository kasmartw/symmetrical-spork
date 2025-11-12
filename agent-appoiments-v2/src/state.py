"""State schema for appointment booking agent.

Best Practices (2025):
- TypedDict for lightweight state schemas
- Annotated with add_messages for message accumulation
- Keep state minimal and explicit
- Use Enums for discrete states
"""
from enum import Enum
from typing import TypedDict, Annotated, Optional, Dict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ConversationState(str, Enum):
    """
    Discrete conversation states.

    Supports three flows:
    - Booking flow (11 states)
    - Cancellation flow (4 states)
    - Rescheduling flow (5 states) (v1.3)
    - Hub state (1 state)
    """
    # Booking flow states
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

    # Cancellation flow states (v1.2)
    CANCEL_ASK_CONFIRMATION = "cancel_ask_confirmation"
    CANCEL_VERIFY = "cancel_verify"
    CANCEL_CONFIRM = "cancel_confirm"
    CANCEL_PROCESS = "cancel_process"

    # Rescheduling flow states (v1.3)
    RESCHEDULE_ASK_CONFIRMATION = "reschedule_ask_confirmation"
    RESCHEDULE_VERIFY = "reschedule_verify"
    RESCHEDULE_SELECT_DATETIME = "reschedule_select_datetime"
    RESCHEDULE_CONFIRM = "reschedule_confirm"
    RESCHEDULE_PROCESS = "reschedule_process"

    # Hub state (v1.2)
    POST_ACTION = "post_action"


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
    - retry_count: Retry tracking for error handling (v1.2, v1.3 - cancel & reschedule)

    Pattern from: LangGraph Best Practices (Swarnendu De, 2025)
    """
    messages: Annotated[list[BaseMessage], add_messages]
    current_state: ConversationState
    collected_data: CollectedData
    available_slots: list  # Temporary storage for API responses
    retry_count: Dict[str, int]  # {"cancel": 0, "reschedule": 0} (v1.2, v1.3)


# Type alias for clarity
State = AppointmentState


# State machine transition map
# Pattern: Current state → [allowed next states]
VALID_TRANSITIONS: Dict[ConversationState, list[ConversationState]] = {
    # Booking flow transitions
    ConversationState.COLLECT_SERVICE: [
        ConversationState.SHOW_AVAILABILITY,
        ConversationState.CANCEL_ASK_CONFIRMATION,  # Allow switch to cancel
        ConversationState.RESCHEDULE_ASK_CONFIRMATION,  # Allow switch to reschedule (v1.3)
    ],
    ConversationState.SHOW_AVAILABILITY: [
        ConversationState.COLLECT_DATE,
        ConversationState.CANCEL_ASK_CONFIRMATION,
        ConversationState.RESCHEDULE_ASK_CONFIRMATION,  # v1.3
    ],
    ConversationState.COLLECT_DATE: [
        ConversationState.COLLECT_TIME,
        ConversationState.CANCEL_ASK_CONFIRMATION,
        ConversationState.RESCHEDULE_ASK_CONFIRMATION,  # v1.3
    ],
    ConversationState.COLLECT_TIME: [
        ConversationState.COLLECT_NAME,
        ConversationState.CANCEL_ASK_CONFIRMATION,
        ConversationState.RESCHEDULE_ASK_CONFIRMATION,  # v1.3
    ],
    ConversationState.COLLECT_NAME: [
        ConversationState.COLLECT_EMAIL,
        ConversationState.CANCEL_ASK_CONFIRMATION,
        ConversationState.RESCHEDULE_ASK_CONFIRMATION,  # v1.3
    ],
    ConversationState.COLLECT_EMAIL: [
        ConversationState.COLLECT_PHONE,
        ConversationState.CANCEL_ASK_CONFIRMATION,
        ConversationState.RESCHEDULE_ASK_CONFIRMATION,  # v1.3
    ],
    ConversationState.COLLECT_PHONE: [
        ConversationState.SHOW_SUMMARY,
        ConversationState.CANCEL_ASK_CONFIRMATION,
        ConversationState.RESCHEDULE_ASK_CONFIRMATION,  # v1.3
    ],
    ConversationState.SHOW_SUMMARY: [
        ConversationState.CONFIRM,
        ConversationState.CANCEL_ASK_CONFIRMATION,
        ConversationState.RESCHEDULE_ASK_CONFIRMATION,  # v1.3
    ],
    ConversationState.CONFIRM: [
        ConversationState.CREATE_APPOINTMENT,
        ConversationState.COLLECT_TIME,  # Allow retry if user declines
        ConversationState.CANCEL_ASK_CONFIRMATION,
        ConversationState.RESCHEDULE_ASK_CONFIRMATION,  # v1.3
    ],
    ConversationState.CREATE_APPOINTMENT: [
        ConversationState.COMPLETE,
        ConversationState.POST_ACTION,  # New option (v1.2)
    ],
    ConversationState.COMPLETE: [
        ConversationState.POST_ACTION,  # Can continue to menu
    ],

    # Cancellation flow transitions (v1.2)
    ConversationState.CANCEL_ASK_CONFIRMATION: [
        ConversationState.CANCEL_VERIFY,
    ],
    ConversationState.CANCEL_VERIFY: [
        ConversationState.CANCEL_CONFIRM,
        ConversationState.POST_ACTION,  # Escalation after 2 failures
    ],
    ConversationState.CANCEL_CONFIRM: [
        ConversationState.CANCEL_PROCESS,
        ConversationState.POST_ACTION,  # User declined
    ],
    ConversationState.CANCEL_PROCESS: [
        ConversationState.POST_ACTION,
    ],

    # Rescheduling flow transitions (v1.3)
    ConversationState.RESCHEDULE_ASK_CONFIRMATION: [
        ConversationState.RESCHEDULE_VERIFY,
    ],
    ConversationState.RESCHEDULE_VERIFY: [
        ConversationState.RESCHEDULE_SELECT_DATETIME,
        ConversationState.POST_ACTION,  # Escalation after 2 failures
        ConversationState.COLLECT_SERVICE,  # Offer new booking after escalation
    ],
    ConversationState.RESCHEDULE_SELECT_DATETIME: [
        ConversationState.RESCHEDULE_CONFIRM,
    ],
    ConversationState.RESCHEDULE_CONFIRM: [
        ConversationState.RESCHEDULE_PROCESS,
        ConversationState.RESCHEDULE_SELECT_DATETIME,  # User wants different time
    ],
    ConversationState.RESCHEDULE_PROCESS: [
        ConversationState.POST_ACTION,
    ],

    # Hub state transitions (v1.2)
    ConversationState.POST_ACTION: [
        ConversationState.COLLECT_SERVICE,  # Book new appointment
        ConversationState.CANCEL_ASK_CONFIRMATION,  # Cancel another
        ConversationState.RESCHEDULE_ASK_CONFIRMATION,  # Reschedule another (v1.3)
        # END handled separately
    ],
}


def validate_transition(
    current: ConversationState,
    intended: ConversationState
) -> bool:
    """
    Validate state transition.

    Prevents:
    - Skipping states
    - Backward transitions (except CONFIRM → COLLECT_TIME)
    - Invalid jumps

    Args:
        current: Current conversation state
        intended: Intended next state

    Returns:
        True if transition is valid

    Example:
        >>> validate_transition(
        ...     ConversationState.COLLECT_SERVICE,
        ...     ConversationState.SHOW_AVAILABILITY
        ... )
        True
    """
    allowed = VALID_TRANSITIONS.get(current, [])
    return intended in allowed
