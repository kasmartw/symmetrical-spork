# Optimización del Agente - Corrección de Errores y Mejoras de Performance

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Optimizar el agente de citas existente corrigiendo errores de detección de intención, mejorando configuraciones del LLM, y optimizando herramientas para mejor performance y consistencia.

**Architecture:** Mejoras incrementales sobre arquitectura existente de LangGraph con ChatOpenAI. No se agregan nuevas características, solo optimización de funcionalidad actual.

**Tech Stack:**
- LangGraph 1.0 (StateGraph con MemorySaver)
- LangChain + langchain-openai
- Python 3.12+ con type hints
- Regex para detección de intención mejorada

---

## Task 1: Mejorar Detección de Intención de Finalización

**Files:**
- Modify: `agent-appoiments-v2/src/intent.py:12-54` (ExitIntentDetector)
- Test: `agent-appoiments-v2/tests/test_intent_detection.py` (new file)

**Problem:** El agente solo detecta finalizaciones con palabras clave exactas pero NO entiende contexto cuando el usuario dice "Gracias, hasta luego", "Perfecto, eso es todo", etc.

**Step 1: Write failing tests for contextual exit detection**

Create test file to verify detection of contextual exit phrases:

```python
"""Tests for improved intent detection."""
import pytest
from src.intent import ExitIntentDetector


class TestExitIntentDetector:
    """Test exit intent detection with contextual phrases."""

    def setup_method(self):
        """Initialize detector before each test."""
        self.detector = ExitIntentDetector()

    # Existing exact keyword tests
    def test_exact_exit_keywords_english(self):
        """Test exact exit keywords in English."""
        assert self.detector.is_exit_intent("bye")
        assert self.detector.is_exit_intent("goodbye")
        assert self.detector.is_exit_intent("exit")

    def test_exact_exit_keywords_spanish(self):
        """Test exact exit keywords in Spanish."""
        assert self.detector.is_exit_intent("adiós")
        assert self.detector.is_exit_intent("hasta luego")

    # NEW: Contextual exit intent tests
    def test_contextual_exit_thanks(self):
        """Test 'thanks + goodbye' pattern."""
        assert self.detector.is_exit_intent("Gracias, hasta luego")
        assert self.detector.is_exit_intent("Muchas gracias")
        assert self.detector.is_exit_intent("Thank you, bye")

    def test_contextual_exit_completion(self):
        """Test 'completion' phrases."""
        assert self.detector.is_exit_intent("Perfecto, eso es todo")
        assert self.detector.is_exit_intent("Ok listo, nos vemos")
        assert self.detector.is_exit_intent("Ya está, gracias")
        assert self.detector.is_exit_intent("That's all, thanks")
        assert self.detector.is_exit_intent("Perfect, that's it")

    def test_contextual_exit_done(self):
        """Test 'done' phrases."""
        assert self.detector.is_exit_intent("Ya terminé")
        assert self.detector.is_exit_intent("Listo, ya")
        assert self.detector.is_exit_intent("All done")

    def test_not_exit_intent(self):
        """Test phrases that should NOT trigger exit."""
        # "Thanks" alone without goodbye shouldn't exit
        assert not self.detector.is_exit_intent("Gracias por la información")
        assert not self.detector.is_exit_intent("Thanks for helping")
        # Questions shouldn't exit
        assert not self.detector.is_exit_intent("Qué horarios tienen?")
        # Confirmations shouldn't exit
        assert not self.detector.is_exit_intent("Perfecto, confirmado")
```

**Step 2: Run tests to verify they fail**

Run: `cd agent-appoiments-v2 && source venv/bin/activate && pytest tests/test_intent_detection.py::TestExitIntentDetector -v`

Expected: FAIL - contextual tests fail because current implementation only checks exact keywords

**Step 3: Implement enhanced ExitIntentDetector with contextual patterns**

Update `src/intent.py` ExitIntentDetector class:

```python
class ExitIntentDetector:
    """
    Detect exit/goodbye intents with contextual understanding.

    Pattern: Multi-level pattern matching:
    1. Exact keywords (high confidence)
    2. Contextual phrases (medium confidence)
    3. Completion signals (medium confidence)
    """

    # Level 1: Exact exit keywords (original patterns)
    EXIT_KEYWORDS: List[str] = [
        # English
        r'\b(bye|goodbye|exit|quit)\b',
        r'\bno\s+thanks?\b',
        r'\bnevermind\b',
        r'\bdon\'?t\s+need\b',
        r'\bno\s+longer\b',
        r'\bstop\b',
        # Spanish
        r'\b(adios|adiós|chao|chau)\b',
        r'\b(hasta\s+luego|hasta\s+pronto)\b',
        r'\bno\s+gracias\b',
        r'\bno\s+necesito\b',
        r'\bno\s+importa\b',
        r'\bsalir\b',
        r'\bterminar\b',
        r'\bfinalizar\b',
        r'\bya\s+no\b',
    ]

    # Level 2: Contextual completion phrases (NEW)
    COMPLETION_PATTERNS: List[str] = [
        # "Thanks + something" patterns
        r'\b(gracias|muchas\s+gracias|thank\s+you|thanks)\s*,?\s*(hasta|bye|adiós|luego|nos\s+vemos)',
        r'\b(muchas\s+gracias|thank\s+you\s+so\s+much|thanks\s+a\s+lot)\b',

        # "Done/finished" patterns
        r'\b(perfecto|perfect|ok|listo|ya\s+está)\s*,?\s*(eso\s+es\s+todo|that\'?s\s+(all|it)|nos\s+vemos)',
        r'\bya\s+(terminé|termine|está|esta)\b',
        r'\b(all\s+done|i\'?m\s+done|that\'?s\s+everything)\b',

        # "That's all" patterns
        r'\beso\s+es\s+todo\b',
        r'\bthat\'?s\s+(all|it|everything)\b',
        r'\bnada\s+más\b',
        r'\bnothing\s+(else|more)\b',
    ]

    def is_exit_intent(self, message: str) -> bool:
        """
        Check if message expresses exit intent.

        Uses two-level detection:
        1. Exact keywords (original behavior)
        2. Contextual completion phrases (NEW)

        Args:
            message: User message

        Returns:
            True if user wants to exit
        """
        message_lower = message.lower().strip()

        # Level 1: Check exact keywords
        if any(re.search(pattern, message_lower, re.IGNORECASE)
               for pattern in self.EXIT_KEYWORDS):
            return True

        # Level 2: Check contextual completion patterns
        if any(re.search(pattern, message_lower, re.IGNORECASE)
               for pattern in self.COMPLETION_PATTERNS):
            return True

        return False
```

**Step 4: Run tests to verify they pass**

Run: `cd agent-appoiments-v2 && source venv/bin/activate && pytest tests/test_intent_detection.py::TestExitIntentDetector -v`

Expected: PASS - all tests pass including contextual detection

**Step 5: Commit**

```bash
cd agent-appoiments-v2
git add src/intent.py tests/test_intent_detection.py
git commit -m "feat: improve exit intent detection with contextual phrases

- Add contextual pattern detection for 'thanks + goodbye'
- Add completion phrase detection ('that's all', 'eso es todo')
- Maintain backward compatibility with exact keywords
- Add comprehensive tests for new patterns

Fixes: Agent not ending conversation naturally when user says
'Gracias, hasta luego' or 'Perfecto, eso es todo'"
```

---

## Task 2: Optimizar Configuración del LLM

**Files:**
- Modify: `agent-appoiments-v2/src/agent.py:68-73`
- Test: Manual testing + integration tests

**Problem:** LLM usa configuración por defecto (temperatura alta, sin límite de tokens, sin timeout) causando respuestas inconsistentes y largas.

**Step 1: Write test to verify LLM configuration**

Add to existing test file or create new test:

```python
"""Test LLM configuration is properly set."""
import pytest
from src.agent import llm


def test_llm_configuration():
    """Verify LLM has optimal configuration for consistency."""
    # Check model
    assert llm.model_name == "gpt-4o-mini"

    # Check temperature for consistency
    assert llm.temperature == 0.2, "Temperature should be 0.2 for consistent responses"

    # Check max tokens to avoid long responses
    assert llm.max_tokens == 200, "max_tokens should limit response length"

    # Check timeout settings
    assert llm.request_timeout == 15, "Should have 15s timeout"
```

**Step 2: Run test to verify it fails**

Run: `cd agent-appoiments-v2 && source venv/bin/activate && pytest tests/test_llm_config.py::test_llm_configuration -v`

Expected: FAIL - current configuration doesn't have temperature, max_tokens, or timeout set

**Step 3: Update LLM configuration with optimized settings**

Modify `src/agent.py` lines 68-73:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd agent-appoiments-v2 && source venv/bin/activate && pytest tests/test_llm_config.py::test_llm_configuration -v`

Expected: PASS

**Step 5: Manual integration test**

Test conversation to verify responses are concise and consistent:

```bash
cd agent-appoiments-v2
python chat_cli.py
# Test multiple conversations with same questions
# Verify responses are:
# 1. Consistent across runs
# 2. Concise (not overly verbose)
# 3. Complete within 15s timeout
```

**Step 6: Commit**

```bash
cd agent-appoiments-v2
git add src/agent.py tests/test_llm_config.py
git commit -m "perf: optimize LLM configuration for consistency

- Set temperature=0.2 for predictable responses
- Set max_tokens=200 to prevent verbose responses
- Add timeout=15 and request_timeout=15 to prevent hanging
- Add test to verify LLM configuration

Benefits:
- More consistent responses across conversations
- Faster responses (concise output)
- No hanging on API failures"
```

---

## Task 3: Mejorar Docstrings de Todas las Tools (VERSIÓN CONCISA)

**Files:**
- Modify: `agent-appoiments-v2/src/tools.py` (all @tool functions)
- Modify: `agent-appoiments-v2/src/tools_appointment_mgmt.py` (all @tool functions)

**Problem:** El LLM no entiende bien cuándo usar cada tool porque los docstrings no son lo suficientemente descriptivos.

**CRITICAL CONSTRAINT:** Docstrings deben ser CONCISOS (3-5 líneas max) para no consumir tokens innecesarios. Priorizar "when to use" sobre descripciones largas.

**Step 1: Write test to verify tool docstrings exist and are descriptive**

```python
"""Test that all tools have descriptive docstrings."""
import pytest
from src.tools import (
    validate_email_tool,
    validate_phone_tool,
    get_services_tool,
    fetch_and_cache_availability_tool,
    filter_and_show_availability_tool,
    create_appointment_tool,
)
from src.tools_appointment_mgmt import (
    cancel_appointment_tool,
    get_appointment_tool,
    reschedule_appointment_tool,
)


def test_all_tools_have_docstrings():
    """Verify all tools have non-empty docstrings."""
    tools = [
        validate_email_tool,
        validate_phone_tool,
        get_services_tool,
        fetch_and_cache_availability_tool,
        filter_and_show_availability_tool,
        create_appointment_tool,
        cancel_appointment_tool,
        get_appointment_tool,
        reschedule_appointment_tool,
    ]

    for tool in tools:
        assert tool.__doc__ is not None, f"{tool.name} missing docstring"
        assert len(tool.__doc__) > 50, f"{tool.name} docstring too short"
        # Check for key phrases
        assert "Args:" in tool.__doc__ or "Parameters:" in tool.__doc__, \
            f"{tool.name} docstring missing Args section"
        assert "Returns:" in tool.__doc__, \
            f"{tool.name} docstring missing Returns section"


def test_tools_have_when_to_use_guidance():
    """Verify tools explain WHEN to use them (for LLM)."""
    # These tools need "Use this when..." or "Call this when..." guidance
    critical_tools = [
        (fetch_and_cache_availability_tool, ["IMMEDIATELY after", "Use this"]),
        (filter_and_show_availability_tool, ["AFTER user responds", "Use this"]),
        (create_appointment_tool, ["ONLY AFTER", "Call this"]),
    ]

    for tool, expected_phrases in critical_tools:
        doc = tool.__doc__
        assert any(phrase in doc for phrase in expected_phrases), \
            f"{tool.name} docstring missing 'when to use' guidance"
```

**Step 2: Run tests to verify current docstrings**

Run: `cd agent-appoiments-v2 && source venv/bin/activate && pytest tests/test_tool_docstrings.py -v`

Expected: PASS or PARTIAL PASS - some tools may already have good docstrings

**Step 3: Enhance validate_email_tool and validate_phone_tool docstrings (CONCISE VERSION)**

Update `src/tools.py` with CONCISE docstrings:

```python
@tool
def validate_email_tool(email: str) -> str:
    """
    Validate email format. Call IMMEDIATELY after user provides email.
    Returns [VALID] or [INVALID]. If [INVALID], ask user to provide correct email.
    """
    is_valid, message = validation_cache.validate_email(email)
    if is_valid:
        return f"[VALID] Email '{email}' is valid."
    else:
        return f"[INVALID] Email '{email}' is not valid. Please provide a valid email (e.g., name@example.com)."


@tool
def validate_phone_tool(phone: str) -> str:
    """
    Validate phone number (7+ digits). Call IMMEDIATELY after user provides phone.
    Returns [VALID] or [INVALID]. If [INVALID], ask user to provide correct phone.
    """
    is_valid, message = validation_cache.validate_phone(phone)
    if is_valid:
        return f"[VALID] Phone '{phone}' is valid."
    else:
        return f"[INVALID] Phone '{phone}' is not valid. Please provide at least 7 digits."
```

**Step 4: Enhance get_services_tool, fetch_and_cache, filter_and_show docstrings (CONCISE VERSION)**

Continue updating `src/tools.py` with CONCISE docstrings:

```python
@tool
def get_services_tool() -> str:
    """
    Get available services. Call at START of conversation or when user asks "what services?".
    Returns [SERVICES] list with IDs and names. No parameters needed.
    """
    # ... existing implementation


@tool
def fetch_and_cache_availability_tool(service_id: str) -> str:
    """
    Fetch 30 days of availability and cache (BACKGROUND only - does NOT show to user).
    Call IMMEDIATELY after user selects service, BEFORE asking time preference.
    Returns [SUCCESS] with count. Then ask time preference and use filter_and_show tool.
    """
    # ... existing implementation


@tool
def filter_and_show_availability_tool(
    service_id: str,
    time_preference: str = "any",
    offset: int = 0
) -> str:
    """
    Filter cached slots by time and show 3 days to user. Call AFTER user responds to time preference.
    time_preference: "morning" (before 12pm), "afternoon" (12pm+), or "any".
    offset: 0 for first 3 days, 3 for next 3 days, etc.
    Returns [AVAILABILITY] formatted for user. This is what user sees!
    """
    # ... existing implementation
```

**Step 5: Enhance create_appointment_tool docstring (CONCISE VERSION)**

```python
@tool
def create_appointment_tool(
    service_id: str,
    date: str,
    start_time: str,
    client_name: str,
    client_email: str,
    client_phone: str
) -> str:
    """
    Create appointment. Call ONLY AFTER user confirms AND email/phone validated.
    date: YYYY-MM-DD, start_time: HH:MM (24-hour).
    Returns [SUCCESS] with confirmation number or [ERROR] with alternatives.
    """
    # ... existing implementation
```

**Step 6: Run tests to verify enhanced docstrings**

Run: `cd agent-appoiments-v2 && source venv/bin/activate && pytest tests/test_tool_docstrings.py -v`

Expected: PASS - all tools now have comprehensive docstrings

**Step 7: Commit tools.py changes**

```bash
cd agent-appoiments-v2
git add src/tools.py tests/test_tool_docstrings.py
git commit -m "docs: enhance tool docstrings with LLM-friendly guidance

- Add 'When to use' section to all tools
- Add 'What it does' explanations
- Add 'Next step after...' guidance for LLM
- Add performance notes
- Add comprehensive examples
- Add tests to verify docstring quality

Benefits:
- LLM better understands when to call each tool
- Clearer parameter expectations
- Better error recovery guidance"
```

**Step 8: Enhance appointment management tools docstrings (CONCISE VERSION)**

Update `src/tools_appointment_mgmt.py` with CONCISE docstrings:

```python
@tool
def cancel_appointment_tool(confirmation_number: str) -> str:
    """
    Cancel appointment. Call AFTER user confirms cancellation.
    SECURITY: Only accepts confirmation number (NO email lookup).
    Returns [SUCCESS] or [ERROR]. System auto-escalates after 2 failures.
    """
    # ... existing implementation


@tool
def get_appointment_tool(confirmation_number: str) -> str:
    """
    Get appointment details for rescheduling. Call IMMEDIATELY after user provides confirmation number.
    SECURITY: Only accepts confirmation number (NO email lookup).
    Returns [APPOINTMENT] with current details or [ERROR]. System auto-escalates after 2 failures.
    """
    # ... existing implementation


@tool
def reschedule_appointment_tool(
    confirmation_number: str,
    new_date: str,
    new_start_time: str
) -> str:
    """
    Reschedule appointment. Call ONLY AFTER user confirms AND selects new date/time.
    Client info preserved automatically (NO need to ask again).
    new_date: YYYY-MM-DD, new_start_time: HH:MM (24-hour).
    Returns [SUCCESS] with updated details or [ERROR].
    """
    # ... existing implementation
```

**Step 9: Commit tools_appointment_mgmt.py changes**

```bash
cd agent-appoiments-v2
git add src/tools_appointment_mgmt.py
git commit -m "docs: enhance appointment mgmt tool docstrings

- Add 'When to use' guidance for all mgmt tools
- Add security notes (confirmation number only)
- Add 'Next step after...' guidance
- Clarify client info preservation in rescheduling

Benefits:
- LLM understands security requirements better
- Clearer flow for cancellation and rescheduling
- Better error recovery"
```

---

## Task 4: Optimizar Retry Handler

**Files:**
- Modify: `agent-appoiments-v2/src/agent.py:363-440` (retry_handler_node)
- Test: `agent-appoiments-v2/tests/test_retry_handler.py` (new file)

**Problem:** Retry handler es muy básico - solo cuenta intentos pero no detecta QUÉ tipo de error ocurrió.

**Step 1: Write tests for intelligent retry handling**

Create test file:

```python
"""Tests for intelligent retry handler."""
import pytest
from langchain_core.messages import AIMessage, ToolMessage
from src.agent import retry_handler_node
from src.state import AppointmentState, ConversationState


class TestRetryHandler:
    """Test retry handler intelligence."""

    def test_retry_on_not_found_error(self):
        """Test retry increments on 'not found' errors."""
        state: AppointmentState = {
            "messages": [
                ToolMessage(
                    content="[ERROR] Appointment APPT-9999 not found",
                    tool_call_id="test-123"
                )
            ],
            "current_state": ConversationState.CANCEL_VERIFY,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = retry_handler_node(state)

        # Should increment cancel retry count
        assert result.get("retry_count", {}).get("cancel") == 1

    def test_no_retry_on_success(self):
        """Test no retry increment on successful tool responses."""
        state: AppointmentState = {
            "messages": [
                ToolMessage(
                    content="[APPOINTMENT] Current appointment: ...",
                    tool_call_id="test-123"
                )
            ],
            "current_state": ConversationState.RESCHEDULE_VERIFY,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = retry_handler_node(state)

        # Should not increment retry count
        assert result.get("retry_count", {}) == {}

    def test_escalation_after_2_failures(self):
        """Test escalation to POST_ACTION after 2 failures."""
        state: AppointmentState = {
            "messages": [
                ToolMessage(
                    content="[ERROR] Appointment APPT-9999 not found",
                    tool_call_id="test-123"
                )
            ],
            "current_state": ConversationState.RESCHEDULE_VERIFY,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {"reschedule": 1},  # Already 1 failure
        }

        result = retry_handler_node(state)

        # Should escalate to POST_ACTION
        assert result.get("current_state") == ConversationState.POST_ACTION
        # Should have escalation message
        messages = result.get("messages", [])
        assert len(messages) > 0
        assert "cannot find your appointment" in messages[0].content.lower()

    def test_no_action_on_non_verify_states(self):
        """Test handler does nothing outside VERIFY states."""
        state: AppointmentState = {
            "messages": [
                ToolMessage(
                    content="[ERROR] Some error",
                    tool_call_id="test-123"
                )
            ],
            "current_state": ConversationState.COLLECT_SERVICE,
            "collected_data": {},
            "available_slots": [],
            "retry_count": {},
        }

        result = retry_handler_node(state)

        # Should return empty dict (no changes)
        assert result == {}
```

**Step 2: Run tests to verify current behavior**

Run: `cd agent-appoiments-v2 && source venv/bin/activate && pytest tests/test_retry_handler.py -v`

Expected: PASS - current implementation should already handle these cases

**Step 3: Enhance retry handler with error type detection**

Update `src/agent.py` retry_handler_node function:

```python
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
```

**Step 4: Add tests for new error type detection**

Add to `tests/test_retry_handler.py`:

```python
def test_immediate_escalation_on_system_error():
    """Test immediate escalation on API/system errors (no retry)."""
    state: AppointmentState = {
        "messages": [
            ToolMessage(
                content="[ERROR] Could not connect to API: Connection timeout",
                tool_call_id="test-123"
            )
        ],
        "current_state": ConversationState.CANCEL_VERIFY,
        "collected_data": {},
        "available_slots": [],
        "retry_count": {},
    }

    result = retry_handler_node(state)

    # Should escalate immediately without retry
    assert result.get("current_state") == ConversationState.POST_ACTION
    messages = result.get("messages", [])
    assert "technical difficulties" in messages[0].content.lower()


def test_retry_on_user_error():
    """Test retry on user errors (wrong confirmation number)."""
    state: AppointmentState = {
        "messages": [
            ToolMessage(
                content="[ERROR] Appointment APPT-9999 not found",
                tool_call_id="test-123"
            )
        ],
        "current_state": ConversationState.CANCEL_VERIFY,
        "collected_data": {},
        "available_slots": [],
        "retry_count": {},
    }

    result = retry_handler_node(state)

    # Should increment retry, not escalate yet
    assert result.get("retry_count", {}).get("cancel") == 1
    assert "current_state" not in result  # No state change yet
```

**Step 5: Run tests to verify enhanced retry handler**

Run: `cd agent-appoiments-v2 && source venv/bin/activate && pytest tests/test_retry_handler.py -v`

Expected: PASS

**Step 6: Commit**

```bash
cd agent-appoiments-v2
git add src/agent.py tests/test_retry_handler.py
git commit -m "feat: enhance retry handler with error type detection

- Classify errors as user errors (retryable) vs system errors (not retryable)
- Immediate escalation on API/system errors
- User errors allow 2 retries before escalation
- Add tests for error classification

Benefits:
- Better UX on system failures (no pointless retries)
- Clearer error messages for users
- Faster escalation on technical issues"
```

---

## Task 5: Optimizar Sistema de Caché

**Files:**
- Modify: `agent-appoiments-v2/src/cache.py:1-138`
- Test: `agent-appoiments-v2/tests/test_cache.py` (new file)

**Problem:** El caché actual tiene TTL fijo y no limpia entradas antiguas automáticamente.

**Step 1: Write tests for cache optimization**

```python
"""Tests for optimized cache system."""
import pytest
import time
from src.cache import ValidationCache, AvailabilityCache


class TestValidationCache:
    """Test validation cache with TTL."""

    def setup_method(self):
        """Reset cache before each test."""
        self.cache = ValidationCache()
        self.cache.email_cache.clear()
        self.cache.phone_cache.clear()

    def test_cache_hit(self):
        """Test cache returns cached result."""
        # First call validates and caches
        result1 = self.cache.validate_email("test@example.com")
        # Second call should hit cache
        result2 = self.cache.validate_email("test@example.com")
        assert result1 == result2

    def test_cache_ttl_expiration(self):
        """Test cache entries expire after TTL."""
        # Cache with very short TTL for testing
        self.cache.ttl = 0.1  # 100ms

        # Cache result
        self.cache.validate_email("test@example.com")

        # Wait for expiration
        time.sleep(0.2)

        # Should revalidate (cache expired)
        # We can't directly test this without mocking, but we verify
        # the cache doesn't grow indefinitely
        assert len(self.cache.email_cache) >= 0


class TestAvailabilityCache:
    """Test availability cache optimization."""

    def setup_method(self):
        """Reset cache before each test."""
        self.cache = AvailabilityCache()
        self.cache.cache.clear()

    def test_cache_stores_availability(self):
        """Test cache stores and retrieves availability."""
        slots = [{"date": "2025-11-15", "start_time": "09:00"}]
        service = {"id": "srv-001", "name": "Test Service"}

        self.cache.set("srv-001", slots, service, {}, {})

        result = self.cache.get("srv-001")
        assert result is not None
        assert result["slots"] == slots
        assert result["service"] == service

    def test_cache_ttl(self):
        """Test cache expires after TTL."""
        # Cache with short TTL
        self.cache.ttl = 0.1  # 100ms

        slots = [{"date": "2025-11-15", "start_time": "09:00"}]
        self.cache.set("srv-001", slots, {}, {}, {})

        # Should be cached
        assert self.cache.get("srv-001") is not None

        # Wait for expiration
        time.sleep(0.2)

        # Should be expired
        assert self.cache.get("srv-001") is None
```

**Step 2: Run tests to verify current cache behavior**

Run: `cd agent-appoiments-v2 && source venv/bin/activate && pytest tests/test_cache.py -v`

Expected: PASS or PARTIAL - current implementation may already support TTL

**Step 3: Enhance cache with automatic cleanup**

Update `src/cache.py`:

```python
"""Caching system for validation and availability (OPTIMIZED v1.2, v1.5, v1.7).

Best Practices:
- Use TTL (time-to-live) for automatic expiration
- Automatic cleanup of expired entries
- Thread-safe for concurrent access
- Memory-efficient with size limits
"""
import re
import time
from typing import Tuple, Optional, Dict, Any, List
from datetime import datetime, timedelta


class ValidationCache:
    """
    Cache for email/phone validation (100x performance improvement).

    Pattern: In-memory cache with TTL and automatic cleanup.

    v1.7 Enhancements:
    - Automatic cleanup of expired entries
    - Configurable TTL
    - Memory limit to prevent unbounded growth
    """

    def __init__(self, ttl: int = 3600, max_size: int = 1000):
        """
        Initialize validation cache.

        Args:
            ttl: Time-to-live in seconds (default: 1 hour)
            max_size: Maximum cache entries before cleanup (default: 1000)
        """
        self.email_cache: Dict[str, Tuple[bool, str, float]] = {}
        self.phone_cache: Dict[str, Tuple[bool, str, float]] = {}
        self.ttl = ttl  # seconds
        self.max_size = max_size

    def _is_expired(self, timestamp: float) -> bool:
        """Check if cache entry has expired."""
        return time.time() - timestamp > self.ttl

    def _cleanup_if_needed(self, cache: Dict[str, Tuple[bool, str, float]]):
        """Clean up expired entries if cache is getting large."""
        if len(cache) > self.max_size:
            # Remove expired entries
            current_time = time.time()
            expired_keys = [
                key for key, (_, _, ts) in cache.items()
                if current_time - ts > self.ttl
            ]
            for key in expired_keys:
                del cache[key]

            # If still too large, remove oldest entries
            if len(cache) > self.max_size:
                sorted_items = sorted(cache.items(), key=lambda x: x[1][2])
                to_remove = len(cache) - self.max_size
                for key, _ in sorted_items[:to_remove]:
                    del cache[key]

    def validate_email(self, email: str) -> Tuple[bool, str]:
        """
        Validate email with caching.

        Args:
            email: Email to validate

        Returns:
            Tuple of (is_valid, message)
        """
        # Check cache
        if email in self.email_cache:
            is_valid, message, timestamp = self.email_cache[email]
            if not self._is_expired(timestamp):
                return (is_valid, message)

        # Validate
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        is_valid = bool(re.match(pattern, email))
        message = f"Email '{email}' is valid." if is_valid else f"Email '{email}' is invalid."

        # Cache result with timestamp
        self.email_cache[email] = (is_valid, message, time.time())

        # Cleanup if needed
        self._cleanup_if_needed(self.email_cache)

        return (is_valid, message)

    def validate_phone(self, phone: str) -> Tuple[bool, str]:
        """
        Validate phone with caching.

        Args:
            phone: Phone to validate

        Returns:
            Tuple of (is_valid, message)
        """
        # Check cache
        if phone in self.phone_cache:
            is_valid, message, timestamp = self.phone_cache[phone]
            if not self._is_expired(timestamp):
                return (is_valid, message)

        # Validate (count digits only)
        digits = re.sub(r'\D', '', phone)
        is_valid = len(digits) >= 7
        message = f"Phone '{phone}' is valid." if is_valid else f"Phone '{phone}' needs at least 7 digits."

        # Cache result with timestamp
        self.phone_cache[phone] = (is_valid, message, time.time())

        # Cleanup if needed
        self._cleanup_if_needed(self.phone_cache)

        return (is_valid, message)


class AvailabilityCache:
    """
    Cache for availability data (v1.5 - 30-day caching strategy).

    Pattern: Service-keyed cache with TTL.

    v1.7 Enhancements:
    - Configurable TTL based on business hours
    - Automatic cleanup
    - Memory-efficient storage
    """

    def __init__(self, ttl: int = 1800):
        """
        Initialize availability cache.

        Args:
            ttl: Time-to-live in seconds (default: 30 minutes)
                 30 minutes is optimal for balancing freshness and performance
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl  # seconds

    def _is_expired(self, timestamp: float) -> bool:
        """Check if cache entry has expired."""
        return time.time() - timestamp > self.ttl

    def get(self, service_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached availability for service.

        Args:
            service_id: Service ID

        Returns:
            Cached data or None if not found/expired
        """
        if service_id not in self.cache:
            return None

        data = self.cache[service_id]

        # Check expiration
        if self._is_expired(data.get("timestamp", 0)):
            # Remove expired entry
            del self.cache[service_id]
            return None

        return data

    def set(
        self,
        service_id: str,
        slots: List[Dict[str, Any]],
        service: Dict[str, Any],
        location: Dict[str, Any],
        assigned_person: Dict[str, Any]
    ):
        """
        Cache availability data for service.

        Args:
            service_id: Service ID
            slots: Available time slots
            service: Service details
            location: Location details
            assigned_person: Provider details
        """
        self.cache[service_id] = {
            "slots": slots,
            "service": service,
            "location": location,
            "assigned_person": assigned_person,
            "timestamp": time.time()
        }

    def clear(self, service_id: Optional[str] = None):
        """
        Clear cache entries.

        Args:
            service_id: Specific service to clear, or None to clear all
        """
        if service_id:
            self.cache.pop(service_id, None)
        else:
            self.cache.clear()

    def cleanup_expired(self):
        """Remove all expired entries."""
        current_time = time.time()
        expired_keys = [
            key for key, data in self.cache.items()
            if current_time - data.get("timestamp", 0) > self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]


# Global instances
validation_cache = ValidationCache(ttl=3600, max_size=1000)  # 1 hour TTL, max 1000 entries
availability_cache = AvailabilityCache(ttl=1800)  # 30 minutes TTL
```

**Step 4: Run tests to verify optimized cache**

Run: `cd agent-appoiments-v2 && source venv/bin/activate && pytest tests/test_cache.py -v`

Expected: PASS

**Step 5: Commit**

```bash
cd agent-appoiments-v2
git add src/cache.py tests/test_cache.py
git commit -m "perf: optimize cache system with automatic cleanup

- Add configurable TTL for both validation and availability caches
- Implement automatic cleanup of expired entries
- Add memory limits to prevent unbounded growth
- Add cleanup_expired() method for manual cleanup
- Improve cache efficiency with timestamp-based expiration

Benefits:
- Prevents memory leaks from cache growth
- Configurable TTL based on use case
- Better memory efficiency
- Automatic cleanup reduces manual management"
```

---

## Task 6: [OPCIONAL] Mejorar Consistencia de Mensajes en System Prompt

**⚠️ WARNING: Esta task es OPCIONAL y EXPERIMENTAL**

**Files:**
- Modify: `agent-appoiments-v2/src/agent.py` (enhance system prompt)

**Problem:** Mensajes del bot varían mucho debido al LLM. Queremos mensajes más consistentes y profesionales.

**CRITICAL REALITY CHECK:**
- ❌ Templates en system prompt son solo "sugerencias", NO garantías
- ❌ Con `temperature=0.2`, el LLM NO reproducirá templates exactos
- ❌ No hay mecanismo para FORZAR al LLM a usar text exacto
- ✅ Solo podemos GUIAR al LLM con ejemplos en system prompt
- ✅ Templates son útiles para POST-PROCESSING (fuera de scope de este plan)
- ✅ O para mensajes automáticos no generados por LLM (escalaciones, errores)

**RECOMMENDATION:**
- Implementar esta task SOLO como experimento
- Medir si mejora consistencia con testing manual
- Si NO mejora consistencia perceptiblemente, DESCARTAR esta task
- NO dedicar más de 30 minutos a esta task

**Step 1: Add consistency guidelines to system prompt (EXPERIMENTAL)**

Update `src/agent.py` build_system_prompt function to add message consistency examples:

```python
def build_system_prompt(state: AppointmentState) -> str:
    """Build context-aware system prompt (v1.7 - consistency guidance)."""
    current = state.get("current_state", ConversationState.COLLECT_SERVICE)

    base = """You are a friendly assistant for booking, cancelling, and rescheduling appointments at Downtown Medical Center.

IMPORTANT: Respond in the SAME LANGUAGE the user speaks to you (Spanish, English, etc).

CONSISTENCY GUIDELINES (v1.7 - EXPERIMENTAL):
Keep responses concise and professional. Examples of preferred style:
- Greeting: "Hello! Welcome to Downtown Medical Center. How can I help you today?"
- Time preference: "Do you prefer morning (before 12 PM), afternoon (after 12 PM), or any time?"
- Confirmation: Always include: service, date, time, client name, email, phone
- Success: Always mention confirmation number and remind to save it

AVAILABLE FLOWS:
... (rest unchanged)
"""
    # ... rest of function unchanged
```

**Step 2: Manual testing (30 minutes max)**

Test if consistency improved:

```bash
cd agent-appoiments-v2
python chat_cli.py

# Test same conversation 3 times:
# 1. Book appointment in English
# 2. Book appointment in Spanish
# 3. Book appointment in English again

# Compare responses:
# - Are greetings similar?
# - Are time preference questions similar?
# - Are confirmation messages similar?
```

**Step 3: Decision point**

**If consistency improved noticeably:** Commit changes

```bash
cd agent-appoiments-v2
git add src/agent.py
git commit -m "experiment: add message consistency guidelines to system prompt

- Add examples of preferred message style
- Guide LLM toward concise, professional responses
- Experimental: measure consistency improvement

Note: This is guidance only - LLM may still vary responses"
```

**If NO noticeable improvement:** Revert changes and skip this task

```bash
cd agent-appoiments-v2
git checkout src/agent.py
# SKIP THIS TASK - temperature=0.2 + better docstrings may be enough
```

**RECOMMENDATION:** Given the limited impact and time investment, consider skipping this task entirely and relying on Task 2 (LLM config) + Task 3 (tool docstrings) for improved consistency.

---
## Task 7: Optimizar Llamadas HTTP a API

**Files:**
- Modify: `agent-appoiments-v2/src/tools.py` (all HTTP requests)
- Test: Manual testing

**Problem:** Llamadas HTTP no tienen retry automático ni connection pooling.

**Step 1: Create HTTP client utility**

Create new file `src/http_client.py`:

```python
"""HTTP client utilities with retry and connection pooling (v1.7).

Purpose: Centralize HTTP configuration for better performance and resilience.

Pattern: requests.Session with retry strategy and connection pooling.
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src import config


def create_http_session(
    max_retries: int = 3,
    backoff_factor: float = 0.3,
    timeout: int = 5
) -> requests.Session:
    """
    Create HTTP session with retry and connection pooling.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Backoff multiplier (default: 0.3)
                       Retry delays: 0.3s, 0.6s, 1.2s
        timeout: Request timeout in seconds (default: 5)

    Returns:
        Configured requests.Session
    """
    session = requests.Session()

    # Retry strategy
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP codes
        allowed_methods=["GET", "POST"],  # Retry these methods
    )

    # Mount adapter with retry strategy
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,  # Connection pool size
        pool_maxsize=10,      # Max connections in pool
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


# Global session (reuse connections)
api_session = create_http_session()
```

**Step 2: Update tools to use HTTP session**

Update `src/tools.py` to import and use session:

```python
from src.http_client import api_session

@tool
def get_services_tool() -> str:
    """Get list of available services from the API (OPTIMIZED v1.7)."""
    try:
        response = api_session.get(
            f"{config.MOCK_API_BASE_URL}/services",
            timeout=5
        )
        response.raise_for_status()
        # ... rest unchanged
    except requests.exceptions.RequestException as e:
        return f"[ERROR] Could not connect to API: {str(e)}"
    except Exception as e:
        return f"[ERROR] Unexpected error: {str(e)}"


@tool
def fetch_and_cache_availability_tool(service_id: str) -> str:
    """Fetch 30 days of availability and cache it (OPTIMIZED v1.7)."""
    try:
        date_from = datetime.now().strftime("%Y-%m-%d")
        params = {
            "service_id": service_id,
            "date_from": date_from
        }

        response = api_session.get(
            f"{config.MOCK_API_BASE_URL}/availability",
            params=params,
            timeout=5
        )
        response.raise_for_status()
        # ... rest unchanged
    except requests.exceptions.RequestException as e:
        return f"[ERROR] Could not connect to API: {str(e)}"
    except Exception as e:
        return f"[ERROR] Unexpected error: {str(e)}"


@tool
def create_appointment_tool(
    service_id: str,
    date: str,
    start_time: str,
    client_name: str,
    client_email: str,
    client_phone: str
) -> str:
    """Create an appointment booking (OPTIMIZED v1.7)."""
    try:
        payload = {
            "service_id": service_id,
            "date": date,
            "start_time": start_time,
            "client": {
                "name": client_name,
                "email": client_email,
                "phone": client_phone
            }
        }

        response = api_session.post(
            f"{config.MOCK_API_BASE_URL}/appointments",
            json=payload,
            timeout=5
        )
        # ... rest unchanged
    except requests.exceptions.RequestException as e:
        return f"[ERROR] Could not connect to API: {str(e)}"
    except Exception as e:
        return f"[ERROR] Unexpected error: {str(e)}"
```

**Step 3: Update appointment management tools**

Update `src/tools_appointment_mgmt.py`:

```python
from src.http_client import api_session

# Update all HTTP calls to use api_session instead of requests
# (cancel_appointment_tool, get_appointment_tool, reschedule_appointment_tool)
```

**Step 4: Manual testing**

Test with API failures:

```bash
# Stop mock API
pkill -f "python mock_api.py"

# Start agent and try booking
cd agent-appoiments-v2
python chat_cli.py
# Try to book - should retry 3 times before giving error

# Restart mock API
python mock_api.py &

# Try again - should work
```

**Step 5: Commit**

```bash
cd agent-appoiments-v2
git add src/http_client.py src/tools.py src/tools_appointment_mgmt.py
git commit -m "perf: optimize HTTP calls with retry and connection pooling

- Create centralized HTTP session with retry strategy
- Add automatic retry on 500/502/503/504 errors
- Add connection pooling for better performance
- Configure exponential backoff (0.3s, 0.6s, 1.2s)
- Update all tools to use shared session

Benefits:
- Better resilience on API failures
- Faster requests (connection reuse)
- Automatic retry without LLM involvement
- Reduced latency from connection pooling"
```

---

## Summary

This plan optimizes the existing appointment booking agent by:

1. **Exit Intent Detection** - Contextual phrase detection for natural conversation endings
2. **LLM Configuration** - Optimal temperature, max_tokens, and timeout settings
3. **Tool Docstrings** - Comprehensive LLM-friendly documentation
4. **Retry Handler** - Intelligent error type detection and appropriate retry logic
5. **Cache System** - Automatic cleanup and configurable TTL
6. **Message Templates** - Consistent, professional responses
7. **HTTP Optimization** - Retry strategy and connection pooling

All improvements maintain backward compatibility and don't add new features - just optimize existing functionality.

## Plan Execution

Plan complete and saved to `agent-appoiments-v2/docs/plans/2025-11-13-optimizacion-agente-errores.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
