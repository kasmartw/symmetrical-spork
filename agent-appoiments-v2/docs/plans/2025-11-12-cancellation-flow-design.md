# Cancellation Flow Design

**Date:** 2025-11-12
**Status:** Approved
**Version:** 1.0

## Overview

Transform the appointment booking agent from a single-flow system (booking only) to a dual-flow system that supports both appointment booking and cancellation with dynamic flow switching.

## Goals

1. Allow users to cancel appointments at any point in the conversation
2. Support bilingual operation (Spanish/English with auto-detection)
3. Minimize token consumption using pre-agent routing
4. Implement retry logic with human escalation after 2 failed attempts
5. Provide seamless post-action options (book another / cancel another / exit)

## Architecture

### Multi-Flow System

The agent will handle two independent flows:

1. **Booking Flow** (existing): 11 states from COLLECT_SERVICE to COMPLETE
2. **Cancellation Flow** (new): 4 states for cancellation process
3. **Hub State** (new): POST_ACTION for post-completion routing

### Flow Switching

- Users can switch from booking to cancellation at any time
- Detection happens pre-agent using `CancellationIntentDetector` (regex-based)
- Zero token cost for detection
- Follows LangGraph best practices for conditional routing

## State Machine Changes

### New States (5 total)

```python
class ConversationState(str, Enum):
    # ... existing booking states ...

    # Cancellation states
    CANCEL_ASK_CONFIRMATION = "cancel_ask_confirmation"
    CANCEL_VERIFY = "cancel_verify"
    CANCEL_CONFIRM = "cancel_confirm"
    CANCEL_PROCESS = "cancel_process"

    # Hub state
    POST_ACTION = "post_action"
```

### New State Fields

```python
class AppointmentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    current_state: ConversationState
    collected_data: CollectedData
    available_slots: list
    detected_language: Optional[str]  # NEW: "es" | "en"
    retry_count: Dict[str, int]       # NEW: {"cancel": 0}
```

### State Transitions

**Cancellation Flow:**
```
CANCEL_ASK_CONFIRMATION → CANCEL_VERIFY → CANCEL_CONFIRM → CANCEL_PROCESS → POST_ACTION
                               ↓ (2 failures)
                          POST_ACTION (escalation)
```

**From any booking state:**
- Can transition to `CANCEL_ASK_CONFIRMATION` when cancellation intent detected

**From POST_ACTION:**
- → `COLLECT_SERVICE` (book new appointment)
- → `CANCEL_ASK_CONFIRMATION` (cancel another)
- → `END` (finish conversation)

## Language Detection

### Implementation

New file: `src/language.py`

```python
class LanguageDetector:
    """Detects user language from first 2-3 messages."""

    SPANISH_PATTERNS = [
        r'\b(hola|buenos|días|quiero|necesito|cita)\b',
        r'\b(cancelar|agendar|gracias|sí|no)\b',
    ]

    ENGLISH_PATTERNS = [
        r'\b(hello|hi|good|want|need|appointment)\b',
        r'\b(cancel|book|thanks|yes|no)\b',
    ]

    def detect(self, messages: List[str]) -> str:
        """Returns 'es' or 'en', defaults to 'es'"""
```

### Usage

- Detect language in first user message
- Store in `state["detected_language"]`
- Use to generate bilingual system prompts
- Persist throughout entire conversation

## Intent Detection

### Routing Strategy: Pre-Agent (Option 1)

**Pattern:** Detect intent in `chat_cli.py` BEFORE calling agent node

**Why:**
- Zero token cost (regex-based)
- Faster (no LLM latency)
- More predictable
- Follows LangGraph best practices
- Industry standard pattern

**Evidence from research:**
- LangGraph official docs use Python routing functions
- Article "Optimizing initial calls in LangGraph" recommends pre-processing
- All conditional_edges examples use deterministic functions

### Enhanced Patterns

Expand `src/intent.py` with comprehensive patterns:

```python
CANCEL_PATTERNS: List[str] = [
    # Direct - English
    r'\bcancel\s+(my\s+)?(appointment|booking)\b',
    r'\bdelete\s+(my\s+)?appointment\b',

    # Direct - Spanish
    r'\bcancelar\s+(mi\s+)?cita\b',
    r'\beliminar\s+(mi\s+)?cita\b',
    r'\bborrar\s+(mi\s+)?cita\b',

    # Indirect
    r'\b(olvida|forget|olvídate)\b',
    r'\bmejor\s+(no|otro\s+día)\b',
    r'\bya\s+no\b',

    # Contextual
    r'\bno\s+(voy|puedo|podre)\b.*\bcita\b',
]
```

## Retry and Escalation

### Retry Logic

1. **First attempt**: User provides confirmation number → API returns 404
   - Increment `retry_count["cancel"]` = 1
   - Response: "No encontré esa cita. ¿Puedes verificar el número?"
   - Stay in `CANCEL_VERIFY`

2. **Second attempt**: User tries again → API returns 404
   - Increment `retry_count["cancel"]` = 2
   - Trigger escalation

3. **Escalation** (after 2 failures):
   - Bilingual message: "Un miembro del equipo te asistirá..."
   - Transition to `POST_ACTION`
   - Reset `retry_count["cancel"]` = 0

### Escalation Messages

```python
ESCALATION_MESSAGES = {
    "es": """Lo siento, no he podido encontrar tu cita después de varios intentos.
Un miembro del equipo te asistirá personalmente.

📞 Puedes contactarnos en: [SUPPORT_CONTACT]

¿Hay algo más en lo que pueda ayudarte?""",

    "en": """Sorry, I couldn't find your appointment after several attempts.
A team member will assist you personally.

📞 You can contact us at: [SUPPORT_CONTACT]

Is there anything else I can help you with?"""
}
```

## System Prompt Updates

### Bilingual System Prompts

```python
def build_system_prompt(state: AppointmentState) -> str:
    lang = state.get("detected_language", "es")
    current = state["current_state"]

    base = BASE_PROMPTS[lang]  # Bilingual base
    state_instruction = CANCELLATION_PROMPTS[current][lang]

    return base + state_instruction
```

### Cancellation State Instructions

Each cancellation state has specific instructions in both languages:
- `CANCEL_ASK_CONFIRMATION`: Ask for confirmation number
- `CANCEL_VERIFY`: Call cancel_appointment_tool to verify
- `CANCEL_CONFIRM`: Ask "Are you sure?"
- `CANCEL_PROCESS`: Execute cancellation
- `POST_ACTION`: Offer options menu

## Tools Integration

### Add Cancellation Tools

```python
# In src/agent.py
from src.tools_cancellation import (
    cancel_appointment_tool,
    get_user_appointments_tool  # Optional
)

tools = [
    # ... existing tools ...
    cancel_appointment_tool,
    get_user_appointments_tool,
]
```

### Tool Documentation in Prompt

```
AVAILABLE TOOLS:
- cancel_appointment_tool(confirmation_number) - Cancel appointment by code
- get_user_appointments_tool(email) - List user's appointments (optional)
```

## Conversation Flow Example

### Spanish Flow

```
Usuario: "Quiero cancelar mi cita"
  ↓ [Pre-Agent Detection]
Bot: "Claro, ¿cuál es tu número de confirmación?"
  ↓
Usuario: "APPT-5678"
  ↓ [Tool Call]
Bot: "Encontré: Consulta General, 15 nov 10:00 AM. ¿Seguro de cancelar?"
  ↓
Usuario: "Sí"
  ↓ [Cancel Process]
Bot: "✅ Cancelada. ¿Necesitas algo más? (agendar / cancelar otra / terminar)"
  ↓ [POST_ACTION]
```

### English Flow

```
User: "I need to cancel my appointment"
  ↓ [Pre-Agent Detection]
Bot: "Sure, what's your confirmation number?"
  ↓
User: "APPT-5678"
  ↓ [Tool Call]
Bot: "Found: General Consultation, Nov 15 10:00 AM. Cancel it?"
  ↓
User: "Yes"
  ↓ [Cancel Process]
Bot: "✅ Cancelled. Need anything else? (book / cancel another / exit)"
  ↓ [POST_ACTION]
```

## Testing Strategy

### Unit Tests

- `test_cancellation_intent_spanish()` - Spanish patterns
- `test_cancellation_intent_english()` - English patterns
- `test_language_detection()` - ES/EN detection
- `test_cancel_state_transitions()` - Valid transitions
- `test_retry_count_increment()` - Retry logic

### Integration Tests

- `test_full_cancellation_flow()` - End-to-end
- `test_cancellation_retry_logic()` - 2-attempt escalation
- `test_flow_switching()` - Booking → Cancellation
- `test_post_action_routing()` - POST_ACTION → new flows

### Manual Testing Checklist

- [ ] Cancel from initial state
- [ ] Cancel from mid-booking
- [ ] Invalid confirmation number (2 attempts)
- [ ] Successful cancellation → POST_ACTION
- [ ] POST_ACTION → new booking
- [ ] Spanish language detection
- [ ] English language detection

## Files to Create/Modify

### New Files (2)

1. `src/language.py` - Language detection
2. `docs/plans/2025-11-12-cancellation-flow-design.md` - This document

### Modified Files (6)

1. `src/state.py` - Add 5 states + 2 fields
2. `src/agent.py` - Add tools + bilingual prompts
3. `src/intent.py` - Enhance patterns (ES/EN)
4. `chat_cli.py` - Integrate CancellationIntentDetector
5. `tests/unit/test_exit_detection.py` - Expand
6. `tests/integration/test_cancellation.py` - Expand

## Performance Metrics

### Token Consumption

- **Pre-Agent Routing:** 0 tokens (regex)
- **Agent Node Processing:** ~600 tokens per call
- **Total per cancellation:** ~600 tokens
- **Cost:** ~$0.0001 USD per cancellation

### Comparison to Alternatives

- **In-Agent Routing:** 800-2000 tokens (1.3x - 3.3x more expensive)
- **Hybrid Approach:** Complex, minimal benefit

### Time Estimates

| Task | Estimated Time |
|------|----------------|
| Update state.py | 10 min |
| Create language.py | 15 min |
| Update agent.py | 20 min |
| Update intent.py | 10 min |
| Update chat_cli.py | 10 min |
| Update tests | 15 min |
| Manual testing | 10 min |
| **TOTAL** | **90 min** |

## Risk Analysis

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Regex misses edge cases | Low | Add patterns iteratively |
| State transition conflicts | Medium | Validate with VALID_TRANSITIONS |
| Language detection fails | Low | Default to Spanish |
| Breaking existing booking | High | Full regression testing |

## Success Criteria

1. ✅ User can cancel from any point in conversation
2. ✅ Cancellation works in Spanish and English
3. ✅ Retry logic triggers after 2 failed attempts
4. ✅ POST_ACTION offers clear next steps
5. ✅ Zero token cost for intent detection
6. ✅ All tests pass (unit + integration)
7. ✅ No regression in booking flow

## Future Enhancements

- Add `get_user_appointments_tool` for email-based lookup
- Support rescheduling (not just cancellation)
- Add SMS/email notifications for cancellations
- Multi-appointment cancellation (batch)
- Calendar integration

## References

- LangGraph Official Docs: Conditional Routing
- Article: "Optimizing initial calls in LangGraph workflows"
- Article: "Minimizing LLMs' Response Time with LangGraph"
- Article: "Stateful routing with LangGraph" (Medium)
- Research: Industry patterns favor pre-agent routing

---

**Approved by:** User
**Implementation Date:** 2025-11-12
**Expected Completion:** 90 minutes
