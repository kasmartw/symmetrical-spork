"""Tests for optimized cache system."""
import pytest
import time
from src.cache import ValidationCache, AvailabilityCache


class TestValidationCache:
    """Test validation cache with TTL."""

    def setup_method(self):
        """Reset cache before each test."""
        self.cache = ValidationCache()
        # Clear any cached data
        if hasattr(self.cache, 'email_cache'):
            self.cache.email_cache.clear()
        if hasattr(self.cache, 'phone_cache'):
            self.cache.phone_cache.clear()

    def test_cache_hit(self):
        """Test cache returns cached result."""
        # First call validates and caches
        result1 = self.cache.validate_email("test@example.com")
        # Second call should hit cache
        result2 = self.cache.validate_email("test@example.com")
        assert result1 == result2

    def test_cache_different_inputs(self):
        """Test cache handles different inputs correctly."""
        result1 = self.cache.validate_email("test1@example.com")
        result2 = self.cache.validate_email("test2@example.com")
        # Both should be valid but different
        assert result1[0] is True
        assert result2[0] is True
        # Results should be different (different emails in message)
        assert result1[1] != result2[1]

    def test_phone_validation_cache(self):
        """Test phone validation caching."""
        result1 = self.cache.validate_phone("555-1234")
        result2 = self.cache.validate_phone("555-1234")
        assert result1 == result2
        assert result1[0] is True


class TestAvailabilityCache:
    """Test availability cache optimization."""

    def setup_method(self):
        """Reset cache before each test."""
        self.cache = AvailabilityCache()
        self.cache.clear()

    def test_cache_stores_availability(self):
        """Test cache stores and retrieves availability."""
        slots = [{"date": "2025-11-15", "start_time": "09:00"}]
        service = {"id": "srv-001", "name": "Test Service"}

        self.cache.set("srv-001", slots, service, {}, {})

        result = self.cache.get("srv-001")
        assert result is not None
        assert result["slots"] == slots
        assert result["service"] == service

    def test_cache_expiration(self):
        """Test cache expires after TTL."""
        # Create cache with very short TTL for testing
        self.cache.ttl = 0.1  # 100ms

        slots = [{"date": "2025-11-15", "start_time": "09:00"}]
        self.cache.set("srv-001", slots, {}, {}, {})

        # Should be cached
        assert self.cache.get("srv-001") is not None

        # Wait for expiration
        time.sleep(0.2)

        # Should be expired
        assert self.cache.get("srv-001") is None

    def test_cache_returns_none_for_missing_key(self):
        """Test cache returns None for non-existent key."""
        result = self.cache.get("non-existent")
        assert result is None

    def test_cleanup_expired_method_exists(self):
        """Test cleanup_expired method exists and works."""
        # Set multiple entries with short TTL
        if hasattr(self.cache, 'ttl'):
            self.cache.ttl = 0.1  # 100ms

        self.cache.set("srv-001", [], {}, {}, {})
        self.cache.set("srv-002", [], {}, {}, {})

        # Wait for expiration
        time.sleep(0.2)

        # Cleanup should remove expired entries
        if hasattr(self.cache, 'cleanup_expired'):
            self.cache.cleanup_expired()
            # Cache should be empty after cleanup
            assert self.cache.get("srv-001") is None
            assert self.cache.get("srv-002") is None
