"""Tests for HTTP client resilience features (v1.11)."""
import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from src.http_client import create_http_session


class TestTenacityRetries:
    """Test exponential backoff retry behavior."""

    def test_retries_on_connection_error(self):
        """Should retry 3 times on connection errors with exponential backoff."""
        # Patch at the requests module level before session creation
        with patch('requests.Session.request') as mock_request:
            # Simulate connection failures
            mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")

            session = create_http_session()

            # Should raise after retries exhausted
            with pytest.raises(requests.exceptions.ConnectionError):
                session.get("http://test.com/api")

            # Verify 4 attempts (1 initial + 3 retries)
            assert mock_request.call_count == 4

    def test_retries_on_timeout(self):
        """Should retry on timeout errors."""
        with patch('requests.Session.request') as mock_request:
            mock_request.side_effect = requests.exceptions.Timeout("Request timeout")

            session = create_http_session()

            with pytest.raises(requests.exceptions.Timeout):
                session.get("http://test.com/api")

            assert mock_request.call_count == 4

    def test_retries_on_503_service_unavailable(self):
        """Should retry on 503 status code."""
        with patch('requests.Session.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("503 Service Unavailable")
            mock_request.return_value = mock_response

            session = create_http_session()

            with pytest.raises(requests.exceptions.HTTPError):
                session.get("http://test.com/api")

            assert mock_request.call_count == 4

    def test_exponential_backoff_delays(self):
        """Should use exponential backoff: 1s, 2s, 4s."""
        import time

        with patch('requests.Session.request') as mock_request:
            mock_request.side_effect = requests.exceptions.ConnectionError("Failed")

            session = create_http_session()

            start = time.time()
            with pytest.raises(requests.exceptions.ConnectionError):
                session.get("http://test.com/api")
            elapsed = time.time() - start

            # Total delay should be ~7s (1 + 2 + 4)
            # Allow 20% tolerance for test execution overhead
            assert 5.6 <= elapsed <= 8.4, f"Expected ~7s, got {elapsed:.2f}s"

    def test_success_on_second_attempt(self):
        """Should succeed if retry succeeds."""
        with patch('requests.Session.request') as mock_request:
            # First call fails, second succeeds
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status.return_value = None

            mock_request.side_effect = [
                requests.exceptions.ConnectionError("Failed"),
                mock_response
            ]

            session = create_http_session()

            response = session.get("http://test.com/api")

            assert response.status_code == 200
            assert mock_request.call_count == 2
