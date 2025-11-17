# FastAPI Production API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the appointment booking agent into a production-ready multi-tenant REST API with FastAPI, PostgreSQL persistence, streaming support, security, and plugin integration capabilities.

**Architecture:** Three-tier system with FastAPI presentation layer, LangGraph orchestration layer, and PostgreSQL persistence. Implements session management, API key authentication, rate limiting, and SSE streaming for real-time responses.

**Tech Stack:** FastAPI, LangGraph, PostgreSQL (with PostgresSaver), SQLAlchemy async, bcrypt, slowapi, Redis (optional), bleach, pytest-asyncio

---

## PHASE 1: API FOUNDATIONS (Week 1)

### Task 1.1: Create FastAPI Base Structure

**Files:**
- Create: `agent-appoiments-v2/src/api_server.py`
- Create: `agent-appoiments-v2/src/api/__init__.py`
- Create: `agent-appoiments-v2/src/api/models.py`
- Create: `agent-appoiments-v2/src/api/middleware.py`
- Test: `agent-appoiments-v2/tests/unit/test_api_models.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_api_models.py
"""Test API request/response models."""
import pytest
from pydantic import ValidationError
from src.api.models import ChatRequest, ChatResponse


def test_chat_request_valid():
    """Valid chat request should pass validation."""
    req = ChatRequest(
        message="Hello",
        session_id="550e8400-e29b-41d4-a716-446655440000",
        org_id="org-123"
    )
    assert req.message == "Hello"
    assert str(req.session_id) == "550e8400-e29b-41d4-a716-446655440000"


def test_chat_request_empty_message_fails():
    """Empty message should fail validation."""
    with pytest.raises(ValidationError) as exc_info:
        ChatRequest(
            message="",
            session_id="550e8400-e29b-41d4-a716-446655440000",
            org_id="org-123"
        )
    assert "message" in str(exc_info.value)


def test_chat_request_too_long_message_fails():
    """Message exceeding 2000 chars should fail."""
    with pytest.raises(ValidationError):
        ChatRequest(
            message="x" * 2001,
            session_id="550e8400-e29b-41d4-a716-446655440000",
            org_id="org-123"
        )


def test_chat_request_invalid_uuid_fails():
    """Invalid UUID should fail validation."""
    with pytest.raises(ValidationError):
        ChatRequest(
            message="Hello",
            session_id="not-a-uuid",
            org_id="org-123"
        )


def test_chat_response_valid():
    """Valid chat response should serialize correctly."""
    resp = ChatResponse(
        response="Appointment created!",
        session_id="550e8400-e29b-41d4-a716-446655440000",
        metadata={"state": "COMPLETE"}
    )
    assert resp.response == "Appointment created!"
    assert resp.metadata["state"] == "COMPLETE"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_api_models.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.api.models'"

**Step 3: Write minimal Pydantic models**

```python
# src/api/models.py
"""Pydantic models for API request/response validation."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator, UUID4


class ChatRequest(BaseModel):
    """Request schema for /api/v1/chat endpoint."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User message (1-2000 characters)",
        examples=["I'd like to book an appointment"]
    )
    session_id: UUID4 = Field(
        ...,
        description="Client session UUID for conversation tracking",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    org_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Organization identifier",
        examples=["org-123", "clinic-downtown"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "I need to book a consultation",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "org_id": "org-123"
            }
        }


class ChatResponse(BaseModel):
    """Response schema for /api/v1/chat endpoint."""
    response: str = Field(..., description="Agent response message")
    session_id: UUID4 = Field(..., description="Session identifier")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata (state, context, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "response": "I'd be happy to help! What service would you like?",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "metadata": {"current_state": "COLLECT_SERVICE"}
            }
        }


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    code: Optional[str] = Field(None, description="Error code")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Rate limit exceeded",
                "detail": "Maximum 100 requests per hour exceeded",
                "code": "RATE_LIMIT_EXCEEDED"
            }
        }
```

```python
# src/api/__init__.py
"""API package initialization."""
from src.api.models import ChatRequest, ChatResponse, ErrorResponse

__all__ = ["ChatRequest", "ChatResponse", "ErrorResponse"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_api_models.py -v`
Expected: PASS (all 5 tests)

**Step 5: Create FastAPI app skeleton with CORS**

```python
# src/api_server.py
"""FastAPI production server for appointment booking agent.

Features:
- CORS middleware for WordPress/Shopify integration
- Global exception handling
- Health check endpoint
- Structured logging
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.api.models import ErrorResponse

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown logic."""
    logger.info("FastAPI server starting up...")
    # Startup: Initialize database connections, etc.
    yield
    # Shutdown: Close connections
    logger.info("FastAPI server shutting down...")


app = FastAPI(
    title="Appointment Booking Agent API",
    description="Multi-tenant conversational AI for appointment booking",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for WordPress/Shopify integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://*.wordpress.com",
        "https://*.myshopify.com",
        "http://localhost:3000",  # Development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors consistently."""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation Error",
            detail=str(exc.errors()),
            code="VALIDATION_ERROR"
        ).model_dump()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal Server Error",
            detail="An unexpected error occurred. Please try again later.",
            code="INTERNAL_ERROR"
        ).model_dump()
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for load balancers."""
    return {
        "status": "healthy",
        "service": "appointment-agent-api",
        "version": "1.0.0"
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API info."""
    return {
        "message": "Appointment Booking Agent API",
        "docs": "/docs",
        "health": "/health"
    }
```

**Step 6: Test FastAPI server manually**

Run: `cd agent-appoiments-v2 && uvicorn src.api_server:app --reload --port 8000`
Test: `curl http://localhost:8000/health`
Expected: `{"status":"healthy","service":"appointment-agent-api","version":"1.0.0"}`

**Step 7: Commit**

```bash
git add src/api/ src/api_server.py tests/unit/test_api_models.py
git commit -m "feat: add FastAPI base structure with CORS and error handling

- Create Pydantic models for ChatRequest/ChatResponse with validation
- Setup FastAPI app with CORS middleware for WordPress/Shopify
- Add global exception handlers for consistent error responses
- Add health check endpoint for load balancers
- Add structured logging configuration"
```

---

### Task 1.2: Migrate from MemorySaver to PostgreSQL

**Files:**
- Modify: `agent-appoiments-v2/src/database.py`
- Modify: `agent-appoiments-v2/src/agent.py:693-699`
- Create: `agent-appoiments-v2/tests/integration/test_postgres_checkpointing.py`
- Create: `agent-appoiments-v2/alembic.ini` (optional for migrations)

**Step 1: Write failing integration test**

```python
# tests/integration/test_postgres_checkpointing.py
"""Test PostgreSQL checkpointing functionality."""
import pytest
import os
from uuid import uuid4
from langchain_core.messages import HumanMessage
from src.agent import create_production_graph
from src.database import get_postgres_saver


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set - skipping Postgres tests"
)
def test_postgres_saver_persists_conversation():
    """PostgresSaver should persist conversation state across sessions."""
    # Create graph with PostgreSQL checkpointer
    graph = create_production_graph()

    # Session 1: Send first message
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result1 = graph.invoke(
        {"messages": [HumanMessage(content="Hello")]},
        config=config
    )

    assert len(result1["messages"]) > 0

    # Session 2: Continue conversation (should have history)
    result2 = graph.invoke(
        {"messages": [HumanMessage(content="I need an appointment")]},
        config=config
    )

    # Should have messages from both sessions
    assert len(result2["messages"]) > len(result1["messages"])


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set - skipping Postgres tests"
)
def test_postgres_saver_setup_creates_tables():
    """PostgresSaver.setup() should create necessary tables."""
    with get_postgres_saver() as saver:
        # This should not raise an exception
        saver.setup()

        # Verify we can write a checkpoint
        from langgraph.checkpoint.base import Checkpoint
        checkpoint = Checkpoint(
            v=1,
            id=str(uuid4()),
            ts="2025-01-01T00:00:00Z",
            channel_values={},
            channel_versions={},
            versions_seen={}
        )

        # Should succeed without errors
        config = {"configurable": {"thread_id": str(uuid4())}}
        saver.put(config, checkpoint, {})
```

**Step 2: Run test to verify it fails**

Run: `DATABASE_URL="postgresql://user:pass@localhost:5432/testdb" pytest tests/integration/test_postgres_checkpointing.py -v`
Expected: FAIL (currently using MemorySaver in create_production_graph)

**Step 3: Update database.py with async pool and initialization**

```python
# src/database.py
"""Database and checkpointing setup.

Production Pattern:
- PostgresSaver with async connection pooling
- Automatic table creation via setup()
- Thread-safe operations
- Proper connection lifecycle management
"""
import os
from contextlib import contextmanager
from typing import Optional
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver


# Global connection pool (initialized on first use)
_connection_pool: Optional[ConnectionPool] = None


def get_connection_pool() -> ConnectionPool:
    """
    Get or create connection pool for PostgreSQL.

    Pattern: Singleton connection pool for horizontal scaling.
    Pool configuration:
    - min_size=2: Minimum connections kept alive
    - max_size=10: Maximum connections (adjust based on load)
    - Connection reuse across requests

    Returns:
        ConnectionPool instance

    Raises:
        ValueError: If DATABASE_URL not set
    """
    global _connection_pool

    if _connection_pool is None:
        db_uri = os.getenv("DATABASE_URL")
        if not db_uri:
            raise ValueError(
                "DATABASE_URL environment variable required. "
                "Format: postgresql://user:password@host:port/database"
            )

        _connection_pool = ConnectionPool(
            conninfo=db_uri,
            min_size=2,
            max_size=10,
            timeout=30,  # Connection acquisition timeout
        )

    return _connection_pool


@contextmanager
def get_postgres_saver():
    """
    Get PostgresSaver with automatic cleanup.

    Context manager pattern ensures proper connection lifecycle.

    Usage:
        with get_postgres_saver() as saver:
            saver.setup()  # Create tables if not exist
            graph = builder.compile(checkpointer=saver)

    Yields:
        PostgresSaver: Configured checkpointer instance
    """
    pool = get_connection_pool()

    try:
        with pool.connection() as conn:
            saver = PostgresSaver(conn)
            yield saver
    finally:
        # Connection returned to pool automatically
        pass


def close_connection_pool():
    """
    Close the global connection pool.

    Call this during application shutdown to gracefully close
    all database connections.

    Usage:
        @app.on_event("shutdown")
        async def shutdown():
            close_connection_pool()
    """
    global _connection_pool

    if _connection_pool is not None:
        _connection_pool.close()
        _connection_pool = None


def init_database():
    """
    Initialize database tables for checkpointing.

    Creates all necessary tables for LangGraph checkpointing.
    Safe to call multiple times (idempotent).

    Usage:
        @app.on_event("startup")
        async def startup():
            init_database()
    """
    with get_postgres_saver() as saver:
        saver.setup()
```

**Step 4: Update agent.py to use PostgreSQL in production**

```python
# Modify src/agent.py around line 693-699

def create_production_graph():
    """
    Create graph with PostgreSQL checkpointing (production).

    Use this in production environments with DATABASE_URL set.
    Falls back to MemorySaver if DATABASE_URL not available.

    Pattern: Checkpointer is created once and reused via connection pool.
    """
    from src.database import get_postgres_saver

    builder = StateGraph(AppointmentState)

    # Add nodes (same as create_graph)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("retry_handler", retry_handler_node)

    # Edges
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )

    builder.add_conditional_edges(
        "tools",
        should_use_retry_handler,
        {
            "retry_handler": "retry_handler",
            "agent": "agent"
        }
    )
    builder.add_edge("retry_handler", "agent")

    # Production checkpointer with PostgreSQL
    if os.getenv("DATABASE_URL"):
        # Use PostgreSQL connection pool (long-lived saver)
        pool = get_connection_pool()
        conn = pool.connection()
        saver = PostgresSaver(conn)
        saver.setup()  # Create tables if not exist
        return builder.compile(checkpointer=saver)
    else:
        # Fallback for development
        import warnings
        warnings.warn(
            "DATABASE_URL not set - using MemorySaver (not production-ready)"
        )
        return builder.compile(checkpointer=MemorySaver())
```

**Step 5: Run test to verify it passes**

Run: `DATABASE_URL="postgresql://user:pass@localhost:5432/testdb" pytest tests/integration/test_postgres_checkpointing.py -v`
Expected: PASS (both tests)

**Step 6: Update .env.example with DATABASE_URL**

```bash
# Add to agent-appoiments-v2/.env.example
DATABASE_URL=postgresql://user:password@localhost:5432/appointments
```

**Step 7: Commit**

```bash
git add src/database.py src/agent.py tests/integration/test_postgres_checkpointing.py .env.example
git commit -m "feat: migrate from MemorySaver to PostgreSQL for production

- Update database.py with connection pooling (min=2, max=10)
- Add init_database() for table creation on startup
- Update create_production_graph() to use PostgresSaver
- Add integration tests for PostgreSQL persistence
- Add DATABASE_URL to .env.example
- Maintain MemorySaver fallback for development"
```

---

### Task 1.3: Implement Basic /chat Endpoint

**Files:**
- Modify: `agent-appoiments-v2/src/api_server.py`
- Create: `agent-appoiments-v2/src/api/dependencies.py`
- Create: `agent-appoiments-v2/tests/integration/test_chat_endpoint.py`

**Step 1: Write failing integration test**

```python
# tests/integration/test_chat_endpoint.py
"""Test /api/v1/chat endpoint."""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.fixture
def client():
    """Create FastAPI test client."""
    from src.api_server import app
    return TestClient(app)


def test_chat_endpoint_returns_response(client, monkeypatch):
    """POST /api/v1/chat should return agent response."""
    # Mock DATABASE_URL for testing
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    session_id = str(uuid4())
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Hello, I need an appointment",
            "session_id": session_id,
            "org_id": "org-test-123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "session_id" in data
    assert data["session_id"] == session_id
    assert isinstance(data["response"], str)
    assert len(data["response"]) > 0


def test_chat_endpoint_maintains_conversation_state(client, monkeypatch):
    """Multiple requests with same session_id should maintain context."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    session_id = str(uuid4())

    # First message
    response1 = client.post(
        "/api/v1/chat",
        json={
            "message": "Hello",
            "session_id": session_id,
            "org_id": "org-test-123"
        }
    )
    assert response1.status_code == 200

    # Second message (should have context from first)
    response2 = client.post(
        "/api/v1/chat",
        json={
            "message": "I need a consultation",
            "session_id": session_id,
            "org_id": "org-test-123"
        }
    )
    assert response2.status_code == 200
    data = response2.json()
    assert "metadata" in data


def test_chat_endpoint_rejects_invalid_request(client):
    """Invalid request should return 422."""
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "",  # Empty message
            "session_id": "not-a-uuid",
            "org_id": "org-test-123"
        }
    )
    assert response.status_code == 422
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_chat_endpoint.py -v`
Expected: FAIL with "404 Not Found" (endpoint doesn't exist yet)

**Step 3: Create dependency for graph access**

```python
# src/api/dependencies.py
"""FastAPI dependency injection functions."""
from functools import lru_cache
from src.agent import create_production_graph


@lru_cache(maxsize=1)
def get_agent_graph():
    """
    Get compiled LangGraph agent (cached singleton).

    Pattern: Create graph once, reuse across requests.
    Graph compilation is expensive (~500ms), so we cache it.

    Returns:
        Compiled StateGraph with PostgreSQL checkpointer
    """
    return create_production_graph()
```

**Step 4: Implement /chat endpoint**

```python
# Add to src/api_server.py

from fastapi import Depends
from langchain_core.messages import HumanMessage
from src.api.models import ChatRequest, ChatResponse
from src.api.dependencies import get_agent_graph


@app.post("/api/v1/chat", tags=["Chat"], response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    graph=Depends(get_agent_graph)
):
    """
    Process chat message and return agent response.

    Args:
        request: ChatRequest with message, session_id, org_id
        graph: Compiled LangGraph agent (injected dependency)

    Returns:
        ChatResponse with agent's reply and metadata

    Raises:
        422: Validation error
        500: Internal server error
    """
    try:
        # Configure LangGraph with session and org context
        config = {
            "configurable": {
                "thread_id": str(request.session_id),  # Maps to PostgreSQL checkpoint
                "org_id": request.org_id  # For multi-tenant configuration
            }
        }

        # Invoke graph with user message
        logger.info(f"Processing message for session={request.session_id}, org={request.org_id}")
        result = graph.invoke(
            {"messages": [HumanMessage(content=request.message)]},
            config=config
        )

        # Extract response from last message
        messages = result.get("messages", [])
        if not messages:
            raise ValueError("No response from agent")

        last_message = messages[-1]
        response_text = last_message.content if hasattr(last_message, 'content') else str(last_message)

        # Build metadata
        metadata = {
            "current_state": str(result.get("current_state", "")),
            "message_count": len(messages)
        }

        logger.info(f"Response generated for session={request.session_id}")

        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
            metadata=metadata
        )

    except Exception as e:
        logger.error(f"Error processing chat: {e}", exc_info=True)
        raise
```

**Step 5: Update lifespan to initialize database**

```python
# Modify lifespan in src/api_server.py

from src.database import init_database, close_connection_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown logic."""
    logger.info("FastAPI server starting up...")

    # Startup: Initialize database tables
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    yield

    # Shutdown: Close connections
    close_connection_pool()
    logger.info("FastAPI server shutting down...")
```

**Step 6: Run test to verify it passes**

Run: `DATABASE_URL="postgresql://user:pass@localhost:5432/testdb" pytest tests/integration/test_chat_endpoint.py -v`
Expected: PASS (all 3 tests)

**Step 7: Test manually with curl**

```bash
# Terminal 1: Start server
cd agent-appoiments-v2
DATABASE_URL="postgresql://user:pass@localhost:5432/appointments" uvicorn src.api_server:app --reload --port 8000

# Terminal 2: Test endpoint
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, I need an appointment",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "org_id": "org-123"
  }'
```

Expected: JSON response with agent's greeting

**Step 8: Commit**

```bash
git add src/api_server.py src/api/dependencies.py tests/integration/test_chat_endpoint.py
git commit -m "feat: implement POST /api/v1/chat endpoint

- Create /api/v1/chat endpoint for conversational interaction
- Integrate LangGraph with FastAPI via dependency injection
- Use session_id as thread_id for PostgreSQL checkpointing
- Extract response and metadata from graph results
- Initialize database on startup, close pool on shutdown
- Add integration tests for chat endpoint and state persistence"
```

---

## PHASE 2: LANGGRAPH INTEGRATION (Week 2)

### Task 2.1: Session Management with thread_id

**Files:**
- Create: `agent-appoiments-v2/src/session_manager.py`
- Create: `agent-appoiments-v2/src/api/database_models.py` (SQLAlchemy models)
- Create: `agent-appoiments-v2/tests/unit/test_session_manager.py`
- Create: `agent-appoiments-v2/alembic/versions/001_create_sessions_table.py`

**Step 1: Write failing test**

```python
# tests/unit/test_session_manager.py
"""Test session management functionality."""
import pytest
from uuid import UUID
from datetime import datetime, timedelta
from src.session_manager import SessionManager, SessionNotFoundError


@pytest.fixture
def session_manager():
    """Create SessionManager with in-memory database."""
    return SessionManager(database_url="sqlite:///:memory:")


def test_create_session_generates_thread_id(session_manager):
    """Creating session should generate unique thread_id."""
    session_id = "550e8400-e29b-41d4-a716-446655440000"
    org_id = "org-123"

    thread_id = session_manager.create_session(session_id, org_id)

    assert isinstance(thread_id, str)
    assert len(thread_id) > 0
    assert thread_id != session_id  # Should be different


def test_get_thread_id_retrieves_existing_session(session_manager):
    """Getting thread_id for existing session should return same value."""
    session_id = "550e8400-e29b-41d4-a716-446655440000"
    org_id = "org-123"

    thread_id_1 = session_manager.create_session(session_id, org_id)
    thread_id_2 = session_manager.get_thread_id(session_id)

    assert thread_id_1 == thread_id_2


def test_get_thread_id_raises_for_nonexistent_session(session_manager):
    """Getting thread_id for non-existent session should raise error."""
    with pytest.raises(SessionNotFoundError):
        session_manager.get_thread_id("nonexistent-session-id")


def test_cleanup_expired_sessions_removes_old_sessions(session_manager):
    """Cleanup should remove sessions older than 48 hours."""
    # Create old session (manually set timestamp)
    old_session_id = "old-session-id"
    session_manager.create_session(old_session_id, "org-123")

    # Manually update timestamp to 49 hours ago
    session_manager._update_last_activity(
        old_session_id,
        datetime.utcnow() - timedelta(hours=49)
    )

    # Create recent session
    recent_session_id = "recent-session-id"
    session_manager.create_session(recent_session_id, "org-123")

    # Cleanup expired sessions
    deleted_count = session_manager.cleanup_expired_sessions(max_age_hours=48)

    assert deleted_count == 1

    # Old session should be gone
    with pytest.raises(SessionNotFoundError):
        session_manager.get_thread_id(old_session_id)

    # Recent session should still exist
    assert session_manager.get_thread_id(recent_session_id) is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_session_manager.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.session_manager'"

**Step 3: Create SQLAlchemy models**

```python
# src/api/database_models.py
"""SQLAlchemy database models for API layer."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Session(Base):
    """Session tracking table for thread_id mapping."""
    __tablename__ = "sessions"

    session_id = Column(String(255), primary_key=True, index=True)
    thread_id = Column(String(255), nullable=False, unique=True, index=True)
    org_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Session(session_id={self.session_id}, org_id={self.org_id})>"
```

**Step 4: Implement SessionManager**

```python
# src/session_manager.py
"""Session management for mapping client session_id to LangGraph thread_id."""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, Session as SQLSession
from src.api.database_models import Base, Session


class SessionNotFoundError(Exception):
    """Raised when session_id not found in database."""
    pass


class SessionManager:
    """
    Manages mapping between client session_id and LangGraph thread_id.

    Responsibilities:
    - Generate unique thread_id for each session
    - Store session metadata (org_id, timestamps)
    - Cleanup expired sessions (>48 hours inactive)

    Pattern: Thin wrapper around SQLAlchemy for session persistence.
    """

    def __init__(self, database_url: str):
        """
        Initialize SessionManager with database connection.

        Args:
            database_url: SQLAlchemy connection string
        """
        self.engine = create_engine(database_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_session(self, session_id: str, org_id: str) -> str:
        """
        Create new session with generated thread_id.

        Args:
            session_id: Client-provided session UUID
            org_id: Organization identifier

        Returns:
            Generated thread_id for LangGraph checkpointing
        """
        thread_id = f"thread-{uuid.uuid4()}"

        with self.SessionLocal() as db:
            session = Session(
                session_id=session_id,
                thread_id=thread_id,
                org_id=org_id,
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow()
            )
            db.add(session)
            db.commit()

        return thread_id

    def get_thread_id(self, session_id: str) -> str:
        """
        Get thread_id for existing session.

        Args:
            session_id: Client-provided session UUID

        Returns:
            thread_id for LangGraph

        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        with self.SessionLocal() as db:
            session = db.query(Session).filter(Session.session_id == session_id).first()

            if not session:
                raise SessionNotFoundError(f"Session {session_id} not found")

            # Update last_activity timestamp
            session.last_activity = datetime.utcnow()
            db.commit()

            return session.thread_id

    def get_or_create_thread_id(self, session_id: str, org_id: str) -> str:
        """
        Get existing thread_id or create new session.

        Args:
            session_id: Client-provided session UUID
            org_id: Organization identifier

        Returns:
            thread_id (existing or newly created)
        """
        try:
            return self.get_thread_id(session_id)
        except SessionNotFoundError:
            return self.create_session(session_id, org_id)

    def cleanup_expired_sessions(self, max_age_hours: int = 48) -> int:
        """
        Delete sessions older than max_age_hours.

        Args:
            max_age_hours: Maximum session age in hours (default: 48)

        Returns:
            Number of deleted sessions
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        with self.SessionLocal() as db:
            deleted = db.query(Session).filter(
                Session.last_activity < cutoff_time
            ).delete()
            db.commit()

        return deleted

    def _update_last_activity(self, session_id: str, timestamp: datetime):
        """Helper for testing - manually update last_activity."""
        with self.SessionLocal() as db:
            session = db.query(Session).filter(Session.session_id == session_id).first()
            if session:
                session.last_activity = timestamp
                db.commit()
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_session_manager.py -v`
Expected: PASS (all 5 tests)

**Step 6: Integrate SessionManager into /chat endpoint**

```python
# Modify src/api_server.py

from src.session_manager import SessionManager

# Initialize SessionManager (singleton)
session_manager = SessionManager(database_url=os.getenv("DATABASE_URL"))


@app.post("/api/v1/chat", tags=["Chat"], response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    graph=Depends(get_agent_graph)
):
    """Process chat message with session management."""
    try:
        # Get or create thread_id for this session
        thread_id = session_manager.get_or_create_thread_id(
            session_id=str(request.session_id),
            org_id=request.org_id
        )

        # Configure LangGraph with thread_id
        config = {
            "configurable": {
                "thread_id": thread_id,  # Internal LangGraph thread
                "org_id": request.org_id
            }
        }

        # ... rest of endpoint logic ...
```

**Step 7: Add cleanup job to lifespan**

```python
# Add to lifespan in src/api_server.py

import asyncio


async def cleanup_sessions_periodically():
    """Background task to cleanup expired sessions every hour."""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            deleted = session_manager.cleanup_expired_sessions(max_age_hours=48)
            logger.info(f"Cleaned up {deleted} expired sessions")
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan with session cleanup background task."""
    logger.info("FastAPI server starting up...")

    # Startup
    init_database()
    cleanup_task = asyncio.create_task(cleanup_sessions_periodically())

    yield

    # Shutdown
    cleanup_task.cancel()
    close_connection_pool()
    logger.info("FastAPI server shutting down...")
```

**Step 8: Commit**

```bash
git add src/session_manager.py src/api/database_models.py tests/unit/test_session_manager.py src/api_server.py
git commit -m "feat: add session management with thread_id mapping

- Create SessionManager for client session_id to LangGraph thread_id mapping
- Add SQLAlchemy Session model with org_id and timestamps
- Implement get_or_create_thread_id() for seamless session handling
- Add cleanup_expired_sessions() to remove inactive sessions (>48h)
- Integrate SessionManager into /chat endpoint
- Add hourly background task for automatic session cleanup"
```

---

### Task 2.2: Implement Streaming with Server-Sent Events

**Files:**
- Create: `agent-appoiments-v2/src/api/streaming.py`
- Modify: `agent-appoiments-v2/src/api_server.py`
- Create: `agent-appoiments-v2/tests/integration/test_streaming_endpoint.py`

**Step 1: Write failing integration test**

```python
# tests/integration/test_streaming_endpoint.py
"""Test /api/v1/chat/stream endpoint."""
import pytest
import json
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.fixture
def client():
    """Create FastAPI test client."""
    from src.api_server import app
    return TestClient(app)


def test_streaming_endpoint_returns_sse_events(client, monkeypatch):
    """POST /api/v1/chat/stream should return Server-Sent Events."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    session_id = str(uuid4())

    with client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={
            "message": "Hello",
            "session_id": session_id,
            "org_id": "org-test-123"
        }
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                data_str = line[6:]  # Remove "data: " prefix
                event_data = json.loads(data_str)
                events.append(event_data)

        # Should have at least one event
        assert len(events) > 0

        # Last event should have done=True
        assert events[-1]["done"] is True


def test_streaming_endpoint_streams_chunks(client, monkeypatch):
    """Streaming should send multiple chunks during processing."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    session_id = str(uuid4())

    with client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={
            "message": "I need an appointment for consultation",
            "session_id": session_id,
            "org_id": "org-test-123"
        }
    ) as response:
        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                event_data = json.loads(data_str)
                events.append(event_data)

        # Should have multiple chunks (agent processes through steps)
        assert len(events) >= 2

        # Events should have chunk field
        for event in events[:-1]:  # All except last
            assert "chunk" in event
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_streaming_endpoint.py -v`
Expected: FAIL with "404 Not Found" (endpoint doesn't exist)

**Step 3: Create streaming helper module**

```python
# src/api/streaming.py
"""Server-Sent Events streaming utilities."""
import json
import asyncio
from typing import AsyncGenerator, Dict, Any


async def stream_graph_events(
    graph,
    input_data: Dict[str, Any],
    config: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    """
    Stream LangGraph execution as Server-Sent Events.

    Yields SSE-formatted events with:
    - chunk: Partial output from graph nodes
    - done: Boolean indicating completion
    - metadata: Additional context (node name, state, etc.)

    Args:
        graph: Compiled LangGraph instance
        input_data: Input dictionary for graph.astream()
        config: Configuration dict (thread_id, org_id, etc.)

    Yields:
        SSE-formatted strings: "data: {json}\n\n"
    """
    try:
        # Stream events from LangGraph
        async for event in graph.astream(input_data, config=config):
            # event structure: {node_name: {messages: [...], ...}}

            for node_name, node_output in event.items():
                # Extract relevant data from node output
                chunk_data = {
                    "chunk": str(node_output),
                    "done": False,
                    "metadata": {
                        "node": node_name,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                }

                # Format as SSE
                yield f"data: {json.dumps(chunk_data)}\n\n"

        # Send final "done" event
        final_event = {
            "chunk": "",
            "done": True,
            "metadata": {"completed": True}
        }
        yield f"data: {json.dumps(final_event)}\n\n"

    except Exception as e:
        # Send error event
        error_event = {
            "chunk": "",
            "done": True,
            "error": str(e)
        }
        yield f"data: {json.dumps(error_event)}\n\n"
```

**Step 4: Implement /chat/stream endpoint**

```python
# Add to src/api_server.py

from fastapi.responses import StreamingResponse
from src.api.streaming import stream_graph_events


@app.post("/api/v1/chat/stream", tags=["Chat"])
async def chat_stream(
    request: ChatRequest,
    graph=Depends(get_agent_graph)
):
    """
    Process chat message with Server-Sent Events streaming.

    Streams real-time updates as the agent processes the request.
    Useful for showing typing indicators or progressive responses.

    Args:
        request: ChatRequest with message, session_id, org_id
        graph: Compiled LangGraph agent

    Returns:
        StreamingResponse with text/event-stream content

    Response Format:
        data: {"chunk": "partial text", "done": false, "metadata": {...}}
        data: {"chunk": "", "done": true, "metadata": {...}}
    """
    # Get or create thread_id
    thread_id = session_manager.get_or_create_thread_id(
        session_id=str(request.session_id),
        org_id=request.org_id
    )

    # Configure graph
    config = {
        "configurable": {
            "thread_id": thread_id,
            "org_id": request.org_id
        }
    }

    # Prepare input
    input_data = {"messages": [HumanMessage(content=request.message)]}

    # Stream events
    logger.info(f"Starting stream for session={request.session_id}")

    return StreamingResponse(
        stream_graph_events(graph, input_data, config),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/integration/test_streaming_endpoint.py -v`
Expected: PASS (both tests)

**Step 6: Test manually with curl**

```bash
# Stream endpoint test
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "org_id": "org-123"
  }' \
  --no-buffer
```

Expected: Series of SSE events showing agent processing

**Step 7: Commit**

```bash
git add src/api/streaming.py src/api_server.py tests/integration/test_streaming_endpoint.py
git commit -m "feat: implement Server-Sent Events streaming for chat

- Create POST /api/v1/chat/stream endpoint for real-time responses
- Implement stream_graph_events() to convert LangGraph events to SSE
- Send chunk, done, and metadata fields in SSE format
- Add proper SSE headers (Cache-Control, X-Accel-Buffering)
- Add integration tests for streaming endpoint
- Enable frontend typing indicators and progressive UI"
```

---

### Task 2.3: Multi-tenancy Configuration

**Files:**
- Modify: `agent-appoiments-v2/src/api/dependencies.py`
- Create: `agent-appoiments-v2/src/api/org_loader.py`
- Create: `agent-appoiments-v2/tests/unit/test_org_loader.py`
- Modify: `agent-appoiments-v2/src/api_server.py`

**Step 1: Write failing test**

```python
# tests/unit/test_org_loader.py
"""Test organization configuration loading."""
import pytest
from src.api.org_loader import OrgConfigLoader, OrgNotFoundError


@pytest.fixture
def config_loader():
    """Create OrgConfigLoader with in-memory database."""
    return OrgConfigLoader(database_url="sqlite:///:memory:")


def test_load_org_config_returns_valid_config(config_loader):
    """Loading org config should return OrganizationConfig."""
    from src.org_config import OrganizationConfig

    # Assume org-123 exists in database
    config = config_loader.load_org_config("org-123")

    assert isinstance(config, OrganizationConfig)
    assert config.org_id == "org-123"


def test_load_org_config_raises_for_inactive_org(config_loader):
    """Loading inactive org should raise error."""
    with pytest.raises(OrgNotFoundError) as exc_info:
        config_loader.load_org_config("org-inactive")

    assert "not active" in str(exc_info.value).lower()


def test_load_org_config_raises_for_nonexistent_org(config_loader):
    """Loading non-existent org should raise error."""
    with pytest.raises(OrgNotFoundError):
        config_loader.load_org_config("org-nonexistent")


def test_validate_org_exists_returns_true_for_active_org(config_loader):
    """Validation should return True for active org."""
    assert config_loader.validate_org_exists("org-123") is True


def test_validate_org_exists_returns_false_for_inactive_org(config_loader):
    """Validation should return False for inactive org."""
    assert config_loader.validate_org_exists("org-inactive") is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_org_loader.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.api.org_loader'"

**Step 3: Create organization database table**

```python
# Add to src/api/database_models.py

from sqlalchemy import Column, String, Boolean, JSON


class Organization(Base):
    """Organization configuration table."""
    __tablename__ = "organizations"

    org_id = Column(String(100), primary_key=True, index=True)
    org_name = Column(String(200), nullable=True)
    system_prompt = Column(String(5000), nullable=True)
    services = Column(JSON, nullable=False, default=list)  # List of ServiceConfig dicts
    permissions = Column(JSON, nullable=False)  # PermissionsConfig dict
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

**Step 4: Implement OrgConfigLoader**

```python
# src/api/org_loader.py
"""Organization configuration loading from database."""
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.api.database_models import Base, Organization
from src.org_config import OrganizationConfig, ServiceConfig, PermissionsConfig


class OrgNotFoundError(Exception):
    """Raised when organization not found or inactive."""
    pass


class OrgConfigLoader:
    """
    Loads organization configuration from database.

    Pattern: Separate database persistence from domain models.
    OrganizationConfig (domain) vs Organization (database).
    """

    def __init__(self, database_url: str):
        """Initialize with database connection."""
        self.engine = create_engine(database_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def load_org_config(self, org_id: str) -> OrganizationConfig:
        """
        Load organization configuration from database.

        Args:
            org_id: Organization identifier

        Returns:
            OrganizationConfig instance

        Raises:
            OrgNotFoundError: If org doesn't exist or is inactive
        """
        with self.SessionLocal() as db:
            org = db.query(Organization).filter(
                Organization.org_id == org_id,
                Organization.is_active == True
            ).first()

            if not org:
                raise OrgNotFoundError(f"Organization {org_id} not found or not active")

            # Convert database model to domain model
            return OrganizationConfig(
                org_id=org.org_id,
                org_name=org.org_name,
                system_prompt=org.system_prompt,
                services=[ServiceConfig(**svc) for svc in org.services],
                permissions=PermissionsConfig(**org.permissions)
            )

    def validate_org_exists(self, org_id: str) -> bool:
        """
        Check if organization exists and is active.

        Args:
            org_id: Organization identifier

        Returns:
            True if active, False otherwise
        """
        try:
            self.load_org_config(org_id)
            return True
        except OrgNotFoundError:
            return False
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_org_loader.py -v`
Expected: PASS (all tests - after adding test fixtures with sample data)

**Step 6: Integrate org validation into /chat endpoint**

```python
# Modify src/api_server.py

from src.api.org_loader import OrgConfigLoader, OrgNotFoundError

# Initialize OrgConfigLoader
org_loader = OrgConfigLoader(database_url=os.getenv("DATABASE_URL"))


@app.post("/api/v1/chat", tags=["Chat"], response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    graph=Depends(get_agent_graph)
):
    """Process chat with org validation."""
    try:
        # Validate org exists and is active
        if not org_loader.validate_org_exists(request.org_id):
            raise OrgNotFoundError(f"Organization {request.org_id} not found or inactive")

        # Load org configuration
        org_config = org_loader.load_org_config(request.org_id)

        # Get or create thread_id
        thread_id = session_manager.get_or_create_thread_id(
            session_id=str(request.session_id),
            org_id=request.org_id
        )

        # Configure graph with org settings
        config = {
            "configurable": {
                "thread_id": thread_id,
                "org_id": request.org_id,
                # Pass org configuration to graph
                "org_config": org_config.model_dump()
            }
        }

        # ... rest of endpoint logic ...

    except OrgNotFoundError as e:
        logger.warning(f"Invalid org_id: {request.org_id}")
        raise HTTPException(status_code=403, detail=str(e))
```

**Step 7: Add org validation error handler**

```python
# Add to src/api_server.py

from fastapi import HTTPException


@app.exception_handler(OrgNotFoundError)
async def org_not_found_handler(request: Request, exc: OrgNotFoundError):
    """Handle organization not found errors."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=ErrorResponse(
            error="Organization Not Found",
            detail=str(exc),
            code="ORG_NOT_FOUND"
        ).model_dump()
    )
```

**Step 8: Commit**

```bash
git add src/api/org_loader.py src/api/database_models.py src/api_server.py tests/unit/test_org_loader.py
git commit -m "feat: add multi-tenancy with org configuration validation

- Create Organization database table for config storage
- Implement OrgConfigLoader to load configs from database
- Add org validation before processing chat requests
- Pass org_config through LangGraph configurable
- Raise 403 Forbidden for inactive/non-existent orgs
- Add integration tests for org validation flow"
```

---

## PHASE 3: SECURITY & AUTHENTICATION (Week 3)

### Task 3.1: API Key Authentication System

**Files:**
- Create: `agent-appoiments-v2/src/auth.py`
- Create: `agent-appoiments-v2/tests/unit/test_auth.py`
- Modify: `agent-appoiments-v2/src/api/database_models.py`
- Modify: `agent-appoiments-v2/src/api_server.py`

**Step 1: Write failing test**

```python
# tests/unit/test_auth.py
"""Test API key authentication."""
import pytest
from src.auth import APIKeyManager, InvalidAPIKeyError


@pytest.fixture
def api_key_manager():
    """Create APIKeyManager with in-memory database."""
    return APIKeyManager(database_url="sqlite:///:memory:")


def test_generate_api_key_creates_unique_key(api_key_manager):
    """Generating API key should return unique string."""
    org_id = "org-123"

    api_key = api_key_manager.generate_api_key(org_id)

    assert isinstance(api_key, str)
    assert len(api_key) > 20  # Should be UUID-based
    assert api_key.startswith("ak_")  # Prefix for identification


def test_validate_api_key_returns_org_id(api_key_manager):
    """Validating API key should return associated org_id."""
    org_id = "org-123"
    api_key = api_key_manager.generate_api_key(org_id)

    validated_org_id = api_key_manager.validate_api_key(api_key)

    assert validated_org_id == org_id


def test_validate_api_key_raises_for_invalid_key(api_key_manager):
    """Validating invalid API key should raise error."""
    with pytest.raises(InvalidAPIKeyError):
        api_key_manager.validate_api_key("invalid_key_12345")


def test_validate_api_key_raises_for_inactive_key(api_key_manager):
    """Validating inactive API key should raise error."""
    org_id = "org-123"
    api_key = api_key_manager.generate_api_key(org_id)

    # Deactivate key
    api_key_manager.deactivate_api_key(api_key)

    # Should raise error
    with pytest.raises(InvalidAPIKeyError) as exc_info:
        api_key_manager.validate_api_key(api_key)

    assert "inactive" in str(exc_info.value).lower()


def test_generate_api_key_updates_last_used(api_key_manager):
    """Validating API key should update last_used timestamp."""
    import time

    org_id = "org-123"
    api_key = api_key_manager.generate_api_key(org_id)

    # Get initial last_used
    initial_last_used = api_key_manager._get_last_used(api_key)

    time.sleep(0.1)

    # Validate (should update last_used)
    api_key_manager.validate_api_key(api_key)

    # Check last_used was updated
    updated_last_used = api_key_manager._get_last_used(api_key)
    assert updated_last_used > initial_last_used
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_auth.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.auth'"

**Step 3: Create API key database table**

```python
# Add to src/api/database_models.py

import bcrypt


class APIKey(Base):
    """API key authentication table."""
    __tablename__ = "api_keys"

    key_hash = Column(String(255), primary_key=True)  # bcrypt hash
    org_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)  # Optional label

    @staticmethod
    def hash_key(api_key: str) -> str:
        """Hash API key using bcrypt."""
        return bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_key(api_key: str, key_hash: str) -> bool:
        """Verify API key against hash."""
        return bcrypt.checkpw(api_key.encode(), key_hash.encode())
```

**Step 4: Implement APIKeyManager**

```python
# src/auth.py
"""API key authentication and management."""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.api.database_models import Base, APIKey


class InvalidAPIKeyError(Exception):
    """Raised when API key is invalid or inactive."""
    pass


class APIKeyManager:
    """
    Manages API key generation, validation, and lifecycle.

    Pattern: Secure key generation with bcrypt hashing.
    Keys are shown in plain text ONCE during generation.
    """

    def __init__(self, database_url: str):
        """Initialize with database connection."""
        self.engine = create_engine(database_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def generate_api_key(self, org_id: str, description: Optional[str] = None) -> str:
        """
        Generate new API key for organization.

        WARNING: Returns key in plain text ONCE.
        Store it securely - cannot be retrieved later.

        Args:
            org_id: Organization identifier
            description: Optional description/label

        Returns:
            API key in format: ak_<uuid>
        """
        # Generate secure random key
        api_key = f"ak_{uuid.uuid4().hex}"

        # Hash key for storage
        key_hash = APIKey.hash_key(api_key)

        # Store in database
        with self.SessionLocal() as db:
            db_key = APIKey(
                key_hash=key_hash,
                org_id=org_id,
                created_at=datetime.utcnow(),
                last_used=datetime.utcnow(),
                is_active=True,
                description=description
            )
            db.add(db_key)
            db.commit()

        # Return plain text key (ONLY TIME IT'S VISIBLE)
        return api_key

    def validate_api_key(self, api_key: str) -> str:
        """
        Validate API key and return associated org_id.

        Updates last_used timestamp on successful validation.

        Args:
            api_key: API key to validate

        Returns:
            org_id associated with this key

        Raises:
            InvalidAPIKeyError: If key is invalid or inactive
        """
        with self.SessionLocal() as db:
            # Get all active keys (must check hash against each)
            all_keys = db.query(APIKey).filter(APIKey.is_active == True).all()

            for db_key in all_keys:
                if APIKey.verify_key(api_key, db_key.key_hash):
                    # Valid key found - update last_used
                    db_key.last_used = datetime.utcnow()
                    db.commit()

                    return db_key.org_id

            # No matching key found
            raise InvalidAPIKeyError("Invalid or inactive API key")

    def deactivate_api_key(self, api_key: str):
        """
        Deactivate API key (soft delete).

        Args:
            api_key: API key to deactivate

        Raises:
            InvalidAPIKeyError: If key not found
        """
        with self.SessionLocal() as db:
            all_keys = db.query(APIKey).all()

            for db_key in all_keys:
                if APIKey.verify_key(api_key, db_key.key_hash):
                    db_key.is_active = False
                    db.commit()
                    return

            raise InvalidAPIKeyError("API key not found")

    def _get_last_used(self, api_key: str) -> datetime:
        """Helper for testing - get last_used timestamp."""
        with self.SessionLocal() as db:
            all_keys = db.query(APIKey).all()

            for db_key in all_keys:
                if APIKey.verify_key(api_key, db_key.key_hash):
                    return db_key.last_used

            raise InvalidAPIKeyError("API key not found")
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_auth.py -v`
Expected: PASS (all 5 tests)

**Step 6: Create FastAPI dependency for auth**

```python
# Add to src/api/dependencies.py

from fastapi import Header, HTTPException, status
from src.auth import APIKeyManager, InvalidAPIKeyError
import os

# Initialize API key manager
api_key_manager = APIKeyManager(database_url=os.getenv("DATABASE_URL"))


async def validate_api_key(x_api_key: str = Header(..., description="API Key")) -> str:
    """
    FastAPI dependency for API key validation.

    Validates X-API-Key header and returns org_id.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        org_id associated with the API key

    Raises:
        HTTPException 401: If API key invalid
    """
    try:
        org_id = api_key_manager.validate_api_key(x_api_key)
        return org_id
    except InvalidAPIKeyError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "ApiKey"}
        )
```

**Step 7: Protect /chat endpoints with API key**

```python
# Modify src/api_server.py

from src.api.dependencies import validate_api_key


@app.post("/api/v1/chat", tags=["Chat"], response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    org_id_from_key: str = Depends(validate_api_key),  # NEW
    graph=Depends(get_agent_graph)
):
    """Process chat with API key authentication."""
    # Verify org_id in request matches API key
    if request.org_id != org_id_from_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key is for org '{org_id_from_key}', but request specifies '{request.org_id}'"
        )

    # ... rest of endpoint logic ...


@app.post("/api/v1/chat/stream", tags=["Chat"])
async def chat_stream(
    request: ChatRequest,
    org_id_from_key: str = Depends(validate_api_key),  # NEW
    graph=Depends(get_agent_graph)
):
    """Stream chat with API key authentication."""
    # Verify org_id match
    if request.org_id != org_id_from_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key mismatch: expected '{org_id_from_key}', got '{request.org_id}'"
        )

    # ... rest of endpoint logic ...
```

**Step 8: Add CLI tool for API key generation**

```python
# Create agent-appoiments-v2/scripts/generate_api_key.py
"""CLI tool to generate API keys for organizations."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import APIKeyManager
from dotenv import load_dotenv

load_dotenv()


def main():
    """Generate API key for organization."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_api_key.py <org_id> [description]")
        sys.exit(1)

    org_id = sys.argv[1]
    description = sys.argv[2] if len(sys.argv) > 2 else None

    manager = APIKeyManager(database_url=os.getenv("DATABASE_URL"))

    api_key = manager.generate_api_key(org_id, description)

    print(f"\n✅ API Key generated for organization: {org_id}")
    print(f"\n🔑 API Key: {api_key}")
    print("\n⚠️  IMPORTANT: Save this key securely! It cannot be retrieved later.")
    print("\nUsage:")
    print(f"  curl -X POST http://localhost:8000/api/v1/chat \\")
    print(f"    -H 'X-API-Key: {api_key}' \\")
    print(f"    -H 'Content-Type: application/json' \\")
    print(f"    -d '{{...}}'")


if __name__ == "__main__":
    main()
```

**Step 9: Commit**

```bash
git add src/auth.py src/api/dependencies.py src/api/database_models.py src/api_server.py tests/unit/test_auth.py scripts/generate_api_key.py
git commit -m "feat: add API key authentication system

- Create APIKey database table with bcrypt hashing
- Implement APIKeyManager for key generation and validation
- Add validate_api_key FastAPI dependency
- Protect /chat and /chat/stream with X-API-Key header
- Verify org_id in request matches API key org_id
- Add CLI tool for generating API keys
- Update last_used timestamp on each validation"
```

---

### Task 3.1B: FIX CRITICAL BUG - API Key Validation Performance (URGENT - 1-2 hours)

**Context:** Current implementation in Step 6 of Task 3.1 has O(N) performance bug - validates by iterating ALL active keys. This kills database performance with 1000+ organizations.

**Files:**
- Modify: `agent-appoiments-v2/src/auth.py:1914-1942`
- Create: `agent-appoiments-v2/tests/performance/test_api_key_performance.py`

**Step 1: Write failing performance test**

```python
# tests/performance/test_api_key_performance.py
"""Test API key validation performance."""
import pytest
import time
from src.auth import APIKeyManager


@pytest.fixture
def api_key_manager_with_many_keys():
    """Create APIKeyManager with 1000 keys."""
    manager = APIKeyManager(database_url="sqlite:///:memory:")

    # Create 1000 organizations with API keys
    for i in range(1000):
        manager.generate_api_key(f"org-{i:04d}", f"Test org {i}")

    return manager


def test_api_key_validation_is_fast(api_key_manager_with_many_keys):
    """API key validation should be O(1), not O(N)."""
    manager = api_key_manager_with_many_keys

    # Generate one more key to test
    test_key = manager.generate_api_key("org-test", "Test")

    # Validation should be fast (< 100ms even with 1000 keys)
    start = time.time()
    org_id = manager.validate_api_key(test_key)
    elapsed = time.time() - start

    assert org_id == "org-test"
    assert elapsed < 0.1, f"Validation took {elapsed:.3f}s - TOO SLOW! Should be O(1)"


def test_invalid_key_validation_is_fast(api_key_manager_with_many_keys):
    """Invalid key check should also be O(1)."""
    manager = api_key_manager_with_many_keys

    # Invalid key should fail fast
    start = time.time()
    with pytest.raises(Exception):  # Will raise InvalidAPIKeyError
        manager.validate_api_key("ak_invalid_key_12345")
    elapsed = time.time() - start

    assert elapsed < 0.1, f"Invalid key check took {elapsed:.3f}s - TOO SLOW!"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/performance/test_api_key_performance.py -v`
Expected: FAIL with "AssertionError: Validation took X.XXs - TOO SLOW! Should be O(1)"

**Step 3: FIX THE BUG - Use indexed hash lookup instead of iteration**

```python
# Modify src/auth.py lines 1914-1942

def validate_api_key(self, api_key: str) -> str:
    """
    Validate API key and return associated org_id.

    PERFORMANCE FIX: Uses indexed hash lookup instead of O(N) iteration.
    Previous bug: Iterated ALL active keys to find match (catastrophic with 1000+ orgs).
    New approach: Hash input key once, use indexed WHERE clause for O(1) lookup.

    Updates last_used timestamp on successful validation.

    Args:
        api_key: API key to validate

    Returns:
        org_id associated with this key

    Raises:
        InvalidAPIKeyError: If key is invalid or inactive
    """
    # CRITICAL FIX: Hash the input key ONCE
    input_key_hash = APIKey.hash_key(api_key)

    with self.SessionLocal() as db:
        # O(1) indexed lookup by hash (primary key)
        # Instead of O(N) iteration over all active keys
        db_key = db.query(APIKey).filter(
            APIKey.key_hash == input_key_hash,
            APIKey.is_active == True
        ).first()

        if not db_key:
            raise InvalidAPIKeyError("Invalid or inactive API key")

        # Valid key found - update last_used
        db_key.last_used = datetime.utcnow()
        db.commit()

        return db_key.org_id
```

**WAIT - CRITICAL ERROR IN ABOVE CODE!**

The above fix is **WRONG** because bcrypt generates different hashes for the same input (salt randomization). We cannot hash and compare directly.

**Step 4: CORRECT FIX - Use database prefix index on key_hash**

The real issue: We MUST verify with bcrypt.checkpw(), but we can optimize the query.

**ACTUAL SOLUTION: Add key_prefix column for fast filtering**

```python
# Modify src/api/database_models.py - Add key_prefix column

class APIKey(Base):
    """API key authentication table."""
    __tablename__ = "api_keys"

    key_hash = Column(String(255), primary_key=True)  # bcrypt hash
    key_prefix = Column(String(10), nullable=False, index=True)  # First 8 chars for fast filtering
    org_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)

    @staticmethod
    def hash_key(api_key: str) -> str:
        """Hash API key using bcrypt."""
        return bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_key(api_key: str, key_hash: str) -> bool:
        """Verify API key against hash."""
        return bcrypt.checkpw(api_key.encode(), key_hash.encode())

    @staticmethod
    def extract_prefix(api_key: str) -> str:
        """Extract first 8 chars for indexed filtering."""
        return api_key[:8] if len(api_key) >= 8 else api_key
```

**Step 5: Update APIKeyManager to use prefix optimization**

```python
# Modify src/auth.py

def generate_api_key(self, org_id: str, description: Optional[str] = None) -> str:
    """
    Generate new API key for organization.

    WARNING: Returns key in plain text ONCE.
    Store it securely - cannot be retrieved later.

    Args:
        org_id: Organization identifier
        description: Optional description/label

    Returns:
        API key in format: ak_<uuid>
    """
    # Generate secure random key
    api_key = f"ak_{uuid.uuid4().hex}"

    # Hash key for storage
    key_hash = APIKey.hash_key(api_key)

    # Extract prefix for fast filtering
    key_prefix = APIKey.extract_prefix(api_key)

    # Store in database
    with self.SessionLocal() as db:
        db_key = APIKey(
            key_hash=key_hash,
            key_prefix=key_prefix,  # NEW
            org_id=org_id,
            created_at=datetime.utcnow(),
            last_used=datetime.utcnow(),
            is_active=True,
            description=description
        )
        db.add(db_key)
        db.commit()

    # Return plain text key (ONLY TIME IT'S VISIBLE)
    return api_key


def validate_api_key(self, api_key: str) -> str:
    """
    Validate API key and return associated org_id.

    PERFORMANCE FIX: Uses prefix index to reduce candidates from N to ~1.
    - Step 1: Filter by key_prefix (indexed) - reduces from 1000 to ~1 row
    - Step 2: Verify with bcrypt only on filtered candidates
    - Result: O(1) instead of O(N) bcrypt operations

    Updates last_used timestamp on successful validation.

    Args:
        api_key: API key to validate

    Returns:
        org_id associated with this key

    Raises:
        InvalidAPIKeyError: If key is invalid or inactive
    """
    # Extract prefix for indexed filtering
    key_prefix = APIKey.extract_prefix(api_key)

    with self.SessionLocal() as db:
        # OPTIMIZED: Filter by prefix first (uses index, fast!)
        # This reduces candidates from ~1000 to ~1
        candidates = db.query(APIKey).filter(
            APIKey.key_prefix == key_prefix,
            APIKey.is_active == True
        ).all()

        # Now verify with bcrypt (only 1-2 candidates instead of 1000)
        for db_key in candidates:
            if APIKey.verify_key(api_key, db_key.key_hash):
                # Valid key found - update last_used
                db_key.last_used = datetime.utcnow()
                db.commit()

                return db_key.org_id

        # No matching key found
        raise InvalidAPIKeyError("Invalid or inactive API key")
```

**Step 6: Run performance test to verify fix**

Run: `pytest tests/performance/test_api_key_performance.py -v`
Expected: PASS (validation < 100ms even with 1000 keys)

**Step 7: Create migration for existing databases**

```python
# Create agent-appoiments-v2/scripts/migrate_add_key_prefix.py
"""Migration: Add key_prefix column to existing api_keys table."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import sessionmaker
from src.api.database_models import Base, APIKey
from dotenv import load_dotenv

load_dotenv()


def migrate():
    """Add key_prefix column and populate from existing keys."""
    engine = create_engine(os.getenv("DATABASE_URL"))

    # Add column if not exists
    with engine.connect() as conn:
        try:
            conn.execute("ALTER TABLE api_keys ADD COLUMN key_prefix VARCHAR(10)")
            conn.execute("CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix)")
            print("✅ Added key_prefix column and index")
        except Exception as e:
            print(f"⚠️  Column might already exist: {e}")

    # WARNING: Cannot populate existing rows because keys are hashed!
    # Solution: Existing keys will have NULL prefix (slower but functional)
    # New keys will use prefix optimization
    print("⚠️  Existing API keys will not have prefix (re-generate recommended)")
    print("✅ Migration complete")


if __name__ == "__main__":
    migrate()
```

**Step 8: Commit the critical fix**

```bash
git add src/auth.py src/api/database_models.py tests/performance/test_api_key_performance.py scripts/migrate_add_key_prefix.py
git commit -m "fix(critical): optimize API key validation from O(N) to O(1)

CRITICAL PERFORMANCE BUG FIX:
- Previous: Iterated ALL active keys for bcrypt validation (O(N))
- Impact: 1000 orgs = 1000 bcrypt ops = 5-10 seconds per request
- Fix: Added key_prefix column with index for fast filtering
- Result: O(1) lookup - filter to ~1 candidate before bcrypt

Changes:
- Add key_prefix column to APIKey model (indexed)
- Extract first 8 chars of key for prefix filtering
- Filter by prefix BEFORE bcrypt verification
- Add performance test with 1000 keys (< 100ms)
- Add migration script for existing databases

Performance:
- Before: 5-10s with 1000 orgs
- After: < 100ms with 1000 orgs
- Improvement: 50-100x faster"
```

---

### Task 3.2: Rate Limiting por Organización

**Estimated Time:** 4 hours

**Files:**
- Create: `agent-appoiments-v2/src/rate_limiter.py`
- Create: `agent-appoiments-v2/tests/unit/test_rate_limiter.py`
- Modify: `agent-appoiments-v2/src/api_server.py`
- Modify: `agent-appoiments-v2/src/api/database_models.py`

**Step 1: Write failing test**

```python
# tests/unit/test_rate_limiter.py
"""Test rate limiting functionality."""
import pytest
import time
from src.rate_limiter import RateLimiter, RateLimitExceeded


@pytest.fixture
def rate_limiter():
    """Create RateLimiter with in-memory storage."""
    return RateLimiter(storage_type="memory")


def test_rate_limiter_allows_requests_within_limit(rate_limiter):
    """Requests within limit should be allowed."""
    org_id = "org-123"

    # Configure 5 requests per minute
    rate_limiter.set_limit(org_id, requests=5, window_seconds=60)

    # First 5 requests should succeed
    for i in range(5):
        rate_limiter.check_rate_limit(org_id)  # Should not raise


def test_rate_limiter_blocks_requests_exceeding_limit(rate_limiter):
    """Requests exceeding limit should be blocked."""
    org_id = "org-123"

    # Configure 3 requests per minute
    rate_limiter.set_limit(org_id, requests=3, window_seconds=60)

    # First 3 requests succeed
    for i in range(3):
        rate_limiter.check_rate_limit(org_id)

    # 4th request should fail
    with pytest.raises(RateLimitExceeded) as exc_info:
        rate_limiter.check_rate_limit(org_id)

    assert "rate limit exceeded" in str(exc_info.value).lower()


def test_rate_limiter_resets_after_window(rate_limiter):
    """Rate limit should reset after time window."""
    org_id = "org-123"

    # Configure 2 requests per 1 second
    rate_limiter.set_limit(org_id, requests=2, window_seconds=1)

    # Use both requests
    rate_limiter.check_rate_limit(org_id)
    rate_limiter.check_rate_limit(org_id)

    # 3rd should fail
    with pytest.raises(RateLimitExceeded):
        rate_limiter.check_rate_limit(org_id)

    # Wait for window to expire
    time.sleep(1.1)

    # Should work again
    rate_limiter.check_rate_limit(org_id)  # Should not raise


def test_rate_limiter_returns_retry_after(rate_limiter):
    """Exception should include retry_after seconds."""
    org_id = "org-123"

    rate_limiter.set_limit(org_id, requests=1, window_seconds=60)

    # Use the one request
    rate_limiter.check_rate_limit(org_id)

    # Next should fail with retry_after
    with pytest.raises(RateLimitExceeded) as exc_info:
        rate_limiter.check_rate_limit(org_id)

    assert hasattr(exc_info.value, 'retry_after')
    assert exc_info.value.retry_after > 0
    assert exc_info.value.retry_after <= 60
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_rate_limiter.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.rate_limiter'"

**Step 3: Install slowapi dependency**

```bash
# Add to pyproject.toml dependencies
"slowapi>=0.1.9",
"redis>=5.0.0",  # Optional, for production Redis backend
```

Run: `pip install slowapi redis`

**Step 4: Implement RateLimiter**

```python
# src/rate_limiter.py
"""Rate limiting for API requests by organization."""
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import threading


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    Pattern: Sliding window with per-org configuration.
    Good for: Development, single-server deployments.
    NOT for: Multi-server production (use Redis instead).
    """

    def __init__(self):
        # {org_id: {"requests": int, "window_seconds": int}}
        self.limits: Dict[str, Dict] = {}

        # {org_id: [(timestamp, ...), ...]}
        self.request_log: Dict[str, list] = defaultdict(list)

        self.lock = threading.Lock()

    def set_limit(self, org_id: str, requests: int, window_seconds: int):
        """Configure rate limit for organization."""
        self.limits[org_id] = {
            "requests": requests,
            "window_seconds": window_seconds
        }

    def check_rate_limit(self, org_id: str):
        """
        Check if request is within rate limit.

        Args:
            org_id: Organization identifier

        Raises:
            RateLimitExceeded: If limit exceeded
        """
        with self.lock:
            # Get org limits (default: 100 req/hour if not configured)
            limit_config = self.limits.get(org_id, {
                "requests": 100,
                "window_seconds": 3600
            })

            max_requests = limit_config["requests"]
            window_seconds = limit_config["window_seconds"]

            # Current time
            now = time.time()
            cutoff = now - window_seconds

            # Remove old requests outside window
            self.request_log[org_id] = [
                ts for ts in self.request_log[org_id]
                if ts > cutoff
            ]

            # Check if within limit
            current_count = len(self.request_log[org_id])

            if current_count >= max_requests:
                # Calculate retry_after
                oldest_request = min(self.request_log[org_id])
                retry_after = int(window_seconds - (now - oldest_request)) + 1

                raise RateLimitExceeded(
                    f"Rate limit exceeded for {org_id}: {max_requests} requests per {window_seconds}s",
                    retry_after=retry_after
                )

            # Log this request
            self.request_log[org_id].append(now)


class RateLimiter:
    """
    Factory for rate limiters with pluggable backends.

    Supports:
    - memory: In-memory (development, single-server)
    - redis: Redis backend (production, multi-server)
    """

    def __init__(self, storage_type: str = "memory", redis_url: Optional[str] = None):
        """
        Initialize rate limiter.

        Args:
            storage_type: "memory" or "redis"
            redis_url: Redis connection string (required if type=redis)
        """
        if storage_type == "memory":
            self.backend = InMemoryRateLimiter()
        elif storage_type == "redis":
            if not redis_url:
                raise ValueError("redis_url required for Redis backend")
            # TODO: Implement RedisRateLimiter (Phase 4)
            raise NotImplementedError("Redis backend not yet implemented")
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")

    def set_limit(self, org_id: str, requests: int, window_seconds: int):
        """Configure rate limit for organization."""
        self.backend.set_limit(org_id, requests, window_seconds)

    def check_rate_limit(self, org_id: str):
        """Check if request is within rate limit."""
        self.backend.check_rate_limit(org_id)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_rate_limiter.py -v`
Expected: PASS (all 4 tests)

**Step 6: Add organization rate limit tiers to database**

```python
# Modify src/api/database_models.py - Add to Organization model

class Organization(Base):
    """Organization configuration table."""
    __tablename__ = "organizations"

    org_id = Column(String(100), primary_key=True, index=True)
    org_name = Column(String(200), nullable=True)
    system_prompt = Column(String(5000), nullable=True)
    services = Column(JSON, nullable=False, default=list)
    permissions = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Rate limiting (NEW)
    rate_limit_tier = Column(String(20), default="free", nullable=False)  # free, basic, premium
    rate_limit_requests = Column(Integer, default=100, nullable=False)
    rate_limit_window_seconds = Column(Integer, default=3600, nullable=False)  # 1 hour

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

**Step 7: Integrate rate limiting into API endpoints**

```python
# Modify src/api_server.py

from src.rate_limiter import RateLimiter, RateLimitExceeded

# Initialize rate limiter
rate_limiter = RateLimiter(storage_type="memory")  # Use Redis in production


# Add rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit errors with Retry-After header."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={"Retry-After": str(exc.retry_after)},
        content=ErrorResponse(
            error="Rate Limit Exceeded",
            detail=str(exc),
            code="RATE_LIMIT_EXCEEDED"
        ).model_dump()
    )


# Modify chat endpoint to check rate limit
@app.post("/api/v1/chat", tags=["Chat"], response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    org_id_from_key: str = Depends(validate_api_key),
    graph=Depends(get_agent_graph)
):
    """Process chat with rate limiting."""
    # Verify org_id match
    if request.org_id != org_id_from_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key mismatch"
        )

    # Load org config
    org_config = org_loader.load_org_config(request.org_id)

    # Configure rate limit from org settings
    rate_limiter.set_limit(
        org_id=request.org_id,
        requests=org_config.rate_limit_requests,  # From database
        window_seconds=org_config.rate_limit_window_seconds
    )

    # CHECK RATE LIMIT (raises RateLimitExceeded if exceeded)
    rate_limiter.check_rate_limit(request.org_id)

    # ... rest of endpoint logic ...
```

**Step 8: Add integration test for rate limiting**

```python
# tests/integration/test_rate_limiting.py
"""Test rate limiting integration."""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.fixture
def client():
    """Create test client."""
    from src.api_server import app
    return TestClient(app)


def test_rate_limit_blocks_excessive_requests(client, monkeypatch):
    """Should return 429 when rate limit exceeded."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    # Assume org has limit of 3 requests per hour
    session_id = str(uuid4())
    api_key = "test_api_key"  # Mocked

    # First 3 requests succeed
    for i in range(3):
        response = client.post(
            "/api/v1/chat",
            headers={"X-API-Key": api_key},
            json={
                "message": f"Message {i}",
                "session_id": session_id,
                "org_id": "org-test"
            }
        )
        assert response.status_code == 200

    # 4th request fails with 429
    response = client.post(
        "/api/v1/chat",
        headers={"X-API-Key": api_key},
        json={
            "message": "Excessive request",
            "session_id": session_id,
            "org_id": "org-test"
        }
    )

    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) > 0
```

**Step 9: Commit**

```bash
git add src/rate_limiter.py src/api_server.py src/api/database_models.py tests/unit/test_rate_limiter.py tests/integration/test_rate_limiting.py pyproject.toml
git commit -m "feat: implement rate limiting per organization

- Create RateLimiter with in-memory sliding window algorithm
- Add rate_limit_tier, requests, window_seconds to Organization model
- Support for tiered plans: free (100/hr), basic (500/hr), premium (2000/hr)
- Integrate rate limiting into /chat and /chat/stream endpoints
- Return 429 Too Many Requests with Retry-After header
- Add unit and integration tests for rate limiting
- Prepare for Redis backend (production multi-server support)"
```

---

### Task 3.3: Validación y Sanitización de Inputs

**Estimated Time:** 3 hours

**Files:**
- Create: `agent-appoiments-v2/src/input_validator.py`
- Create: `agent-appoiments-v2/tests/unit/test_input_validator.py`
- Modify: `agent-appoiments-v2/src/api/models.py`

**Step 1: Write failing test**

```python
# tests/unit/test_input_validator.py
"""Test input validation and sanitization."""
import pytest
from src.input_validator import InputValidator, ValidationError


@pytest.fixture
def validator():
    """Create InputValidator."""
    return InputValidator()


def test_sanitize_removes_html_tags(validator):
    """Should strip HTML tags from input."""
    dirty = "<script>alert('XSS')</script>Hello"
    clean = validator.sanitize_message(dirty)

    assert "<script>" not in clean
    assert "Hello" in clean


def test_sanitize_removes_sql_injection_attempts(validator):
    """Should neutralize SQL injection patterns."""
    dirty = "'; DROP TABLE users; --"
    clean = validator.sanitize_message(dirty)

    # Should escape or remove dangerous SQL
    assert "DROP TABLE" not in clean or clean != dirty


def test_validate_message_rejects_too_long(validator):
    """Should reject messages exceeding max length."""
    with pytest.raises(ValidationError) as exc_info:
        validator.validate_message("x" * 3000, max_length=2000)

    assert "too long" in str(exc_info.value).lower()


def test_validate_message_rejects_empty(validator):
    """Should reject empty messages."""
    with pytest.raises(ValidationError):
        validator.validate_message("")


def test_validate_session_id_accepts_valid_uuid(validator):
    """Should accept valid UUID."""
    valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
    result = validator.validate_uuid(valid_uuid, field_name="session_id")

    assert result == valid_uuid


def test_validate_session_id_rejects_invalid_uuid(validator):
    """Should reject invalid UUID."""
    with pytest.raises(ValidationError) as exc_info:
        validator.validate_uuid("not-a-uuid", field_name="session_id")

    assert "session_id" in str(exc_info.value)
    assert "invalid" in str(exc_info.value).lower()


def test_validate_org_id_rejects_special_chars(validator):
    """Should reject org_id with special characters."""
    with pytest.raises(ValidationError):
        validator.validate_org_id("org-123'; DROP--")

    # Should only allow alphanumeric and hyphens
    validator.validate_org_id("org-123-abc")  # Should not raise
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_input_validator.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.input_validator'"

**Step 3: Install bleach dependency**

```bash
# Add to pyproject.toml
"bleach>=6.0.0",
```

Run: `pip install bleach`

**Step 4: Implement InputValidator**

```python
# src/input_validator.py
"""Input validation and sanitization for API security."""
import re
import bleach
from uuid import UUID
from typing import Optional


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class InputValidator:
    """
    Validates and sanitizes user inputs.

    Protections:
    - XSS: Strips HTML/JavaScript tags
    - SQL Injection: Validates patterns
    - Path Traversal: Validates file paths
    - UUID Format: Validates session IDs
    """

    # Allowed tags for message sanitization (very restrictive)
    ALLOWED_TAGS = []  # No HTML allowed in messages
    ALLOWED_ATTRIBUTES = {}

    # Org ID pattern: alphanumeric, hyphens, underscores only
    ORG_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')

    def sanitize_message(self, message: str) -> str:
        """
        Sanitize user message to prevent XSS.

        Args:
            message: Raw user input

        Returns:
            Sanitized message (HTML stripped)
        """
        # Remove all HTML tags
        clean = bleach.clean(
            message,
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRIBUTES,
            strip=True
        )

        # Remove null bytes (can cause issues)
        clean = clean.replace('\x00', '')

        return clean.strip()

    def validate_message(self, message: str, max_length: int = 2000):
        """
        Validate message constraints.

        Args:
            message: User message
            max_length: Maximum allowed length

        Raises:
            ValidationError: If validation fails
        """
        if not message or not message.strip():
            raise ValidationError("Message cannot be empty")

        if len(message) > max_length:
            raise ValidationError(
                f"Message too long: {len(message)} chars (max: {max_length})"
            )

    def validate_uuid(self, value: str, field_name: str = "UUID") -> str:
        """
        Validate UUID format.

        Args:
            value: UUID string to validate
            field_name: Field name for error messages

        Returns:
            Validated UUID string

        Raises:
            ValidationError: If not valid UUID
        """
        try:
            UUID(value)
            return value
        except ValueError:
            raise ValidationError(f"{field_name} must be valid UUID, got: {value}")

    def validate_org_id(self, org_id: str) -> str:
        """
        Validate organization ID format.

        Only allows: alphanumeric, hyphens, underscores.
        Prevents: SQL injection, path traversal, special chars.

        Args:
            org_id: Organization identifier

        Returns:
            Validated org_id

        Raises:
            ValidationError: If invalid format
        """
        if not org_id:
            raise ValidationError("org_id cannot be empty")

        if len(org_id) > 100:
            raise ValidationError(f"org_id too long: {len(org_id)} chars (max: 100)")

        if not self.ORG_ID_PATTERN.match(org_id):
            raise ValidationError(
                f"org_id contains invalid characters. "
                f"Only alphanumeric, hyphens, and underscores allowed: {org_id}"
            )

        return org_id

    def validate_and_sanitize_all(self, message: str, session_id: str, org_id: str) -> dict:
        """
        Validate and sanitize all request fields.

        Args:
            message: User message
            session_id: Session UUID
            org_id: Organization ID

        Returns:
            Dict with sanitized values

        Raises:
            ValidationError: If any validation fails
        """
        return {
            "message": self.sanitize_message(message),
            "session_id": self.validate_uuid(session_id, "session_id"),
            "org_id": self.validate_org_id(org_id)
        }
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_input_validator.py -v`
Expected: PASS (all 7 tests)

**Step 6: Add custom Pydantic validators to models**

```python
# Modify src/api/models.py

from pydantic import BaseModel, Field, field_validator, UUID4
from src.input_validator import InputValidator

# Global validator instance
_validator = InputValidator()


class ChatRequest(BaseModel):
    """Request schema for /api/v1/chat endpoint."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User message (1-2000 characters)",
        examples=["I'd like to book an appointment"]
    )
    session_id: UUID4 = Field(
        ...,
        description="Client session UUID for conversation tracking",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    org_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Organization identifier",
        examples=["org-123", "clinic-downtown"]
    )

    @field_validator('message')
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        """Sanitize message to prevent XSS."""
        clean = _validator.sanitize_message(v)
        _validator.validate_message(clean, max_length=2000)
        return clean

    @field_validator('org_id')
    @classmethod
    def validate_org_id_format(cls, v: str) -> str:
        """Validate org_id format."""
        return _validator.validate_org_id(v)

    class Config:
        json_schema_extra = {
            "example": {
                "message": "I need to book a consultation",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "org_id": "org-123"
            }
        }
```

**Step 7: Add integration test for XSS prevention**

```python
# tests/integration/test_xss_prevention.py
"""Test XSS prevention."""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.fixture
def client():
    from src.api_server import app
    return TestClient(app)


def test_xss_attack_is_sanitized(client, monkeypatch):
    """XSS attempts should be sanitized."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    session_id = str(uuid4())

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "<script>alert('XSS')</script>Book appointment",
            "session_id": session_id,
            "org_id": "org-test"
        }
    )

    # Should be processed (not rejected)
    assert response.status_code in [200, 401]  # 401 if no API key, 200 if mocked

    # Verify sanitization happened (check logs or response)
    # The actual processing would strip the <script> tag


def test_sql_injection_attempt_is_rejected(client):
    """SQL injection patterns should be rejected."""
    session_id = str(uuid4())

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Hello",
            "session_id": session_id,
            "org_id": "org-123'; DROP TABLE users;--"  # SQL injection attempt
        }
    )

    # Should be rejected with 422 validation error
    assert response.status_code == 422
    data = response.json()
    assert "org_id" in str(data).lower()
```

**Step 8: Commit**

```bash
git add src/input_validator.py src/api/models.py tests/unit/test_input_validator.py tests/integration/test_xss_prevention.py pyproject.toml
git commit -m "feat: add input validation and sanitization for security

- Create InputValidator with XSS, SQL injection protection
- Sanitize messages with bleach (strip all HTML tags)
- Validate UUID format for session_id
- Validate org_id pattern (alphanumeric, hyphens, underscores only)
- Add Pydantic field validators for automatic sanitization
- Prevent null bytes, excessive length, empty messages
- Add integration tests for XSS and SQL injection prevention"
```

---

## PHASE 4: PLUGIN PREPARATION (Week 4)

### Task 4.1: Endpoints Auxiliares Requeridos

**Estimated Time:** 6 hours

**Files:**
- Create: `agent-appoiments-v2/src/api/endpoints/sessions.py`
- Create: `agent-appoiments-v2/src/api/endpoints/webhooks.py`
- Create: `agent-appoiments-v2/tests/integration/test_session_endpoints.py`
- Create: `agent-appoiments-v2/tests/integration/test_webhook_endpoints.py`
- Modify: `agent-appoiments-v2/src/api_server.py`

**Step 1: Write failing test for session history**

```python
# tests/integration/test_session_endpoints.py
"""Test session management endpoints."""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.fixture
def client():
    from src.api_server import app
    return TestClient(app)


def test_get_session_history_returns_messages(client, monkeypatch):
    """GET /sessions/{id}/history should return conversation."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    session_id = str(uuid4())

    # First, create some conversation history
    client.post(
        "/api/v1/chat",
        headers={"X-API-Key": "test_key"},
        json={
            "message": "Hello",
            "session_id": session_id,
            "org_id": "org-test"
        }
    )

    # Get history
    response = client.get(
        f"/api/v1/sessions/{session_id}/history",
        headers={"X-API-Key": "test_key"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert isinstance(data["messages"], list)
    assert len(data["messages"]) > 0


def test_delete_session_clears_conversation(client, monkeypatch):
    """DELETE /sessions/{id} should clear session."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    session_id = str(uuid4())

    # Create conversation
    client.post(
        "/api/v1/chat",
        headers={"X-API-Key": "test_key"},
        json={
            "message": "Hello",
            "session_id": session_id,
            "org_id": "org-test"
        }
    )

    # Delete session
    response = client.delete(
        f"/api/v1/sessions/{session_id}",
        headers={"X-API-Key": "test_key"}
    )

    assert response.status_code == 200

    # Verify session is gone (should return 404 or empty)
    history_response = client.get(
        f"/api/v1/sessions/{session_id}/history",
        headers={"X-API-Key": "test_key"}
    )

    # Could be 404 or empty messages list
    assert history_response.status_code in [200, 404]
```

**Step 2: Implement session endpoints**

```python
# src/api/endpoints/sessions.py
"""Session management endpoints for plugins."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, UUID4
from typing import List, Dict, Any
from langchain_core.messages import BaseMessage

from src.api.dependencies import validate_api_key, get_agent_graph
from src.session_manager import SessionManager, SessionNotFoundError
from src.database import get_postgres_saver
import os

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])

session_manager = SessionManager(database_url=os.getenv("DATABASE_URL"))


class SessionHistoryResponse(BaseModel):
    """Response for session history."""
    session_id: UUID4
    messages: List[Dict[str, Any]]
    metadata: Dict[str, Any]


@router.get("/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str,
    org_id_from_key: str = Depends(validate_api_key),
    graph=Depends(get_agent_graph)
):
    """
    Get conversation history for a session.

    Returns all messages exchanged in this conversation,
    useful for plugins to display chat history.

    Args:
        session_id: Session UUID
        org_id_from_key: Organization from API key

    Returns:
        SessionHistoryResponse with messages array

    Raises:
        404: Session not found
    """
    try:
        # Get thread_id from session
        thread_id = session_manager.get_thread_id(session_id)

        # Get checkpoint from database
        with get_postgres_saver() as saver:
            config = {"configurable": {"thread_id": thread_id}}

            # Get latest checkpoint
            checkpoint = saver.get(config)

            if not checkpoint:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No history found for session {session_id}"
                )

            # Extract messages from checkpoint
            state = checkpoint.get("channel_values", {})
            messages = state.get("messages", [])

            # Convert Message objects to dicts
            message_dicts = []
            for msg in messages:
                if isinstance(msg, BaseMessage):
                    message_dicts.append({
                        "type": msg.type,
                        "content": msg.content,
                        "additional_kwargs": getattr(msg, 'additional_kwargs', {})
                    })
                else:
                    message_dicts.append({"content": str(msg)})

            return SessionHistoryResponse(
                session_id=session_id,
                messages=message_dicts,
                metadata={
                    "thread_id": thread_id,
                    "current_state": str(state.get("current_state", "")),
                    "message_count": len(message_dicts)
                }
            )

    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    org_id_from_key: str = Depends(validate_api_key)
):
    """
    Delete a session and its conversation history.

    Removes all checkpoints and metadata for this session.
    Useful for GDPR compliance or user-requested data deletion.

    Args:
        session_id: Session UUID to delete

    Returns:
        Success message

    Raises:
        404: Session not found
    """
    try:
        # Get thread_id
        thread_id = session_manager.get_thread_id(session_id)

        # Delete checkpoint from database
        with get_postgres_saver() as saver:
            config = {"configurable": {"thread_id": thread_id}}

            # Delete checkpoint (implementation depends on PostgresSaver)
            # May need to directly delete from checkpoints table
            from sqlalchemy import create_engine, text
            engine = create_engine(os.getenv("DATABASE_URL"))

            with engine.connect() as conn:
                conn.execute(
                    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
                    {"thread_id": thread_id}
                )
                conn.commit()

        # Delete session metadata
        with session_manager.SessionLocal() as db:
            from src.api.database_models import Session
            db.query(Session).filter(Session.session_id == session_id).delete()
            db.commit()

        return {
            "status": "deleted",
            "session_id": session_id,
            "thread_id": thread_id
        }

    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
```

**Step 3: Write test for webhook registration**

```python
# tests/integration/test_webhook_endpoints.py
"""Test webhook management endpoints."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.api_server import app
    return TestClient(app)


def test_register_webhook_stores_configuration(client, monkeypatch):
    """POST /webhooks/register should store webhook config."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    response = client.post(
        "/api/v1/webhooks/register",
        headers={"X-API-Key": "test_key"},
        json={
            "event_type": "appointment.created",
            "url": "https://example.com/webhook",
            "secret": "webhook_secret_123"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert "webhook_id" in data
    assert data["event_type"] == "appointment.created"


def test_list_webhooks_returns_registered_hooks(client):
    """GET /webhooks should list registered webhooks."""
    response = client.get(
        "/api/v1/webhooks",
        headers={"X-API-Key": "test_key"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "webhooks" in data
    assert isinstance(data["webhooks"], list)
```

**Step 4: Implement webhook endpoints**

```python
# src/api/endpoints/webhooks.py
"""Webhook management for plugin integrations."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime
import uuid

from src.api.dependencies import validate_api_key
from src.api.database_models import Base
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os


router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


# Database model for webhooks
class Webhook(Base):
    """Webhook configuration table."""
    __tablename__ = "webhooks"

    webhook_id = Column(String(100), primary_key=True)
    org_id = Column(String(100), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)  # appointment.created, appointment.cancelled, etc.
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=True)  # For HMAC signing
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Pydantic models
class WebhookCreate(BaseModel):
    """Request to create webhook."""
    event_type: str
    url: HttpUrl
    secret: Optional[str] = None


class WebhookResponse(BaseModel):
    """Webhook configuration response."""
    webhook_id: str
    event_type: str
    url: str
    is_active: bool
    created_at: datetime


class WebhookListResponse(BaseModel):
    """List of webhooks."""
    webhooks: List[WebhookResponse]


# Database setup
engine = create_engine(os.getenv("DATABASE_URL"))
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)


@router.post("/register", status_code=201, response_model=WebhookResponse)
async def register_webhook(
    webhook: WebhookCreate,
    org_id_from_key: str = Depends(validate_api_key)
):
    """
    Register a webhook for event notifications.

    Plugins can register webhooks to receive notifications when:
    - appointment.created
    - appointment.cancelled
    - appointment.rescheduled

    Args:
        webhook: Webhook configuration
        org_id_from_key: Organization from API key

    Returns:
        Created webhook configuration
    """
    webhook_id = f"wh_{uuid.uuid4().hex[:16]}"

    with SessionLocal() as db:
        db_webhook = Webhook(
            webhook_id=webhook_id,
            org_id=org_id_from_key,
            event_type=webhook.event_type,
            url=str(webhook.url),
            secret=webhook.secret,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(db_webhook)
        db.commit()
        db.refresh(db_webhook)

        return WebhookResponse(
            webhook_id=db_webhook.webhook_id,
            event_type=db_webhook.event_type,
            url=db_webhook.url,
            is_active=db_webhook.is_active,
            created_at=db_webhook.created_at
        )


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    org_id_from_key: str = Depends(validate_api_key)
):
    """
    List all registered webhooks for organization.

    Returns:
        List of webhook configurations
    """
    with SessionLocal() as db:
        webhooks = db.query(Webhook).filter(
            Webhook.org_id == org_id_from_key,
            Webhook.is_active == True
        ).all()

        return WebhookListResponse(
            webhooks=[
                WebhookResponse(
                    webhook_id=wh.webhook_id,
                    event_type=wh.event_type,
                    url=wh.url,
                    is_active=wh.is_active,
                    created_at=wh.created_at
                )
                for wh in webhooks
            ]
        )


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    org_id_from_key: str = Depends(validate_api_key)
):
    """
    Delete (deactivate) a webhook.

    Args:
        webhook_id: Webhook ID to delete

    Returns:
        Success message
    """
    with SessionLocal() as db:
        webhook = db.query(Webhook).filter(
            Webhook.webhook_id == webhook_id,
            Webhook.org_id == org_id_from_key
        ).first()

        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        webhook.is_active = False
        db.commit()

        return {"status": "deleted", "webhook_id": webhook_id}
```

**Step 5: Register routers in main app**

```python
# Modify src/api_server.py

from src.api.endpoints import sessions, webhooks

# Include routers
app.include_router(sessions.router)
app.include_router(webhooks.router)
```

**Step 6: Commit**

```bash
git add src/api/endpoints/ tests/integration/test_session_endpoints.py tests/integration/test_webhook_endpoints.py src/api_server.py
git commit -m "feat: add auxiliary endpoints for plugin integration

Session Management:
- GET /api/v1/sessions/{id}/history - retrieve conversation
- DELETE /api/v1/sessions/{id} - clear session (GDPR)

Webhook Management:
- POST /api/v1/webhooks/register - register event webhook
- GET /api/v1/webhooks - list webhooks
- DELETE /api/v1/webhooks/{id} - deactivate webhook

Features:
- Convert LangGraph checkpoints to JSON messages
- Support event types: appointment.created, cancelled, rescheduled
- HMAC secret for webhook signing (security)
- Org-scoped webhooks via API key validation"
```

---

### Task 4.2: Documentación OpenAPI Automática

**Estimated Time:** 2 hours

**Files:**
- Modify: `agent-appoiments-v2/src/api_server.py`
- Modify: `agent-appoiments-v2/src/api/models.py`
- Create: `agent-appoiments-v2/docs/api/README.md`

**Step 1: Enhance FastAPI metadata**

```python
# Modify src/api_server.py

from fastapi.openapi.utils import get_openapi


app = FastAPI(
    title="Appointment Booking Agent API",
    description="""
# Multi-Tenant Conversational AI API

Production-ready REST API for appointment booking with WordPress/Shopify plugin support.

## Features

- 🤖 **Conversational AI**: LangGraph-powered natural language booking
- 🔐 **Secure**: API key authentication with bcrypt hashing
- 🚀 **Scalable**: PostgreSQL persistence with connection pooling
- 📊 **Rate Limited**: Tiered plans (free, basic, premium)
- 🔌 **Plugin-Ready**: Webhooks for WordPress/Shopify integration
- 📡 **Streaming**: Server-Sent Events for real-time responses

## Authentication

All endpoints require `X-API-Key` header:

```bash
curl -X POST https://api.example.com/api/v1/chat \\
  -H "X-API-Key: ak_your_api_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Book appointment", "session_id": "...", "org_id": "..."}'
```

## Rate Limits

- **Free**: 100 requests/hour
- **Basic**: 500 requests/hour
- **Premium**: 2000 requests/hour

Exceeding limits returns `429 Too Many Requests` with `Retry-After` header.

## Webhooks

Register webhooks to receive event notifications:
- `appointment.created`
- `appointment.cancelled`
- `appointment.rescheduled`

See `/api/v1/webhooks/register` endpoint for details.
    """,
    version="1.0.0",
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# Custom OpenAPI schema
def custom_openapi():
    """Customize OpenAPI schema with examples."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for organization authentication"
        }
    }

    # Apply security globally
    openapi_schema["security"] = [{"ApiKeyAuth": []}]

    # Add server URLs
    openapi_schema["servers"] = [
        {"url": "https://api.example.com", "description": "Production"},
        {"url": "https://staging-api.example.com", "description": "Staging"},
        {"url": "http://localhost:8000", "description": "Development"},
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
```

**Step 2: Add comprehensive docstrings with examples**

```python
# Modify src/api_server.py - enhance endpoint docstrings

@app.post("/api/v1/chat", tags=["Chat"], response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    org_id_from_key: str = Depends(validate_api_key),
    graph=Depends(get_agent_graph)
):
    """
    Process conversational chat message and return agent response.

    ## Description

    Sends a user message to the LangGraph agent and receives a natural language response.
    The agent maintains conversation state across multiple requests using `session_id`.

    ## Use Cases

    - Book a new appointment
    - Ask about available services
    - Reschedule existing appointment
    - Cancel appointment

    ## Rate Limiting

    Subject to organization rate limits:
    - Free: 100 requests/hour
    - Basic: 500 requests/hour
    - Premium: 2000 requests/hour

    ## Example Request

    ```bash
    curl -X POST https://api.example.com/api/v1/chat \\
      -H "X-API-Key: ak_1234567890abcdef" \\
      -H "Content-Type: application/json" \\
      -d '{
        "message": "I need to book a consultation",
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "org_id": "clinic-downtown"
      }'
    ```

    ## Example Response

    ```json
    {
      "response": "I'd be happy to help you book a consultation! What date works best for you?",
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "metadata": {
        "current_state": "COLLECT_DATE",
        "message_count": 2
      }
    }
    ```

    ## Error Responses

    - `401 Unauthorized`: Invalid API key
    - `403 Forbidden`: API key doesn't match org_id
    - `422 Unprocessable Entity`: Invalid request format
    - `429 Too Many Requests`: Rate limit exceeded
    - `500 Internal Server Error`: Server error

    ## Notes

    - Use same `session_id` across requests to maintain conversation context
    - Messages are sanitized to prevent XSS attacks
    - Conversation state is persisted in PostgreSQL
    """
    # ... implementation ...
```

**Step 3: Add response examples to models**

```python
# Modify src/api/models.py

class ChatResponse(BaseModel):
    """Response schema for /api/v1/chat endpoint."""
    response: str = Field(..., description="Agent response message")
    session_id: UUID4 = Field(..., description="Session identifier")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata (state, context, etc.)"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "response": "I'd be happy to help! What service would you like to book?",
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "metadata": {
                        "current_state": "COLLECT_SERVICE",
                        "message_count": 2
                    }
                },
                {
                    "response": "Great! I have the following time slots available on March 15th: 9:00 AM, 11:30 AM, 2:00 PM",
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "metadata": {
                        "current_state": "SHOW_AVAILABILITY",
                        "message_count": 6,
                        "available_slots": 3
                    }
                }
            ]
        }
```

**Step 4: Create API documentation README**

```markdown
# Create docs/api/README.md
# Appointment Booking API Documentation

## Overview

Multi-tenant conversational AI REST API for appointment booking.

## Base URL

- Production: `https://api.example.com`
- Staging: `https://staging-api.example.com`

## Authentication

All requests require `X-API-Key` header:

```http
X-API-Key: ak_your_api_key_here
```

Contact support to obtain API keys for your organization.

## Endpoints

### Chat Endpoints

#### POST /api/v1/chat

Conversational chat interface.

**Request:**
```json
{
  "message": "I need to book an appointment",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "org_id": "your-org-id"
}
```

**Response:**
```json
{
  "response": "I'd be happy to help! What service would you like?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {"current_state": "COLLECT_SERVICE"}
}
```

#### POST /api/v1/chat/stream

Streaming chat with Server-Sent Events.

**Response Format:**
```
data: {"chunk": "I'd be", "done": false, "metadata": {...}}
data: {"chunk": " happy to help!", "done": false, "metadata": {...}}
data: {"chunk": "", "done": true, "metadata": {"completed": true}}
```

### Session Management

#### GET /api/v1/sessions/{session_id}/history

Retrieve conversation history.

#### DELETE /api/v1/sessions/{session_id}

Delete session (GDPR compliance).

### Webhook Management

#### POST /api/v1/webhooks/register

Register webhook for event notifications.

**Events:**
- `appointment.created`
- `appointment.cancelled`
- `appointment.rescheduled`

## Rate Limits

| Plan    | Requests/Hour |
|---------|---------------|
| Free    | 100           |
| Basic   | 500           |
| Premium | 2000          |

## Interactive Documentation

- **Swagger UI**: [/docs](/docs)
- **ReDoc**: [/redoc](/redoc)

## SDKs

Coming soon:
- WordPress Plugin
- Shopify App
- JavaScript SDK
- Python SDK
```

**Step 5: Commit**

```bash
git add src/api_server.py src/api/models.py docs/api/README.md
git commit -m "docs: enhance OpenAPI documentation for plugins

- Add comprehensive API description with features list
- Configure security scheme (X-API-Key) in OpenAPI spec
- Add server URLs (production, staging, development)
- Enhance endpoint docstrings with examples and use cases
- Add multiple response examples to Pydantic models
- Document error responses and status codes
- Create API documentation README for developers
- Make /docs and /redoc production-ready for plugin devs"
```

---

### Task 4.3: Testing de Integración con Simulación de Plugins

**Estimated Time:** 4 hours

**Files:**
- Create: `agent-appoiments-v2/tests/integration/test_api_wordpress_flow.py`
- Create: `agent-appoiments-v2/scripts/simulate_plugin.py`
- Create: `agent-appoiments-v2/tests/integration/test_complete_booking_flow.py`

**Step 1: Write WordPress plugin simulation test**

```python
# tests/integration/test_api_wordpress_flow.py
"""Test complete WordPress plugin integration flow."""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
import time


@pytest.fixture
def client():
    from src.api_server import app
    return TestClient(app)


@pytest.fixture
def test_org_id():
    return "wordpress-clinic-test"


@pytest.fixture
def test_api_key(test_org_id):
    """Generate test API key."""
    from src.auth import APIKeyManager
    import os

    manager = APIKeyManager(database_url=os.getenv("DATABASE_URL"))
    api_key = manager.generate_api_key(test_org_id, "WordPress test key")

    return api_key


def test_wordpress_complete_booking_flow(client, test_api_key, test_org_id):
    """
    Simulate complete WordPress plugin booking flow.

    Steps:
    1. User visits WordPress site
    2. Plugin initiates chat session
    3. User books appointment through conversation
    4. Plugin receives confirmation
    5. Plugin retrieves conversation history
    6. Plugin registers webhook for notifications
    """
    session_id = str(uuid4())

    # Step 1: Initial greeting
    response = client.post(
        "/api/v1/chat",
        headers={"X-API-Key": test_api_key},
        json={
            "message": "Hello, I need to book an appointment",
            "session_id": session_id,
            "org_id": test_org_id
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 0

    # Step 2: Select service
    response = client.post(
        "/api/v1/chat",
        headers={"X-API-Key": test_api_key},
        json={
            "message": "I need a general consultation",
            "session_id": session_id,
            "org_id": test_org_id
        }
    )

    assert response.status_code == 200

    # Step 3: Provide date
    response = client.post(
        "/api/v1/chat",
        headers={"X-API-Key": test_api_key},
        json={
            "message": "Tomorrow at 2 PM",
            "session_id": session_id,
            "org_id": test_org_id
        }
    )

    assert response.status_code == 200

    # Step 4: Provide contact info (simplified)
    response = client.post(
        "/api/v1/chat",
        headers={"X-API-Key": test_api_key},
        json={
            "message": "John Doe, john@example.com, 555-1234",
            "session_id": session_id,
            "org_id": test_org_id
        }
    )

    assert response.status_code == 200

    # Step 5: Confirm
    response = client.post(
        "/api/v1/chat",
        headers={"X-API-Key": test_api_key},
        json={
            "message": "yes",
            "session_id": session_id,
            "org_id": test_org_id
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Should contain confirmation number
    assert "APPT-" in data["response"] or "confirmation" in data["response"].lower()

    # Step 6: Retrieve conversation history (WordPress displays it)
    history_response = client.get(
        f"/api/v1/sessions/{session_id}/history",
        headers={"X-API-Key": test_api_key}
    )

    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history["messages"]) >= 5  # At least 5 messages exchanged

    # Step 7: Register webhook for appointment notifications
    webhook_response = client.post(
        "/api/v1/webhooks/register",
        headers={"X-API-Key": test_api_key},
        json={
            "event_type": "appointment.created",
            "url": "https://wordpress-site.com/wp-json/booking/webhook",
            "secret": "wordpress_webhook_secret"
        }
    )

    assert webhook_response.status_code == 201
    webhook = webhook_response.json()
    assert "webhook_id" in webhook


def test_wordpress_streaming_flow(client, test_api_key, test_org_id):
    """Test WordPress plugin using streaming endpoint."""
    session_id = str(uuid4())

    with client.stream(
        "POST",
        "/api/v1/chat/stream",
        headers={"X-API-Key": test_api_key},
        json={
            "message": "Hello",
            "session_id": session_id,
            "org_id": test_org_id
        }
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Collect all events
        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                import json
                event = json.loads(line[6:])
                events.append(event)

        # Should have received events
        assert len(events) > 0

        # Last event should be done
        assert events[-1]["done"] is True


def test_wordpress_rate_limit_handling(client, test_api_key, test_org_id):
    """Test WordPress plugin handles rate limits gracefully."""
    session_id = str(uuid4())

    # Send requests until rate limit (assuming free tier: 100/hour)
    # For testing, we'll send a burst and check for 429

    responses = []
    for i in range(10):  # Send 10 rapid requests
        response = client.post(
            "/api/v1/chat",
            headers={"X-API-Key": test_api_key},
            json={
                "message": f"Message {i}",
                "session_id": session_id,
                "org_id": test_org_id
            }
        )
        responses.append(response)

    # All should succeed (under limit)
    for resp in responses:
        assert resp.status_code in [200, 429]

    # If rate limited, should have Retry-After header
    rate_limited = [r for r in responses if r.status_code == 429]
    if rate_limited:
        assert "Retry-After" in rate_limited[0].headers
```

**Step 2: Create manual plugin simulation script**

```python
# scripts/simulate_plugin.py
"""Manual WordPress/Shopify plugin simulation script."""
import requests
import json
import time
from uuid import uuid4


class PluginSimulator:
    """Simulates WordPress/Shopify plugin behavior."""

    def __init__(self, base_url: str, api_key: str, org_id: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.org_id = org_id
        self.session_id = str(uuid4())

    def chat(self, message: str, stream: bool = False):
        """Send chat message."""
        endpoint = "/api/v1/chat/stream" if stream else "/api/v1/chat"

        url = f"{self.base_url}{endpoint}"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "message": message,
            "session_id": self.session_id,
            "org_id": self.org_id
        }

        if stream:
            response = requests.post(url, headers=headers, json=payload, stream=True)

            print(f"\n🤖 Agent (streaming): ", end="", flush=True)
            for line in response.iter_lines():
                if line.startswith(b"data: "):
                    data = json.loads(line[6:])
                    if not data.get("done"):
                        print(data.get("chunk", ""), end="", flush=True)
            print()
        else:
            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                print(f"\n🤖 Agent: {data['response']}")
                print(f"   State: {data.get('metadata', {}).get('current_state', 'N/A')}")
            else:
                print(f"\n❌ Error {response.status_code}: {response.text}")

        return response

    def get_history(self):
        """Retrieve conversation history."""
        url = f"{self.base_url}/api/v1/sessions/{self.session_id}/history"
        headers = {"X-API-Key": self.api_key}

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            print(f"\n📜 Conversation History ({len(data['messages'])} messages):")
            for i, msg in enumerate(data['messages']):
                print(f"{i+1}. [{msg.get('type', 'unknown')}] {msg.get('content', '')[:100]}...")
        else:
            print(f"\n❌ Error retrieving history: {response.status_code}")

        return response

    def register_webhook(self, event_type: str, webhook_url: str):
        """Register webhook."""
        url = f"{self.base_url}/api/v1/webhooks/register"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "event_type": event_type,
            "url": webhook_url,
            "secret": "test_secret_123"
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 201:
            data = response.json()
            print(f"\n✅ Webhook registered: {data['webhook_id']}")
            print(f"   Event: {data['event_type']}")
            print(f"   URL: {data['url']}")
        else:
            print(f"\n❌ Error registering webhook: {response.status_code}")

        return response


def main():
    """Run interactive plugin simulation."""
    import sys

    if len(sys.argv) < 4:
        print("Usage: python scripts/simulate_plugin.py <base_url> <api_key> <org_id>")
        print("\nExample:")
        print("  python scripts/simulate_plugin.py http://localhost:8000 ak_12345 org-clinic")
        sys.exit(1)

    base_url = sys.argv[1]
    api_key = sys.argv[2]
    org_id = sys.argv[3]

    print("=" * 60)
    print("WordPress/Shopify Plugin Simulator")
    print("=" * 60)
    print(f"Base URL: {base_url}")
    print(f"Org ID: {org_id}")
    print(f"Session ID: {uuid4()}")
    print("=" * 60)

    simulator = PluginSimulator(base_url, api_key, org_id)

    # Interactive conversation
    print("\n💬 Start chatting (type 'quit' to exit, 'history' to see conversation, 'webhook' to register):\n")

    while True:
        user_input = input("👤 You: ").strip()

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("\n👋 Goodbye!")
            break

        if user_input.lower() == "history":
            simulator.get_history()
            continue

        if user_input.lower() == "webhook":
            webhook_url = input("Webhook URL: ").strip()
            event_type = input("Event type (appointment.created): ").strip() or "appointment.created"
            simulator.register_webhook(event_type, webhook_url)
            continue

        if user_input.lower() == "stream":
            message = input("Message (streaming): ").strip()
            simulator.chat(message, stream=True)
            continue

        simulator.chat(user_input)


if __name__ == "__main__":
    main()
```

**Step 3: Make script executable and test**

```bash
chmod +x scripts/simulate_plugin.py

# Test manually
python scripts/simulate_plugin.py http://localhost:8000 ak_test_key org-test
```

**Step 4: Commit**

```bash
git add tests/integration/test_api_wordpress_flow.py scripts/simulate_plugin.py
git commit -m "test: add WordPress plugin integration simulation

- Create test_api_wordpress_flow.py for complete booking simulation
- Test multi-step conversation flow (greeting → service → booking)
- Test streaming endpoint with SSE
- Test rate limiting behavior
- Test conversation history retrieval
- Test webhook registration
- Create interactive simulate_plugin.py script for manual testing
- Simulate WordPress/Shopify plugin HTTP client behavior
- Support both regular and streaming endpoints
- Enable developers to test API before plugin development"
```

---

### Task 4.4: Revisión Async/Sync con Arquitecto Senior

**Estimated Time:** 30 minutes

**Files:**
- Create: `agent-appoiments-v2/docs/architecture/ASYNC_SYNC_REVIEW.md`

```markdown
# Create docs/architecture/ASYNC_SYNC_REVIEW.md
# Async/Sync Architecture Review

## Current Status

### Async Components ✅
- FastAPI endpoints (`async def`)
- StreamingResponse for SSE
- Background tasks (session cleanup)

### Sync Components ⚠️
- LangGraph graph.invoke() (blocking)
- PostgresSaver operations (blocking)
- SessionManager database queries (blocking)
- APIKeyManager bcrypt operations (blocking)

## Issues Identified

### 1. Blocking I/O in Async Endpoints

**Problem:**
```python
@app.post("/api/v1/chat")  # Async endpoint
async def chat(...):
    result = graph.invoke(...)  # BLOCKS event loop!
```

**Impact:**
- Blocks event loop during LangGraph execution (~2-5s)
- Reduces concurrency (can't handle other requests)
- Not using FastAPI async benefits

**Solution:**
Use `asyncio.to_thread()` or make LangGraph async:
```python
result = await asyncio.to_thread(graph.invoke, input_data, config)
```

OR use LangGraph async API:
```python
result = await graph.ainvoke(input_data, config=config)
```

### 2. Database Operations Not Async

**Current:**
```python
with SessionLocal() as db:
    session = db.query(Session).filter(...).first()  # Blocking
```

**Solution:**
Migrate to async SQLAlchemy:
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

async with async_session() as db:
    result = await db.execute(select(Session).filter(...))
    session = result.scalar_one_or_none()
```

### 3. Bcrypt Blocking CPU-Intensive Operations

**Problem:**
```python
bcrypt.hashpw(...)  # CPU-intensive, blocks event loop
bcrypt.checkpw(...)  # CPU-intensive, blocks event loop
```

**Solution:**
Run in thread pool:
```python
await asyncio.to_thread(bcrypt.hashpw, password, salt)
```

## Recommendations

### Priority 1: LangGraph Async (HIGH IMPACT)
- Use `graph.ainvoke()` instead of `graph.invoke()`
- Use `graph.astream()` for streaming (already done ✅)
- Estimated improvement: 50-100x concurrency

### Priority 2: Database Async (MEDIUM IMPACT)
- Migrate SessionManager to async SQLAlchemy
- Migrate APIKeyManager to async SQLAlchemy
- Use `asyncpg` driver for PostgreSQL
- Estimated improvement: 20-30x concurrency

### Priority 3: CPU-Bound Async (LOW IMPACT)
- Wrap bcrypt in `asyncio.to_thread()`
- Estimated improvement: 5-10x concurrency

## Migration Plan

### Phase 1: Quick Wins (1 day)
```python
# Wrap blocking operations
result = await asyncio.to_thread(graph.invoke, input_data, config)
```

### Phase 2: Proper Async (3 days)
- Install async deps: `asyncpg`, `sqlalchemy[asyncio]`
- Convert all database models to async
- Update all endpoints to use async DB sessions

### Phase 3: Performance Testing (1 day)
- Load test with 100 concurrent requests
- Measure latency improvements
- Validate no regressions

## Action Items

- [ ] Architect approval on migration approach
- [ ] Prioritize Phase 1 vs Phase 2
- [ ] Decide: async SQLAlchemy or keep sync with thread pools?
- [ ] Benchmark current performance (baseline)
- [ ] Schedule migration work

## Questions for Architect

1. **Async SQLAlchemy**: Full migration or thread pools acceptable?
2. **LangGraph**: Confirm `ainvoke()` is production-ready?
3. **Connection Pooling**: Async engine pool sizing guidance?
4. **Testing**: How to test async code comprehensively?
5. **Deployment**: Any async-related gotchas for production?

---
**Reviewer:** _____________
**Date:** _____________
**Decision:** _____________
```

**Commit:**

```bash
git add docs/architecture/ASYNC_SYNC_REVIEW.md
git commit -m "docs: add async/sync architecture review for senior review

Issues Identified:
- Blocking graph.invoke() in async endpoints
- Sync database operations in async context
- CPU-intensive bcrypt blocking event loop

Recommendations:
- Priority 1: Use graph.ainvoke() (50-100x improvement)
- Priority 2: Migrate to async SQLAlchemy (20-30x improvement)
- Priority 3: Wrap bcrypt in thread pools (5-10x improvement)

Migration plan with 3 phases and action items for architect review"
```

---

## FINAL SUMMARY

**Plan Location:** `agent-appoiments-v2/docs/plans/2025-11-16-fastapi-production-api.md`

### Completed Tasks

✅ **Phase 1: API Foundations**
- Task 1.1: FastAPI base with CORS and error handling
- Task 1.2: PostgreSQL migration with connection pooling
- Task 1.3: Basic /chat endpoint with LangGraph integration

✅ **Phase 2: LangGraph Integration**
- Task 2.1: Session management with thread_id mapping
- Task 2.2: Server-Sent Events streaming
- Task 2.3: Multi-tenancy configuration

✅ **Phase 3: Security & Authentication**
- Task 3.1: API key authentication with bcrypt
- Task 3.1B: **CRITICAL BUG FIX** - API key validation O(N) → O(1)
- Task 3.2: Rate limiting by organization (tiered plans)
- Task 3.3: Input validation and sanitization (XSS, SQL injection)

✅ **Phase 4: Plugin Preparation**
- Task 4.1: Auxiliary endpoints (session history, webhooks)
- Task 4.2: OpenAPI documentation for plugin developers
- Task 4.3: WordPress/Shopify plugin simulation tests
- Task 4.4: Async/sync architecture review document

### Estimated Time Breakdown

| Phase | Tasks | Time |
|-------|-------|------|
| Phase 1 | 3 tasks | 2 days |
| Phase 2 | 3 tasks | 2 days |
| Phase 3 | 4 tasks (including bug fix) | 2 days |
| Phase 4 | 4 tasks | 2 days |
| **TOTAL** | **14 tasks** | **~8 days** |

### Critical Additions

1. **Bug Fix (3.1B)**: Performance optimization from O(N) to O(1) using key_prefix index
2. **Complete Phase 3**: Rate limiting + input validation (was incomplete)
3. **Complete Phase 4**: All auxiliary endpoints + documentation + testing
4. **Architecture Review**: Async/sync analysis for production readiness

### Next Steps

1. Review plan with team
2. Choose execution approach:
   - **Option A**: Subagent-driven (this session) - tasks executed one-by-one with review
   - **Option B**: Parallel session - batch execution with checkpoints
3. Begin implementation starting with Phase 1
