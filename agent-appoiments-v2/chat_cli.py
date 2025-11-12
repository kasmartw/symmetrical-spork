#!/usr/bin/env python3
"""
Interactive CLI for testing the appointment booking agent.

This provides a real chat interface where you can interact with the agent
just like a user would.
"""
import os
import sys
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from src.agent import create_graph
from src.state import ConversationState

# Load environment
load_dotenv()

def print_banner():
    """Print welcome banner."""
    print("\n" + "="*70)
    print("🤖  APPOINTMENT BOOKING AGENT - Interactive Chat CLI")
    print("="*70)
    print("\nCommands:")
    print("  /quit or /exit  - Exit the chat")
    print("  /state          - Show current state")
    print("  /data           - Show collected data")
    print("  /clear          - Start new conversation")
    print("  /help           - Show this help")
    print("\n" + "="*70 + "\n")

def print_state(state):
    """Print current state information."""
    print("\n" + "-"*70)
    print(f"📍 Current State: {state['current_state'].value}")
    print(f"💾 Collected Data: {state['collected_data']}")
    print(f"📝 Message Count: {len(state['messages'])}")
    print("-"*70 + "\n")

def format_ai_message(message):
    """Format AI message for display."""
    content = message.content

    # Handle tool calls
    if hasattr(message, 'tool_calls') and message.tool_calls:
        print("\n🔧 [Agent is using tools...]")
        for tool_call in message.tool_calls:
            print(f"   Calling: {tool_call.get('name', 'unknown')}")
        print()

    return content

def main():
    """Run the interactive chat CLI."""

    # Check for API key
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "test-key":
        print("\n❌ ERROR: OPENAI_API_KEY not configured!")
        print("\nPlease set your OpenAI API key:")
        print("1. Copy .env.example to .env")
        print("2. Edit .env and add: OPENAI_API_KEY=your-actual-key")
        print("3. Run this script again\n")
        sys.exit(1)

    print_banner()

    # Create graph
    print("🔄 Initializing agent...")
    try:
        graph = create_graph()
        print("✅ Agent ready!\n")
    except Exception as e:
        print(f"❌ Error creating graph: {e}")
        sys.exit(1)

    # Initialize state
    thread_id = "cli-session-001"
    config = {"configurable": {"thread_id": thread_id}}

    state = {
        "messages": [],
        "current_state": ConversationState.COLLECT_SERVICE,
        "collected_data": {},
        "available_slots": []
    }

    print("💬 Start chatting! (Type /help for commands)\n")

    # Chat loop
    conversation_active = True

    while conversation_active:
        try:
            # Get user input
            user_input = input("👤 You: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith('/'):
                command = user_input.lower()

                if command in ['/quit', '/exit']:
                    print("\n👋 Goodbye! Thanks for chatting.\n")
                    conversation_active = False
                    continue

                elif command == '/state':
                    print_state(state)
                    continue

                elif command == '/data':
                    print(f"\n💾 Collected Data:")
                    for key, value in state['collected_data'].items():
                        print(f"   {key}: {value}")
                    print()
                    continue

                elif command == '/clear':
                    state = {
                        "messages": [],
                        "current_state": ConversationState.COLLECT_SERVICE,
                        "collected_data": {},
                        "available_slots": []
                    }
                    print("\n🔄 Conversation cleared! Starting fresh.\n")
                    continue

                elif command == '/help':
                    print_banner()
                    continue

                else:
                    print(f"❓ Unknown command: {user_input}")
                    print("Type /help to see available commands\n")
                    continue

            # Add user message to state
            state["messages"].append(HumanMessage(content=user_input))

            # Invoke agent
            print("🤖 Agent: ", end="", flush=True)

            try:
                result = graph.invoke(state, config=config)

                # Get the last AI message(s)
                new_messages = result["messages"][len(state["messages"]):]

                # Display all new messages
                for msg in new_messages:
                    if hasattr(msg, 'content'):
                        # Check if it's a tool message
                        if msg.__class__.__name__ == 'ToolMessage':
                            print(f"\n   🔧 Tool result: {msg.content}")
                        else:
                            # Regular AI message
                            formatted = format_ai_message(msg)
                            if formatted:
                                print(formatted)

                print()  # New line after response

                # Update state for next iteration
                state = result

            except Exception as e:
                print(f"\n❌ Error during conversation: {e}")
                print("Type /clear to start a new conversation\n")

        except KeyboardInterrupt:
            print("\n\n👋 Chat interrupted. Goodbye!\n")
            conversation_active = False

        except EOFError:
            print("\n\n👋 Chat ended. Goodbye!\n")
            conversation_active = False

        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            print("Type /quit to exit or /clear to restart\n")

if __name__ == "__main__":
    main()
