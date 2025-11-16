"""FastAPI streaming API server for appointment booking agent (v1.10 OPTIMIZED).

This server provides a thin API layer that proxies to the LangGraph server
with conditional streaming support based on client channel.

Architecture:
User → FastAPI (this file) → LangGraph RemoteGraph (streaming/blocking) → Agent

v1.10 Features:
- Conditional streaming: WhatsApp (blocking) vs Web (SSE streaming)
- Channel detection via X-Channel header, User-Agent, or query param
- Latency tracking and logging
- 91% token reduction (1,100 → 97 tokens)
- Sliding window message management
- Automatic caching optimization

Performance:
- Perceived latency (Web/SSE): <1s (first tokens appear immediately)
- Real latency: 14-16s (optimized with gpt-4o-mini + max_tokens=200)
- WhatsApp: Complete response (blocking)

Usage:
1. Start LangGraph server: langgraph dev
2. Start this API: uvicorn api_server:app --port 8000
3. Send requests: POST /chat with JSON body + optional X-Channel header
"""
import os
import json
import time
import logging
from typing import Optional
from dotenv import load_dotenv

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langgraph_sdk import get_client
from src.channel_detector import detect_channel, should_stream as should_stream_for_channel

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Appointment Booking API",
    description="Conditional streaming API for appointment booking agent (v1.10)",
    version="1.10.0"
)

# CORS middleware (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LangGraph client (connects to langgraph dev server)
# Note: langgraph dev runs on port 2024 by default
LANGGRAPH_URL = os.getenv("LANGGRAPH_URL", "http://localhost:2024")
client = get_client(url=LANGGRAPH_URL)


# Request/Response models
class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    thread_id: Optional[str] = None
    org_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    langgraph_url: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "langgraph_url": LANGGRAPH_URL
    }


@app.post("/chat")
async def chat(request: ChatRequest, req: Request):
    """
    Chat endpoint with conditional streaming (v1.10 OPTIMIZED).

    Streaming behavior:
    - Web clients: SSE streaming (immediate response, <1s perceived latency)
    - WhatsApp: Blocking response (complete message, 14-16s)

    Detection: X-Channel header, User-Agent, or source query param

    Args:
        request: ChatRequest with message, optional thread_id and org_id
        req: FastAPI Request for header inspection

    Returns:
        StreamingResponse (Web) or JSONResponse (WhatsApp)

    Examples:
        # Web (streaming)
        POST /chat
        X-Channel: web
        {"message": "Hello", "thread_id": "user-123"}

        # WhatsApp (blocking)
        POST /chat
        X-Channel: whatsapp
        {"message": "Hola", "thread_id": "user-456"}
    """
    request_start = time.perf_counter()

    # Generate thread_id if not provided
    thread_id = request.thread_id or f"thread-{os.urandom(8).hex()}"
    org_id = request.org_id or "default-org"

    # v1.10: Detect client channel
    headers_dict = dict(req.headers)
    query_params = dict(req.query_params) if req.query_params else {}
    channel = detect_channel(headers_dict, query_params)
    enable_streaming = should_stream_for_channel(channel)

    logger.info(
        f"Chat request - thread={thread_id}, org={org_id}, "
        f"channel={channel.value}, streaming={enable_streaming}"
    )

    try:
        # Route based on channel
        if enable_streaming:
            # WEB: Use SSE streaming
            async def generate_stream():
                first_token_time = None
                total_tokens = 0

                try:
                    async for chunk in client.runs.stream(
                        thread_id=thread_id,
                        assistant_id="appointment_agent",
                        input={"messages": [{"role": "user", "content": request.message}]},
                        stream_mode="messages",
                        config={
                            "configurable": {
                                "org_id": org_id
                            }
                        }
                    ):
                        if chunk.event == "messages/partial":
                            # Stream tokens as they arrive
                            if chunk.data and len(chunk.data) > 0:
                                message = chunk.data[0]
                                content = message.get("content", "")
                                if content:
                                    if first_token_time is None:
                                        first_token_time = time.perf_counter()
                                        ttft_ms = (first_token_time - request_start) * 1000
                                        logger.info(f"TTFT: {ttft_ms:.2f}ms")

                                    total_tokens += len(content.split())
                                    yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

                        elif chunk.event == "messages/complete":
                            # Final message
                            if chunk.data and len(chunk.data) > 0:
                                message = chunk.data[0]
                                content = message.get("content", "")
                                yield f"data: {json.dumps({'type': 'message', 'content': content, 'channel': channel.value})}\n\n"

                    # Track total latency
                    total_latency_ms = (time.perf_counter() - request_start) * 1000
                    logger.info(f"Stream complete - {total_latency_ms:.2f}ms total, {total_tokens} tokens")

                    yield f"data: {json.dumps({'type': 'done'})}\n\n"

                except Exception as e:
                    logger.error(f"Streaming error: {str(e)}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )

        else:
            # WHATSAPP: Blocking response (wait for complete message)
            result = await client.runs.create(
                thread_id=thread_id,
                assistant_id="appointment_agent",
                input={"messages": [{"role": "user", "content": request.message}]},
                config={
                    "configurable": {
                        "org_id": org_id
                    }
                }
            )

            # Wait for completion
            await client.runs.join(thread_id, result["run_id"])

            # Get final state
            state = await client.threads.get_state(thread_id)

            # Extract last AI message
            messages = state.get("values", {}).get("messages", [])
            last_message = ""
            for msg in reversed(messages):
                if msg.get("type") == "ai":
                    last_message = msg.get("content", "")
                    break

            # Track latency
            total_latency_ms = (time.perf_counter() - request_start) * 1000
            logger.info(f"Blocking response complete - {total_latency_ms:.2f}ms")

            return JSONResponse({
                "message": last_message,
                "thread_id": thread_id,
                "channel": channel.value,
                "streaming": False,
                "latency_ms": round(total_latency_ms, 2)
            })

    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/blocking")
async def chat_blocking(request: ChatRequest):
    """
    Non-streaming chat endpoint (for clients that don't support SSE).

    Args:
        request: ChatRequest with message, optional thread_id and org_id

    Returns:
        JSON response with complete message

    Note: This endpoint has higher perceived latency (14-16s) compared to
    streaming endpoint (<1s). Use streaming endpoint when possible.
    """
    # Generate thread_id if not provided
    thread_id = request.thread_id or f"thread-{os.urandom(8).hex()}"
    org_id = request.org_id or "default-org"

    try:
        # Invoke agent (blocking)
        result = await client.runs.create(
            thread_id=thread_id,
            assistant_id="appointment_agent",
            input={"messages": [{"role": "user", "content": request.message}]},
            config={
                "configurable": {
                    "org_id": org_id
                }
            }
        )

        # Wait for completion
        await client.runs.join(thread_id, result["run_id"])

        # Get final state
        state = await client.threads.get_state(thread_id)

        # Extract last assistant message
        messages = state.get("values", {}).get("messages", [])
        if messages:
            last_message = messages[-1]
            return {
                "message": last_message.get("content", ""),
                "thread_id": thread_id
            }
        else:
            return {
                "message": "No response generated",
                "thread_id": thread_id
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/threads/{thread_id}/history")
async def get_thread_history(thread_id: str):
    """
    Get conversation history for a thread.

    Args:
        thread_id: Thread identifier

    Returns:
        JSON with message history
    """
    try:
        state = await client.threads.get_state(thread_id)
        messages = state.get("values", {}).get("messages", [])

        return {
            "thread_id": thread_id,
            "messages": messages,
            "current_state": state.get("values", {}).get("current_state", "unknown")
        }

    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Thread not found: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    # Run server
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
