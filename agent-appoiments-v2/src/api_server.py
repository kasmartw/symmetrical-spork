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
