"""Test that all tools have descriptive docstrings."""
import pytest
from src.tools import (
    validate_email_tool,
    validate_phone_tool,
    get_services_tool,
    fetch_and_cache_availability_tool,
    filter_and_show_availability_tool,
    create_appointment_tool,
)
from src.tools_appointment_mgmt import (
    cancel_appointment_tool,
    get_appointment_tool,
    reschedule_appointment_tool,
)


def test_all_tools_have_docstrings():
    """Verify all tools have non-empty docstrings."""
    tools = [
        validate_email_tool,
        validate_phone_tool,
        get_services_tool,
        fetch_and_cache_availability_tool,
        filter_and_show_availability_tool,
        create_appointment_tool,
        cancel_appointment_tool,
        get_appointment_tool,
        reschedule_appointment_tool,
    ]

    for tool in tools:
        # LangChain tools have description attribute
        desc = tool.description if hasattr(tool, 'description') else tool.__doc__
        assert desc is not None, f"{tool.name} missing description"
        assert len(desc) > 30, f"{tool.name} description too short: {desc}"


def test_tools_have_when_to_use_guidance():
    """Verify critical tools explain WHEN to use them (for LLM)."""
    # These tools need "when to use" guidance
    critical_tools = [
        (validate_email_tool, ["IMMEDIATELY", "Call"]),
        (validate_phone_tool, ["IMMEDIATELY", "Call"]),
        (fetch_and_cache_availability_tool, ["IMMEDIATELY", "Call", "BEFORE"]),
        (filter_and_show_availability_tool, ["AFTER", "Call"]),
        (create_appointment_tool, ["ONLY AFTER", "Call"]),
    ]

    for tool, expected_phrases in critical_tools:
        desc = tool.description if hasattr(tool, 'description') else tool.__doc__
        assert any(phrase in desc for phrase in expected_phrases), \
            f"{tool.name} description missing 'when to use' guidance. Got: {desc[:100]}"
