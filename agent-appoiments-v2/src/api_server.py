"""FastAPI production server for appointment booking agent.

Features:
- CORS middleware for WordPress/Shopify integration
- Global exception handling
- Health check endpoint
- Structured logging
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from langchain_core.messages import HumanMessage

from src.api.models import ErrorResponse, ChatRequest, ChatResponse
from src.api.dependencies import get_agent_graph

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown logic."""
    from src.database import init_database, close_connection_pool

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
