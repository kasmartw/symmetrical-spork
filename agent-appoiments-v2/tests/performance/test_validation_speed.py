"""Performance tests for validation tools."""
import pytest
import time
from src.tools import validate_email_tool, validate_phone_tool


class TestValidationPerformance:
    """Test that validation is fast (< 100ms)."""

    def test_email_validation_is_fast(self):
        """Email validation should complete in < 100ms."""
        start = time.perf_counter()

        result = validate_email_tool.invoke({"email": "test@example.com"})

        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100, f"Email validation took {elapsed_ms:.2f}ms"

    def test_phone_validation_is_fast(self):
        """Phone validation should complete in < 100ms."""
        start = time.perf_counter()

        result = validate_phone_tool.invoke({"phone": "555-123-4567"})

        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100, f"Phone validation took {elapsed_ms:.2f}ms"

    def test_cached_validation_is_instant(self):
        """Second validation of same input should be instant (< 10ms)."""
        from src.cache import ValidationCache

        cache = ValidationCache()

        # First call
        cache.validate_email("test@example.com")

        # Second call (should be cached)
        start = time.perf_counter()
        cache.validate_email("test@example.com")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 10, f"Cached validation took {elapsed_ms:.2f}ms"
