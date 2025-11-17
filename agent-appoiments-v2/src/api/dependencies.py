"""FastAPI dependency injection functions."""
import os
from functools import lru_cache
from fastapi import Header, HTTPException, status
from src.agent import create_production_graph
from src.auth import APIKeyManager, InvalidAPIKeyError
from src.rate_limiter import RateLimiter, RateLimitExceeded


@lru_cache(maxsize=1)
def get_agent_graph():
    """
    Get compiled LangGraph agent (cached singleton).

    Pattern: Create graph once, reuse across requests.
    Graph compilation is expensive (~500ms), so we cache it.

    Returns:
        Compiled StateGraph with PostgreSQL checkpointer
    """
    return create_production_graph()


# Initialize singletons
_api_key_manager = None
_rate_limiter = None


def get_api_key_manager() -> APIKeyManager:
    """Get or create API key manager singleton."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager(
            database_url=os.getenv("DATABASE_URL", "sqlite:///sessions.db")
        )
    return _api_key_manager


def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
        # Set default limits (can be customized per org)
        # Default: 100 requests/hour per organization
    return _rate_limiter


async def validate_api_key(x_api_key: str = Header(..., description="API Key")) -> str:
    """
    FastAPI dependency for API key validation.

    Validates X-API-Key header and returns org_id.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        org_id associated with the API key

    Raises:
        HTTPException 401: If API key invalid
    """
    try:
        manager = get_api_key_manager()
        org_id = manager.validate_api_key(x_api_key)
        return org_id
    except InvalidAPIKeyError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "ApiKey"}
        )


async def check_rate_limit(org_id: str) -> None:
    """
    FastAPI dependency for rate limit checking.

    Args:
        org_id: Organization identifier (from request or API key)

    Raises:
        HTTPException 429: If rate limit exceeded
    """
    try:
        limiter = get_rate_limiter()
        limiter.check_rate_limit(org_id)
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)}
        )
