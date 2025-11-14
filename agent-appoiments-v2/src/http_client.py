"""HTTP client utilities with retry and connection pooling (v1.7).

Purpose: Centralize HTTP configuration for better performance and resilience.

Pattern: requests.Session with retry strategy and connection pooling.
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src import config


def create_http_session(
    max_retries: int = 3,
    backoff_factor: float = 0.3,
    timeout: int = 5
) -> requests.Session:
    """
    Create HTTP session with retry and connection pooling.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Backoff multiplier (default: 0.3)
                       Retry delays: 0.3s, 0.6s, 1.2s
        timeout: Request timeout in seconds (default: 5)

    Returns:
        Configured requests.Session
    """
    session = requests.Session()

    # Retry strategy
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP codes
        allowed_methods=["GET", "POST", "PATCH"],  # Retry these methods
    )

    # Mount adapter with retry strategy
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,  # Connection pool size
        pool_maxsize=10,      # Max connections in pool
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


# Global session (reuse connections)
api_session = create_http_session()
