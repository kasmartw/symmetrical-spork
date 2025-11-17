"""FastAPI dependency injection functions."""
import os
from functools import lru_cache
from fastapi import Header, HTTPException, status
from src.agent import create_production_graph
from src.auth import APIKeyManager, InvalidAPIKeyError


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


# Initialize API key manager (singleton)
_api_key_manager = None


def get_api_key_manager() -> APIKeyManager:
    """Get or create API key manager singleton."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager(
            database_url=os.getenv("DATABASE_URL", "sqlite:///sessions.db")
        )
    return _api_key_manager


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
