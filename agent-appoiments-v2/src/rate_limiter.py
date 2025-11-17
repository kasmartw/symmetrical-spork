"""Rate limiting for API requests by organization."""
import time
from typing import Dict
from collections import defaultdict
import threading


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    Pattern: Sliding window with per-org configuration.
    Good for: Development, single-server deployments.
    NOT for: Multi-server production (use Redis instead).
    """

    def __init__(self):
        # {org_id: {"requests": int, "window_seconds": int}}
        self.limits: Dict[str, Dict] = {}

        # {org_id: [timestamp1, timestamp2, ...]}
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

    def get_limit_info(self, org_id: str) -> Dict:
        """Get current rate limit status for org."""
        with self.lock:
            limit_config = self.limits.get(org_id, {
                "requests": 100,
                "window_seconds": 3600
            })

            now = time.time()
            cutoff = now - limit_config["window_seconds"]

            # Clean old requests
            self.request_log[org_id] = [
                ts for ts in self.request_log[org_id]
                if ts > cutoff
            ]

            current_count = len(self.request_log[org_id])

            return {
                "limit": limit_config["requests"],
                "remaining": max(0, limit_config["requests"] - current_count),
                "reset_in": limit_config["window_seconds"]
            }
