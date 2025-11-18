"""Simple FastAPI server for testing the appointment agent.

This server works directly with the compiled graph (no LangGraph SDK).
Perfect for REST Client testing.

Usage:
    python simple_api.py

Then use REST Client:
    POST http://localhost:8000/chat
    {"message": "hola", "thread_id": "test-123"}
"""
import os
import uvicorn
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from src.agent import create_graph

# Load environment
load_dotenv()

# Create app
app = FastAPI(title="Simple Appointment Agent API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compile graph once at startup
graph = create_graph()


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    thread_id: Optional[str] = "default-thread"


class ChatResponse(BaseModel):
    """Chat response model."""
    message: str
    thread_id: str
    state: Optional[str] = None


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "service": "simple-appointment-api"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the appointment agent.

    Args:
        request: ChatRequest with message and optional thread_id

    Returns:
        ChatResponse with agent's reply

    Example:
        POST /chat
        {"message": "Hola, quiero una cita", "thread_id": "user-123"}
    """
    try:
        # Configure with thread_id for persistence
        config = {
            "configurable": {
                "thread_id": request.thread_id
            }
        }

        # Invoke graph
        result = graph.invoke(
            {"messages": [HumanMessage(content=request.message)]},
            config=config
        )

        # Extract last AI message
        messages = result.get("messages", [])
        if not messages:
            return ChatResponse(
                message="No response generated",
                thread_id=request.thread_id
            )

        last_message = messages[-1]
        response_text = last_message.content if hasattr(last_message, 'content') else str(last_message)

        # Get current state
        current_state = str(result.get("current_state", ""))

        return ChatResponse(
            message=response_text,
            thread_id=request.thread_id,
            state=current_state
        )

    except Exception as e:
        return ChatResponse(
            message=f"Error: {str(e)}",
            thread_id=request.thread_id,
            state="error"
        )


@app.get("/threads/{thread_id}/state")
async def get_thread_state(thread_id: str):
    """
    Get current state of a thread.

    Args:
        thread_id: Thread identifier

    Returns:
        Current state and message count
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = graph.get_state(config)

        return {
            "thread_id": thread_id,
            "current_state": str(state.values.get("current_state", "unknown")),
            "message_count": len(state.values.get("messages", [])),
            "collected_data": state.values.get("collected_data", {})
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    print("🚀 Starting Simple Appointment Agent API...")
    print("📝 Endpoints:")
    print("   GET  /health")
    print("   POST /chat")
    print("   GET  /threads/{thread_id}/state")
    print("\n💡 Test with:")
    print('   curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d \'{"message": "hola"}\'')
    print("\n")

    uvicorn.run(
        "simple_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
