#!/usr/bin/env python3
"""
Test escalation message after 2 failed verification attempts.

Verifies that users get helpful guidance about finding their confirmation number
and contacting support when they can't provide it.
"""

from langchain_core.messages import HumanMessage, ToolMessage
from src.agent import retry_handler_node
from src.state import ConversationState

def test_reschedule_escalation():
    """Test escalation message for rescheduling after 2 failures."""
    print("=" * 70)
    print("🔄 TESTING RESCHEDULING ESCALATION MESSAGE")
    print("=" * 70)
    print()

    # Simulate state after 2 failed attempts
    state = {
        "messages": [
            HumanMessage(content="quiero reagendar mi cita"),
            HumanMessage(content="APPT-9999"),  # First wrong attempt
            ToolMessage(content="[ERROR] Appointment APPT-9999 not found.", tool_call_id="1"),
            HumanMessage(content="APPT-8888"),  # Second wrong attempt
            ToolMessage(content="[ERROR] Appointment APPT-8888 not found.", tool_call_id="2"),
        ],
        "current_state": ConversationState.RESCHEDULE_VERIFY,
        "retry_count": {"reschedule": 1},  # Will become 2 after this call
        "collected_data": {},
        "available_slots": []
    }

    # Call retry handler
    result = retry_handler_node(state)

    # Verify escalation happened
    assert result, "❌ No result from retry_handler_node"
    assert "current_state" in result, "❌ State transition missing"
    assert result["current_state"] == ConversationState.POST_ACTION, "❌ Should transition to POST_ACTION"
    assert "messages" in result, "❌ Escalation message missing"

    escalation_message = result["messages"][0].content

    print("📝 Escalation message:")
    print("-" * 70)
    print(escalation_message)
    print("-" * 70)
    print()

    # Verify message contains helpful information
    checks = {
        "Apology present": "apologize" in escalation_message.lower(),
        "Mentions confirmation number": "confirmation number" in escalation_message.lower(),
        "Suggests checking email": "email" in escalation_message.lower(),
        "Mentions Downtown Medical Center": "Downtown Medical Center" in escalation_message,
        "Offers support contact": "support" in escalation_message.lower(),
        "Offers new booking": "new appointment" in escalation_message.lower(),
    }

    print("✅ Message content checks:")
    all_passed = True
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
        if not passed:
            all_passed = False

    print()
    return all_passed


def test_cancel_escalation():
    """Test escalation message for cancellation after 2 failures."""
    print("=" * 70)
    print("❌ TESTING CANCELLATION ESCALATION MESSAGE")
    print("=" * 70)
    print()

    # Simulate state after 2 failed attempts
    state = {
        "messages": [
            HumanMessage(content="quiero cancelar mi cita"),
            HumanMessage(content="APPT-9999"),
            ToolMessage(content="[ERROR] Appointment APPT-9999 not found.", tool_call_id="1"),
            HumanMessage(content="APPT-8888"),
            ToolMessage(content="[ERROR] Appointment APPT-8888 not found.", tool_call_id="2"),
        ],
        "current_state": ConversationState.CANCEL_VERIFY,
        "retry_count": {"cancel": 1},  # Will become 2
        "collected_data": {},
        "available_slots": []
    }

    result = retry_handler_node(state)

    assert result, "❌ No result from retry_handler_node"
    escalation_message = result["messages"][0].content

    print("📝 Escalation message:")
    print("-" * 70)
    print(escalation_message)
    print("-" * 70)
    print()

    # Verify message says "cancel" not "reschedule"
    checks = {
        "Mentions cancellation": "cancel" in escalation_message.lower(),
        "Has helpful guidance": "confirmation number" in escalation_message.lower(),
    }

    print("✅ Message content checks:")
    all_passed = True
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
        if not passed:
            all_passed = False

    print()
    return all_passed


if __name__ == "__main__":
    print()
    reschedule_passed = test_reschedule_escalation()
    cancel_passed = test_cancel_escalation()

    print("=" * 70)
    if reschedule_passed and cancel_passed:
        print("✅ ALL ESCALATION MESSAGE TESTS PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print("✅ Rescheduling escalation message is helpful and clear")
        print("✅ Cancellation escalation message is helpful and clear")
        print("✅ Users will know how to find their confirmation number")
        print("✅ Users will know to contact support if needed")
        exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 70)
        exit(1)
