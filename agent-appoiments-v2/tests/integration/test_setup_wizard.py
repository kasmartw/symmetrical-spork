# tests/integration/test_setup_wizard.py
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO
from setup_wizard import (
    prompt_yes_no,
    prompt_text,
    prompt_service,
    generate_org_id,
    run_setup_wizard
)


def test_generate_org_id():
    """Test UUID generation."""
    org_id = generate_org_id()

    # Should be valid UUID format
    assert len(org_id) == 36
    assert org_id.count('-') == 4


@patch('builtins.input')
def test_prompt_yes_no_accepts_yes(mock_input):
    """Test yes/no prompt with 'yes' answer."""
    mock_input.return_value = 'yes'
    result = prompt_yes_no("Continue?")
    assert result is True


@patch('builtins.input')
def test_prompt_yes_no_accepts_no(mock_input):
    """Test yes/no prompt with 'no' answer."""
    mock_input.return_value = 'no'
    result = prompt_yes_no("Continue?")
    assert result is False


@patch('builtins.input')
def test_prompt_text_with_validation(mock_input):
    """Test text prompt with validation."""
    mock_input.return_value = 'Test Clinic'
    result = prompt_text("Organization name", required=True)
    assert result == 'Test Clinic'


@patch('builtins.input')
def test_prompt_service(mock_input):
    """Test service input prompt."""
    mock_input.side_effect = [
        'General Consultation',  # name
        'Standard medical consultation',  # description
        '30',  # duration
        '100.00',  # price
        'yes'  # active
    ]

    service = prompt_service(1)

    assert service.name == 'General Consultation'
    assert service.duration_minutes == 30
    assert service.price == 100.0
    assert service.active is True
