"""FastAPI dependency injection functions."""
from functools import lru_cache
from src.agent import create_production_graph


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
