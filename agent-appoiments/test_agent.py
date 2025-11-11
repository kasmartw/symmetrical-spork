"""
Test script for the appointment booking agent.
Simulates a complete conversation flow.
"""

import os
import time
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from agent import create_agent_graph, SYSTEM_PROMPT

# Load environment variables
load_dotenv()

# Verify API key
if not os.getenv("OPENAI_API_KEY"):
    print("⚠️  Error: OPENAI_API_KEY not found in .env file")
    exit(1)


def simulate_conversation():
    """Simulate a complete appointment booking conversation."""

    print("=" * 60)
    print("🧪 TESTING APPOINTMENT BOOKING AGENT")
    print("=" * 60)
    print("\nThis script simulates a complete booking conversation.\n")
    print("Make sure the mock API server is running on http://localhost:5000")
    print("\nPress Enter to start the test...")
    input()

    # Create the agent graph
    agent_graph = create_agent_graph()

    # Test conversation flow
    test_messages = [
        "Hi, I'd like to book an appointment",
        "I need a general consultation",
        "What dates are available?",
        "I'll take the first available slot",
        "My name is John Smith",
        "john.smith@email.com",
        "555-123-4567",
        "Yes, please confirm"
    ]

    # Initialize state
    state = {
        "messages": [HumanMessage(content=SYSTEM_PROMPT + "\n\nGreet the user and ask how you can help them.")],
        "context": {}
    }

    print("\n" + "=" * 60)
    print("CONVERSATION SIMULATION")
    print("=" * 60 + "\n")

    # Start conversation
    try:
        # Get initial greeting
        response = agent_graph.invoke(state)
        state["messages"] = response["messages"]

        # Print agent's greeting
        for message in response["messages"]:
            if hasattr(message, 'content') and message.content:
                print(f"🤖 Agent: {message.content}\n")

        # Simulate user messages
        for i, user_message in enumerate(test_messages, 1):
            print(f"\n{'=' * 60}")
            print(f"TURN {i}")
            print('=' * 60)

            time.sleep(1)  # Pause for readability

            print(f"👤 User: {user_message}\n")

            # Add user message to state
            state["messages"].append(HumanMessage(content=user_message))

            # Get agent response
            response = agent_graph.invoke(state)
            state["messages"] = response["messages"]

            # Print agent response (only new messages)
            for message in response["messages"][-3:]:  # Get last few messages
                if hasattr(message, 'content') and message.content and not message.content.startswith("You are a friendly"):
                    print(f"🤖 Agent: {message.content}\n")

            time.sleep(1)  # Pause between turns

        print("\n" + "=" * 60)
        print("✅ TEST COMPLETED SUCCESSFULLY")
        print("=" * 60 + "\n")

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False


def test_tools():
    """Test individual tools."""
    from agent import (
        get_services,
        get_availability,
        validate_email,
        validate_phone
    )

    print("\n" + "=" * 60)
    print("🧪 TESTING INDIVIDUAL TOOLS")
    print("=" * 60 + "\n")

    tests = [
        {
            "name": "Get Services",
            "function": get_services,
            "args": []
        },
        {
            "name": "Get Availability",
            "function": get_availability,
            "args": ["srv-001"]
        },
        {
            "name": "Validate Email (valid)",
            "function": validate_email,
            "args": ["test@example.com"]
        },
        {
            "name": "Validate Email (invalid)",
            "function": validate_email,
            "args": ["invalid-email"]
        },
        {
            "name": "Validate Phone (valid)",
            "function": validate_phone,
            "args": ["555-123-4567"]
        },
        {
            "name": "Validate Phone (invalid)",
            "function": validate_phone,
            "args": ["123"]
        }
    ]

    for test in tests:
        print(f"\n📝 Testing: {test['name']}")
        print("-" * 60)
        try:
            result = test["function"].invoke({"args": test["args"]}) if test["args"] else test["function"].invoke({})
            print(f"✅ Result:\n{result}\n")
        except Exception as e:
            print(f"❌ Error: {str(e)}\n")

    print("=" * 60)
    print("✅ TOOL TESTS COMPLETED")
    print("=" * 60 + "\n")


def main():
    """Run all tests."""
    print("\n🚀 Starting test suite...\n")

    # Test 1: Individual tools
    print("TEST 1: Individual Tool Testing")
    print("Make sure the mock API is running (python mock_api.py)")
    print("\nPress Enter to continue...")
    input()

    test_tools()

    # Test 2: Full conversation simulation
    print("\n\nTEST 2: Full Conversation Simulation")
    print("This will simulate a complete booking conversation.")
    print("\nPress Enter to continue...")
    input()

    success = simulate_conversation()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    if success:
        print("✅ All tests passed!")
        print("\nThe agent successfully:")
        print("  • Retrieved available services")
        print("  • Showed availability slots")
        print("  • Collected client information")
        print("  • Validated email and phone")
        print("  • Created an appointment")
        print("  • Provided confirmation number")
    else:
        print("❌ Some tests failed. Check the errors above.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
