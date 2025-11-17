#!/usr/bin/env python3
"""Quick test for streaming API."""
import requests
import json

API_URL = "http://localhost:8000/chat"

# Test message
payload = {
    "message": "Hola, quiero agendar una cita",
    "thread_id": "test-123"
}

headers = {
    "Content-Type": "application/json",
    "X-Channel": "web",  # Enable streaming
}

print("🔍 Testing streaming API...")
print(f"📡 Sending: {payload['message']}")
print()

try:
    response = requests.post(
        API_URL,
        json=payload,
        headers=headers,
        stream=True,
        timeout=30
    )

    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        exit(1)

    print("🤖 Respuesta: ", end="", flush=True)

    # Parse SSE stream
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')

            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])

                    if data.get("type") == "token":
                        content = data.get("content", "")
                        print(content, end="", flush=True)

                    elif data.get("type") == "message":
                        content = data.get("content", "")
                        print(content)

                    elif data.get("type") == "error":
                        error = data.get("error", "")
                        print(f"\n❌ Error: {error}")

                except json.JSONDecodeError:
                    pass

    print()
    print()
    print("✅ Streaming funcionó correctamente")

except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
