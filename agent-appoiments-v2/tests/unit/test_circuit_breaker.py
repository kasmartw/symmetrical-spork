"""Tests for circuit breaker pattern (v1.11)."""
import pytest
import time
from src.circuit_breaker import CircuitBreaker, CircuitBreakerOpen


class TestCircuitBreaker:
    """Test circuit breaker behavior."""

    def test_allows_requests_when_closed(self):
        """Should allow requests when circuit is closed."""
        cb = CircuitBreaker(failure_threshold=3, timeout=1)

        def successful_call():
            return "success"

        result = cb.call(successful_call)
        assert result == "success"
        assert cb.state == "closed"

    def test_opens_after_threshold_failures(self):
        """Should open circuit after 3 consecutive failures."""
        cb = CircuitBreaker(failure_threshold=3, timeout=1)

        def failing_call():
            raise Exception("API failed")

        # First 3 failures should be attempted
        for i in range(3):
            with pytest.raises(Exception):
                cb.call(failing_call)

        # Circuit should now be open
        assert cb.state == "open"

        # Next call should fail immediately without attempting
        with pytest.raises(CircuitBreakerOpen):
            cb.call(failing_call)

    def test_transitions_to_half_open_after_timeout(self):
        """Should transition to half-open state after timeout."""
        cb = CircuitBreaker(failure_threshold=3, timeout=1)

        def failing_call():
            raise Exception("Failed")

        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                cb.call(failing_call)

        assert cb.state == "open"

        # Wait for timeout
        time.sleep(1.1)

        # Next call should attempt (half-open)
        with pytest.raises(Exception):
            cb.call(failing_call)

        # Should be open again after failed half-open attempt
        assert cb.state == "open"

    def test_closes_on_successful_half_open_attempt(self):
        """Should close circuit on successful half-open attempt."""
        cb = CircuitBreaker(failure_threshold=3, timeout=1)

        call_count = [0]

        def conditional_call():
            call_count[0] += 1
            if call_count[0] <= 3:
                raise Exception("Failed")
            return "success"

        # Open circuit
        for i in range(3):
            with pytest.raises(Exception):
                cb.call(conditional_call)

        assert cb.state == "open"

        # Wait for timeout
        time.sleep(1.1)

        # Successful half-open attempt
        result = cb.call(conditional_call)
        assert result == "success"
        assert cb.state == "closed"

    def test_resets_failure_count_on_success(self):
        """Should reset failure count after successful call."""
        cb = CircuitBreaker(failure_threshold=3, timeout=1)

        def failing_call():
            raise Exception("Failed")

        def successful_call():
            return "success"

        # 2 failures
        for i in range(2):
            with pytest.raises(Exception):
                cb.call(failing_call)

        # 1 success - should reset
        cb.call(successful_call)

        # 2 more failures - shouldn't open (count reset)
        for i in range(2):
            with pytest.raises(Exception):
                cb.call(failing_call)

        assert cb.state == "closed"
