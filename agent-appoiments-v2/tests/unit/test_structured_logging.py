"""Tests for structured logging (v1.11)."""
import pytest
import json
import logging
from io import StringIO
from src.logging_config import setup_structured_logging, get_logger, generate_request_id


class TestStructuredLogging:
    """Test structured logging with request IDs."""

    def test_setup_configures_structlog(self):
        """Should configure structlog processors."""
        setup_structured_logging(log_level="INFO")
        logger = get_logger(__name__)

        # Logger should be a structlog BoundLogger
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')

    def test_logger_methods_work(self):
        """Should have working log methods."""
        setup_structured_logging(log_level="INFO")
        logger = get_logger(__name__)

        # These should not raise
        logger.info("Test info message")
        logger.warning("Test warning")
        logger.error("Test error")

    def test_generate_request_id_format(self):
        """Should generate request IDs with correct format."""
        request_id = generate_request_id()

        # Should start with "req-"
        assert request_id.startswith("req-")

        # Should have hex chars after prefix
        assert len(request_id) == 16  # "req-" (4) + 12 hex chars

        # Should be unique
        request_id2 = generate_request_id()
        assert request_id != request_id2

    def test_request_id_middleware_adds_header(self):
        """Should add X-Request-ID header to responses."""
        from src.logging_config import RequestIDMiddleware
        from flask import Flask

        app = Flask(__name__)

        @app.route('/test')
        def test_route():
            return "OK"

        # Wrap with middleware
        app.wsgi_app = RequestIDMiddleware(app.wsgi_app)

        # Test request
        with app.test_client() as client:
            response = client.get('/test')

            # Should have request ID header
            assert 'X-Request-ID' in response.headers
            request_id = response.headers['X-Request-ID']

            # Should match format
            assert request_id.startswith('req-')
            assert len(request_id) == 16
