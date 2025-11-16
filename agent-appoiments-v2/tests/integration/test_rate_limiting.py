"""Tests for rate limiting (v1.11)."""
import pytest
import requests
import time
from multiprocessing import Process
from mock_api import app
import os
import signal


@pytest.fixture(scope="module")
def api_server():
    """Start mock API server for testing."""
    def run_server():
        app.run(port=5001, debug=False, use_reloader=False)

    server = Process(target=run_server)
    server.start()
    time.sleep(2)  # Wait for server to start

    yield "http://localhost:5001"

    # Cleanup
    os.kill(server.pid, signal.SIGTERM)
    server.join(timeout=5)


class TestRateLimiting:
    """Test rate limiting behavior."""

    def test_rate_limiting_enforced(self, api_server):
        """Should enforce 10 requests per minute limit."""
        success_count = 0
        rate_limited_count = 0

        # Make 15 requests - some should be rate limited
        for i in range(15):
            response = requests.get(f"{api_server}/services")
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                rate_limited_count += 1

        # Should have allowed exactly 10 requests
        assert success_count == 10, f"Expected 10 successful requests, got {success_count}"
        # Should have rate-limited the rest
        assert rate_limited_count == 5, f"Expected 5 rate-limited requests, got {rate_limited_count}"

    def test_resets_after_minute(self, api_server):
        """Should reset counter after 1 minute."""
        # Hit rate limit
        for i in range(11):
            requests.get(f"{api_server}/services")

        # Wait for reset
        time.sleep(61)

        # Should work again
        response = requests.get(f"{api_server}/services")
        assert response.status_code == 200

    def test_hourly_limit(self, api_server):
        """Should enforce 100 requests per hour limit."""
        # This is a longer test - verify limit exists
        # In practice, we'd mock time or use smaller limits for testing

        # Make requests with small delays to stay under per-minute limit
        # but hit hourly limit
        success_count = 0
        for i in range(105):
            if i > 0 and i % 10 == 0:
                time.sleep(60)  # Wait to reset minute counter

            response = requests.get(f"{api_server}/services")
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                break

        # Should hit hourly limit before completing all requests
        assert success_count <= 100

    def test_different_endpoints_share_limit(self, api_server):
        """Should apply rate limit across all endpoints."""
        # Mix of different endpoints
        for i in range(5):
            requests.get(f"{api_server}/services")
        for i in range(5):
            requests.get(f"{api_server}/health")

        # 11th request to any endpoint should fail
        response = requests.get(f"{api_server}/availability?service_id=srv-001&date_from=2025-01-20")
        assert response.status_code == 429
