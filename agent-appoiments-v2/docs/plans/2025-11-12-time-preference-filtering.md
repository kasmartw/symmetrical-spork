# Time Preference Filtering Integration

**Date:** 2025-11-12
**Status:** Design Complete, Ready for Implementation
**Version:** v1.4

## Overview

Integrate the existing `TimeFilter` functionality into the appointment booking flow to allow users to specify their time preference (morning/afternoon) before viewing availability.

## Current State

- Code exists: `src/availability.py` with `TimeFilter` class
- Tests exist: `tests/unit/test_time_filtering.py`
- **NOT integrated:** No state, no tool usage, no prompt instructions

## Design

### 1. State Changes

**New State:**
- Add `COLLECT_TIME_PREFERENCE` between `COLLECT_SERVICE` and `SHOW_AVAILABILITY`

**New Flow:**
```
COLLECT_SERVICE
    ↓
COLLECT_TIME_PREFERENCE (new)
    ↓
SHOW_AVAILABILITY (modified - now filters)
    ↓
COLLECT_DATE
    ↓
COLLECT_TIME
```

**State Schema Changes (`src/state.py`):**

1. Add enum value:
```python
COLLECT_TIME_PREFERENCE = "collect_time_preference"
```

2. Add field to `CollectedData`:
```python
time_preference: Optional[str]  # "morning", "afternoon", "any"
```

3. Update `VALID_TRANSITIONS`:
```python
ConversationState.COLLECT_SERVICE: [
    ConversationState.COLLECT_TIME_PREFERENCE,  # New path
    ConversationState.CANCEL_ASK_CONFIRMATION,
    ConversationState.RESCHEDULE_ASK_CONFIRMATION,
],
ConversationState.COLLECT_TIME_PREFERENCE: [  # New transitions
    ConversationState.SHOW_AVAILABILITY,
    ConversationState.CANCEL_ASK_CONFIRMATION,
    ConversationState.RESCHEDULE_ASK_CONFIRMATION,
],
ConversationState.SHOW_AVAILABILITY: [
    ConversationState.COLLECT_DATE,
    ConversationState.COLLECT_TIME_PREFERENCE,  # Allow going back
    ConversationState.CANCEL_ASK_CONFIRMATION,
    ConversationState.RESCHEDULE_ASK_CONFIRMATION,
],
```

### 2. Agent Modifications

**Import TimeFilter (`src/agent.py`):**
```python
from src.availability import TimeFilter, TimeOfDay
```

**Add System Prompt Instruction:**
```python
ConversationState.COLLECT_TIME_PREFERENCE: (
    "\nCURRENT STATE: COLLECT_TIME_PREFERENCE\n"
    "ACTION: Ask user: 'Do you prefer morning appointments (before 12:00 PM) "
    "or afternoon appointments (after 12:00 PM)? You can also say any time.'\n"
    "Understand responses like:\n"
    "- 'morning', 'mañana', 'temprano', 'antes de mediodía' → store as 'morning'\n"
    "- 'afternoon', 'tarde', 'después de mediodía' → store as 'afternoon'\n"
    "- 'any', 'cualquiera', 'me da igual', 'any time' → store as 'any'\n"
    "Store in collected_data.time_preference"
),
```

**Add Filtering Node:**
```python
def filter_availability_node(state: AppointmentState) -> dict[str, Any]:
    """
    Filter availability results based on time preference.

    Runs after tools node when:
    - current_state is SHOW_AVAILABILITY
    - time_preference is set
    - last tool call was get_availability_tool
    """
    messages = state["messages"]
    preference = state.get("collected_data", {}).get("time_preference")

    # Only filter if we have preference and last message is tool response
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
    import re
    import json

    # Extract slots from response (simplified parsing)
    slots = parse_slots_from_response(last_msg.content)

    if not slots:
        return {}

    # Apply time filter
    time_filter = TimeFilter()
    preference_enum = TimeOfDay.MORNING if preference == "morning" else TimeOfDay.AFTERNOON

    filtered_slots = time_filter.filter_by_time_of_day(slots, preference_enum)
    filtered_slots = time_filter.limit_to_next_days(filtered_slots, max_days=3)

    # Handle no results
    if not filtered_slots:
        from langchain_core.messages import AIMessage
        return {
            "messages": [AIMessage(
                content=(
                    f"[INFO] No {preference} slots available. "
                    f"Would you like to see all available times instead?"
                )
            )]
        }

    # Format filtered results
    formatted = time_filter.format_slots_grouped(filtered_slots)

    # Replace last message with filtered version
    from langchain_core.messages import AIMessage
    return {
        "messages": [AIMessage(content=formatted)]
    }


def parse_slots_from_response(response: str) -> list:
    """Parse availability slots from tool response string."""
    # Extract slot information from formatted response
    # Return list of dicts: [{"date": "...", "start_time": "...", "end_time": "..."}]
    slots = []

    # Simple regex to extract slot lines
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
```

### 3. Graph Modifications

**Update `create_graph()` in `src/agent.py`:**

```python
def create_graph():
    builder = StateGraph(AppointmentState)

    # Add nodes
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("retry_handler", retry_handler_node)
    builder.add_node("filter_availability", filter_availability_node)  # NEW

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

    # After retry_handler, conditionally filter availability
    builder.add_conditional_edges(
        "retry_handler",
        should_filter_availability,  # NEW routing function
        {
            "filter": "filter_availability",
            "skip": "agent",
        }
    )

    # After filtering, return to agent
    builder.add_edge("filter_availability", "agent")

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


def should_filter_availability(state: AppointmentState) -> str:
    """Route to filter if needed."""
    current = state["current_state"]
    preference = state.get("collected_data", {}).get("time_preference")
    messages = state["messages"]

    # Only filter if showing availability with preference set
    if (current == ConversationState.SHOW_AVAILABILITY and
        preference and preference != "any" and
        messages and "[AVAILABILITY]" in str(messages[-1].content)):
        return "filter"

    return "skip"
```

### 4. Edge Cases

**No slots after filtering:**
- Prompt: "No morning/afternoon slots available. Would you like to see all times?"
- Allow transition back to COLLECT_TIME_PREFERENCE

**Ambiguous user response:**
- Map common phrases to preference values
- Spanish: "mañana/temprano" → morning, "tarde" → afternoon
- English: "morning/early" → morning, "afternoon/evening" → afternoon

**Cancellation/Rescheduling flows:**
- Do NOT apply filtering during these flows
- Only filter in booking flow

### 5. Testing Strategy

**Unit Tests:**
- Test `filter_availability_node()` with mock states
- Test `parse_slots_from_response()` with various response formats
- Test preference mapping logic

**Integration Tests:**
- Full flow: service → preference → filtered availability → booking
- Test "no results" scenario
- Test "any" preference (no filtering)

## Implementation Checklist

- [ ] Update `src/state.py`: Add enum, field, transitions
- [ ] Update `src/agent.py`: Import TimeFilter, add prompt instruction
- [ ] Implement `filter_availability_node()` in `src/agent.py`
- [ ] Implement `parse_slots_from_response()` helper
- [ ] Implement `should_filter_availability()` routing function
- [ ] Update graph in `create_graph()` and `create_production_graph()`
- [ ] Write unit tests for new functionality
- [ ] Write integration test for full flow
- [ ] Manual testing via chat_cli.py
- [ ] Update CHANGELOG.md

## Success Criteria

1. User can specify time preference (morning/afternoon/any)
2. Availability shown is filtered based on preference
3. Graceful handling when no slots match preference
4. No impact on cancellation/rescheduling flows
5. All tests pass

## Related Files

- `src/state.py` - State schema
- `src/agent.py` - Agent logic and graph
- `src/availability.py` - Existing filter code (no changes needed)
- `tests/unit/test_time_filtering.py` - Existing filter tests
- New test file: `tests/integration/test_time_preference_flow.py`
