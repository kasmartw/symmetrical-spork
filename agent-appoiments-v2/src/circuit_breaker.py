"""Circuit breaker pattern for external service protection (v1.11).

Purpose: Prevent cascading failures by failing fast when external service is down.

Pattern: Three states (closed, open, half-open) with failure threshold and timeout.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service failing, requests fail immediately (fail fast)
- HALF_OPEN: Testing if service recovered, allow one request
"""
import time
import logging
from typing import Callable, Any
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open (fail fast)."""
    pass


class CircuitBreaker:
    """Circuit breaker for external service calls."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting half-open
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self._state = CircuitState.CLOSED

    @property
    def state(self) -> str:
        """Get current state as string."""
        return self._state.value

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to call
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is open (fail fast)
            Exception: If function raises exception
        """
        # Check if circuit should transition to half-open
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise CircuitBreakerOpen(
                    f"Circuit breaker is OPEN. "
                    f"Retry after {self._time_until_retry():.1f}s"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time passed to attempt half-open."""
        if self.last_failure_time is None:
            return True

        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.timeout

    def _time_until_retry(self) -> float:
        """Calculate seconds until retry allowed."""
        if self.last_failure_time is None:
            return 0

        elapsed = time.time() - self.last_failure_time
        return max(0, self.timeout - elapsed)

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            logger.info("Circuit breaker closed after successful half-open attempt")

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker opened after failed half-open attempt")
        elif self.failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker opened after {self.failure_count} failures. "
                f"Timeout: {self.timeout}s"
            )
