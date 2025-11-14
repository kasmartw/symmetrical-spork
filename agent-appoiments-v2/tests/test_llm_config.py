"""Test LLM configuration is properly set."""
import pytest
from src.agent import llm


def test_llm_configuration():
    """Verify LLM has optimal configuration for consistency."""
    # Check model
    assert llm.model_name == "gpt-4o-mini"

    # Check temperature for consistency
    assert llm.temperature == 0.2, "Temperature should be 0.2 for consistent responses"

    # Check max tokens to avoid long responses
    assert llm.max_tokens == 200, "max_tokens should limit response length"

    # Check timeout settings
    assert llm.request_timeout == 15, "Should have 15s timeout"
