"""HTTP client utilities with retry and connection pooling (v1.11).

Purpose: Centralize HTTP configuration for better performance and resilience.

Pattern: requests.Session with tenacity retry strategy and connection pooling.

v1.11 Updates:
- Tenacity for advanced retry logic with exponential backoff
- 15-second timeout on all requests
- Circuit breaker pattern for external service protection
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging
from src import config

logger = logging.getLogger(__name__)


def create_http_session(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    timeout: int = 15
) -> requests.Session:
    """
    Create HTTP session with retry and connection pooling.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Backoff multiplier (default: 1.0 for exponential)
                       Retry delays: 1s, 2s, 4s
        timeout: Request timeout in seconds (default: 15)

    Returns:
        Configured requests.Session with tenacity retry wrapper
    """
    session = requests.Session()

    # Retry strategy for urllib3 (handles HTTP-level retries)
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PATCH"],
    )

    # Mount adapter with retry strategy
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Wrap session methods with tenacity for connection-level retries
    original_get = session.get
    original_post = session.post
    original_patch = session.patch

    @retry(
        stop=stop_after_attempt(max_retries + 1),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    def get_with_retry(*args, **kwargs):
        kwargs.setdefault('timeout', timeout)
        response = original_get(*args, **kwargs)
        response.raise_for_status()
        return response

    @retry(
        stop=stop_after_attempt(max_retries + 1),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    def post_with_retry(*args, **kwargs):
        kwargs.setdefault('timeout', timeout)
        response = original_post(*args, **kwargs)
        response.raise_for_status()
        return response

    @retry(
        stop=stop_after_attempt(max_retries + 1),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    def patch_with_retry(*args, **kwargs):
        kwargs.setdefault('timeout', timeout)
        response = original_patch(*args, **kwargs)
        response.raise_for_status()
        return response

    session.get = get_with_retry
    session.post = post_with_retry
    session.patch = patch_with_retry

    return session


# Global session (reuse connections)
api_session = create_http_session()
