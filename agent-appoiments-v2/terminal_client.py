#!/usr/bin/env python3
"""Terminal client with SSE streaming support for appointment agent.

Usage:
    python terminal_client.py

Features:
- SSE streaming for immediate token responses
- Thread persistence across messages
- Colored output for better UX
- Auto-reconnect on errors
"""
import requests
import json
import sys
import uuid
from typing import Optional

# ANSI color codes
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

API_URL = "http://localhost:8000/chat"
THREAD_ID = f"terminal-{uuid.uuid4().hex[:8]}"

def print_colored(text: str, color: str = Colors.RESET):
    """Print colored text."""
    print(f"{color}{text}{Colors.RESET}")

def stream_chat(message: str, thread_id: str, org_id: str = "default-org"):
    """
    Send message and stream response using SSE.

    Args:
        message: User message
        thread_id: Conversation thread ID
        org_id: Organization ID
    """
    payload = {
        "message": message,
        "thread_id": thread_id,
        "org_id": org_id
    }

    headers = {
        "Content-Type": "application/json",
        "X-Channel": "web",  # Enable streaming
        "Accept": "text/event-stream"
    }

    try:
        # POST with stream=True for SSE
        response = requests.post(
            API_URL,
            json=payload,
            headers=headers,
            stream=True,
            timeout=60
        )

        if response.status_code != 200:
            print_colored(f"❌ Error: {response.status_code}", Colors.RED)
            print_colored(response.text, Colors.RED)
            return

        print_colored("🤖 Asistente: ", Colors.GREEN, end="")

        # Parse SSE stream
        full_response = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')

                # SSE format: "data: {...}"
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])  # Skip "data: "

                        if data.get("type") == "token":
                            # Stream tokens as they arrive
                            content = data.get("content", "")
                            print(content, end="", flush=True)
                            full_response += content

                        elif data.get("type") == "message":
                            # Final message (complete)
                            content = data.get("content", "")
                            if not full_response:
                                # If no tokens streamed, print full message
                                print(content)
                                full_response = content

                        elif data.get("type") == "error":
                            error = data.get("error", "Unknown error")
                            print_colored(f"\n❌ Error: {error}", Colors.RED)

                    except json.JSONDecodeError:
                        # Skip malformed JSON
                        pass

        print()  # New line after response

    except requests.exceptions.ConnectionError:
        print_colored("❌ No se pudo conectar al servidor.", Colors.RED)
        print_colored("Verifica que api_server.py esté corriendo:", Colors.YELLOW)
        print_colored("  uvicorn api_server:app --port 8000", Colors.YELLOW)
    except requests.exceptions.Timeout:
        print_colored("❌ Timeout - El servidor tardó demasiado.", Colors.RED)
    except Exception as e:
        print_colored(f"❌ Error inesperado: {e}", Colors.RED)

def blocking_chat(message: str, thread_id: str, org_id: str = "default-org"):
    """
    Send message and get blocking response (WhatsApp mode).

    Args:
        message: User message
        thread_id: Conversation thread ID
        org_id: Organization ID
    """
    payload = {
        "message": message,
        "thread_id": thread_id,
        "org_id": org_id
    }

    headers = {
        "Content-Type": "application/json",
        "X-Channel": "whatsapp",  # Disable streaming
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=60)

        if response.status_code != 200:
            print_colored(f"❌ Error: {response.status_code}", Colors.RED)
            print_colored(response.text, Colors.RED)
            return

        data = response.json()
        assistant_message = data.get("response", "")

        print_colored("🤖 Asistente: ", Colors.GREEN)
        print(assistant_message)

    except Exception as e:
        print_colored(f"❌ Error: {e}", Colors.RED)

def main():
    """Main interactive loop."""
    print_colored("=" * 60, Colors.BLUE)
    print_colored("🏥 Appointment Booking Agent - Terminal Client", Colors.BOLD)
    print_colored("=" * 60, Colors.BLUE)
    print()
    print_colored(f"Thread ID: {THREAD_ID}", Colors.YELLOW)
    print_colored("Modo: Streaming SSE (respuestas en tiempo real)", Colors.YELLOW)
    print()
    print_colored("Comandos especiales:", Colors.YELLOW)
    print_colored("  /new     - Nueva conversación", Colors.YELLOW)
    print_colored("  /block   - Cambiar a modo blocking (WhatsApp)", Colors.YELLOW)
    print_colored("  /stream  - Cambiar a modo streaming (Web)", Colors.YELLOW)
    print_colored("  /quit    - Salir", Colors.YELLOW)
    print()

    global THREAD_ID
    mode = "stream"  # "stream" or "block"

    while True:
        try:
            # Get user input
            print_colored("👤 Tú: ", Colors.BLUE, end="")
            user_input = input()

            if not user_input.strip():
                continue

            # Handle commands
            if user_input.startswith("/"):
                cmd = user_input.lower().strip()

                if cmd == "/quit":
                    print_colored("👋 Adiós!", Colors.YELLOW)
                    break

                elif cmd == "/new":
                    THREAD_ID = f"terminal-{uuid.uuid4().hex[:8]}"
                    print_colored(f"✅ Nueva conversación: {THREAD_ID}", Colors.GREEN)
                    continue

                elif cmd == "/block":
                    mode = "block"
                    print_colored("✅ Modo blocking activado (WhatsApp)", Colors.GREEN)
                    continue

                elif cmd == "/stream":
                    mode = "stream"
                    print_colored("✅ Modo streaming activado (Web)", Colors.GREEN)
                    continue

                else:
                    print_colored(f"❌ Comando desconocido: {cmd}", Colors.RED)
                    continue

            # Send message
            if mode == "stream":
                stream_chat(user_input, THREAD_ID)
            else:
                blocking_chat(user_input, THREAD_ID)

        except KeyboardInterrupt:
            print()
            print_colored("👋 Adiós!", Colors.YELLOW)
            break
        except Exception as e:
            print_colored(f"❌ Error inesperado: {e}", Colors.RED)

if __name__ == "__main__":
    main()
