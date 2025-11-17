"""Test rate limiting functionality."""
import pytest
import time
from src.rate_limiter import RateLimiter, RateLimitExceeded


@pytest.fixture
def rate_limiter():
    """Create RateLimiter with in-memory storage."""
    return RateLimiter()


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
