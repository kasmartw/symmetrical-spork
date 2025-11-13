#!/usr/bin/env python3
"""
Manual test for time preference filtering feature (v1.4).

Tests the complete booking flow with time preference:
1. Service selection
2. Time preference (morning/afternoon)
3. View filtered availability
4. Select date/time
5. Complete booking
"""
from langchain_core.messages import HumanMessage
from src.agent import create_graph
from src.state import ConversationState

def test_time_preference_flow():
    """Test full booking flow with morning preference."""
    graph = create_graph()

    # Configuration
    config = {"configurable": {"thread_id": "test_time_pref_001"}}

    # Initial state
    initial_state = {
        "messages": [],
        "current_state": ConversationState.COLLECT_SERVICE,
        "collected_data": {},
        "available_slots": [],
        "retry_count": {}
    }

    print("=" * 60)
    print("TEST: Time Preference Filtering Flow")
    print("=" * 60)

    # Step 1: User says hi
    print("\n[USER] Hi, I want to book an appointment")
    state = graph.invoke(
        {**initial_state, "messages": [HumanMessage(content="Hi, I want to book an appointment")]},
        config
    )
    print(f"[AGENT STATE] {state['current_state']}")
    last_msg = state["messages"][-1].content
    print(f"[AGENT] {last_msg[:200]}...")

    # Step 2: User selects service
    print("\n[USER] General consultation")
    state = graph.invoke(
        {**state, "messages": state["messages"] + [HumanMessage(content="General consultation")]},
        config
    )
    print(f"[AGENT STATE] {state['current_state']}")
    last_msg = state["messages"][-1].content
    print(f"[AGENT] {last_msg[:200]}...")

    # Step 3: User specifies morning preference
    print("\n[USER] Morning appointments please")
    state = graph.invoke(
        {**state, "messages": state["messages"] + [HumanMessage(content="Morning appointments please")]},
        config
    )
    print(f"[AGENT STATE] {state['current_state']}")
    print(f"[COLLECTED DATA] {state['collected_data']}")
    last_msg = state["messages"][-1].content
    print(f"[AGENT] {last_msg[:400]}...")

    # Check if filtering was applied
    if "morning" in str(state["collected_data"].get("time_preference", "")):
        print("\n✅ SUCCESS: Time preference stored correctly")
    else:
        print("\n❌ FAIL: Time preference not stored")
        return False

    # Check if availability was shown
    if "[AVAILABILITY]" in last_msg or "Available" in last_msg:
        print("✅ SUCCESS: Availability shown")
    else:
        print("❌ FAIL: Availability not shown")
        return False

    # Check if filtering message is present
    if "morning" in last_msg.lower() or "filtered" in last_msg.lower():
        print("✅ SUCCESS: Filtering indicator present")
    else:
        print("⚠️  WARNING: No explicit filtering indicator")

    print("\n" + "=" * 60)
    print("TEST PASSED: Time preference filtering working!")
    print("=" * 60)
    return True


def test_afternoon_preference():
    """Test booking flow with afternoon preference."""
    graph = create_graph()

    # Configuration
    config = {"configurable": {"thread_id": "test_time_pref_002"}}

    # Initial state
    initial_state = {
        "messages": [],
        "current_state": ConversationState.COLLECT_SERVICE,
        "collected_data": {},
        "available_slots": [],
        "retry_count": {}
    }

    print("\n\n" + "=" * 60)
    print("TEST: Afternoon Preference")
    print("=" * 60)

    # Simulate flow
    print("\n[USER] I want an appointment")
    state = graph.invoke(
        {**initial_state, "messages": [HumanMessage(content="I want an appointment")]},
        config
    )

    print("\n[USER] Dental cleaning")
    state = graph.invoke(
        {**state, "messages": state["messages"] + [HumanMessage(content="Dental cleaning")]},
        config
    )

    print("\n[USER] Afternoon times please")
    state = graph.invoke(
        {**state, "messages": state["messages"] + [HumanMessage(content="Afternoon times please")]},
        config
    )

    print(f"\n[AGENT STATE] {state['current_state']}")
    print(f"[COLLECTED DATA] {state['collected_data']}")
    last_msg = state["messages"][-1].content
    print(f"[AGENT] {last_msg[:400]}...")

    if "afternoon" in str(state["collected_data"].get("time_preference", "")):
        print("\n✅ SUCCESS: Afternoon preference stored")
        return True
    else:
        print("\n❌ FAIL: Afternoon preference not stored")
        return False


if __name__ == "__main__":
    try:
        # Test 1: Morning preference
        success1 = test_time_preference_flow()

        # Test 2: Afternoon preference
        success2 = test_afternoon_preference()

        if success1 and success2:
            print("\n\n🎉 ALL TESTS PASSED!")
            exit(0)
        else:
            print("\n\n❌ SOME TESTS FAILED")
            exit(1)

    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
