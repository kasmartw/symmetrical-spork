"""Diagnostic test para trazar el flujo del confirmation number.

Instrumenta cada capa para ver dónde se pierde el confirmation number.
"""
import os
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage
from src.agent import create_graph

# Create graph instance
graph = create_graph()

def get_future_date(days_ahead=7):
    """Generate a future date string in YYYY-MM-DD format."""
    future_date = datetime.now() + timedelta(days=days_ahead)
    return future_date.strftime("%Y-%m-%d")

def test_confirmation_flow():
    """Test mínimo para diagnosticar el flujo del confirmation number."""

    print("\n" + "="*80)
    print("DIAGNOSTIC TEST: Confirmation Number Flow")
    print("="*80)

    config = {"configurable": {"thread_id": "diagnosis-test"}}

    messages = [
        "Hola, quiero agendar una cita",
        "General Consultation",
        "morning",
        get_future_date(4),
        "09:00",
        "Juan Pérez",
        "juan.perez@email.com",
        "+1234567890",
        "sí, confirmar"
    ]

    for i, msg in enumerate(messages, 1):
        print(f"\n{'─'*80}")
        print(f"STEP {i}: User sends: {msg}")
        print(f"{'─'*80}")

        result = graph.invoke(
            {"messages": [HumanMessage(content=msg)]},
            config=config
        )

        # Analizar resultado
        last_message = result["messages"][-1]
        current_state = result.get("current_state")

        print(f"\n📊 Current State: {current_state}")
        print(f"\n💬 Agent Response:")
        print(f"   {last_message.content}")

        # Buscar confirmation number en el mensaje
        import re
        conf_match = re.search(r'APPT-\d+', last_message.content, re.IGNORECASE)

        if conf_match:
            print(f"\n✅ FOUND CONFIRMATION NUMBER: {conf_match.group()}")
        else:
            print(f"\n❌ NO CONFIRMATION NUMBER in agent response")

        # Si hay tool_calls, mostrarlos
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            print(f"\n🔧 Tool Calls in this step:")
            for tc in last_message.tool_calls:
                print(f"   - {tc.get('name', 'unknown')}: {tc.get('args', {})}")

        # Buscar ToolMessage en los mensajes (resultado de tools)
        for msg in reversed(result["messages"][-10:]):  # Últimos 10 mensajes
            if hasattr(msg, 'type') and msg.type == 'tool':
                print(f"\n🔨 Tool Result Found:")
                print(f"   Content: {msg.content[:200]}...")  # Primeros 200 chars

                # Buscar confirmation en tool result
                tool_conf_match = re.search(r'APPT-\d+', msg.content, re.IGNORECASE)
                if tool_conf_match:
                    print(f"   ✅ CONFIRMATION IN TOOL RESULT: {tool_conf_match.group()}")
                else:
                    print(f"   ⚠️  No confirmation number in this tool result")

    print(f"\n{'='*80}")
    print("FINAL DIAGNOSIS")
    print(f"{'='*80}")

    final_message = result["messages"][-1].content
    final_conf = re.search(r'APPT-\d+', final_message, re.IGNORECASE)

    if final_conf:
        print(f"✅ SUCCESS: Confirmation number presente: {final_conf.group()}")
        return True
    else:
        print(f"❌ FAILURE: No confirmation number in final message")
        print(f"\nFinal message content:")
        print(f"{final_message}")

        # Buscar en tool messages
        print(f"\n🔍 Searching tool messages for confirmation number...")
        for msg in reversed(result["messages"]):
            if hasattr(msg, 'type') and msg.type == 'tool':
                tool_conf = re.search(r'APPT-\d+', msg.content, re.IGNORECASE)
                if tool_conf:
                    print(f"\n⚠️  FOUND IN TOOL RESULT: {tool_conf.group()}")
                    print(f"   Tool content: {msg.content[:300]}")
                    print(f"\n❗ DIAGNOSIS: Tool returned confirmation but LLM didn't include it in response")
                    return False

        print(f"\n❗ DIAGNOSIS: Confirmation number not found anywhere in conversation")
        return False

if __name__ == "__main__":
    success = test_confirmation_flow()
    exit(0 if success else 1)
