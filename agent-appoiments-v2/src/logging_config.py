"""Structured logging configuration (v1.11).

Purpose: JSON-formatted logs with request tracing for observability.

Pattern: structlog with standard library integration.
"""
import structlog
import logging
import sys
from typing import Any


def setup_structured_logging(log_level: str = "INFO"):
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get logger instance with structured logging.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Request ID utilities
import uuid

def generate_request_id() -> str:
    """Generate unique request ID."""
    return f"req-{uuid.uuid4().hex[:12]}"


class RequestIDMiddleware:
    """Flask middleware to add request IDs."""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # Generate request ID
        request_id = generate_request_id()
        environ['REQUEST_ID'] = request_id

        # Add to response headers
        def custom_start_response(status, headers, exc_info=None):
            headers.append(('X-Request-ID', request_id))
            return start_response(status, headers, exc_info)

        return self.app(environ, custom_start_response)
