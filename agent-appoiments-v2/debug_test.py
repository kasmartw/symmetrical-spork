"""Debug script to test the optimized prompt."""
import os
from langchain_core.messages import HumanMessage
from src.agent import create_graph
from dotenv import load_dotenv

load_dotenv()

def test_simple_flow():
    """Test a simple booking flow with verbose output."""
    graph = create_graph()
    config = {"configurable": {"thread_id": "debug-test-001"}}

    messages = [
        "Hello, I need to book an appointment",
        "General Consultation",
    ]

    print("="*80)
    print("DEBUGGING OPTIMIZED PROMPT")
    print("="*80)

    for i, msg in enumerate(messages, 1):
        print(f"\n--- USER MESSAGE {i} ---")
        print(f"User: {msg}")

        try:
            result = graph.invoke(
                {"messages": [HumanMessage(content=msg)]},
                config=config,
            )

            last_message = result["messages"][-1]
            print(f"\nAgent: {last_message.content[:500]}")

            # Check for tool calls
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                print(f"\nTool calls: {len(last_message.tool_calls)}")
                for tc in last_message.tool_calls:
                    print(f"  - {tc['name']}")

            print(f"\nCurrent state: {result.get('current_state', 'Unknown')}")
            print(f"Messages in conversation: {len(result['messages'])}")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            break

    print("\n" + "="*80)
    print("DEBUG COMPLETE")
    print("="*80)

if __name__ == "__main__":
    test_simple_flow()
