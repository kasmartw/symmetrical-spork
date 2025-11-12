"""LangSmith tracing configuration (v1.2).

Enables:
- Full conversation tracing
- Node-by-node timing
- Tool call tracking
- Error tracking
"""
import os
from typing import Optional


def setup_langsmith_tracing(
    project_name: str = "appointment-agent-v1.2",
    enabled: Optional[bool] = None
):
    """
    Configure LangSmith tracing.

    Args:
        project_name: LangSmith project name
        enabled: Override enable/disable (defaults to env var)

    Environment Variables:
        LANGCHAIN_TRACING_V2: Set to "true" to enable
        LANGCHAIN_API_KEY: Your LangSmith API key
        LANGCHAIN_PROJECT: Project name (overrides parameter)
    """
    # Check if tracing should be enabled
    if enabled is None:
        enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"

    if not enabled:
        print("ℹ️  LangSmith tracing disabled")
        return

    # Verify API key
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("⚠️  LANGCHAIN_API_KEY not set - tracing disabled")
        return

    # Set environment variables
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", project_name)

    print(f"✅ LangSmith tracing enabled - Project: {os.environ['LANGCHAIN_PROJECT']}")


def get_trace_url(run_id: str) -> str:
    """
    Get LangSmith trace URL for a run.

    Args:
        run_id: Run ID from invocation

    Returns:
        URL to view trace
    """
    project = os.getenv("LANGCHAIN_PROJECT", "appointment-agent-v1.2")
    return f"https://smith.langchain.com/o/projects/p/{project}/r/{run_id}"
