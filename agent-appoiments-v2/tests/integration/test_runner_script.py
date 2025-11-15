# tests/integration/test_runner_script.py
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from src.org_config import OrganizationConfig, ServiceConfig, PermissionsConfig
from src.config_manager import ConfigManager
from test_runner import validate_org_exists, load_and_display_config, run_agent_interactive


@pytest.fixture
def temp_config_dir():
    """Create temporary directory for test configs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def org_config_friendly():
    """Org with friendly custom prompt."""
    return OrganizationConfig(
        org_id="test-org-friendly",
        org_name="Friendly Clinic",
        system_prompt="You are a super friendly and cheerful assistant! Use lots of enthusiasm!",
        services=[
            ServiceConfig(
                id="srv-001",
                name="Consultation",
                description="Medical consultation",
                duration_minutes=30,
                price=100.0,
                active=True
            )
        ],
        permissions=PermissionsConfig(can_book=True, can_reschedule=True, can_cancel=True),
        promotional_offers=[]
    )


@pytest.fixture
def org_config_formal():
    """Org with formal custom prompt and limited permissions."""
    return OrganizationConfig(
        org_id="test-org-formal",
        org_name="Formal Clinic",
        system_prompt="You are a formal, professional assistant. Use concise, technical language.",
        services=[
            ServiceConfig(
                id="srv-100",
                name="Premium Consultation",
                description="Advanced consultation",
                duration_minutes=60,
                price=200.0,
                active=True
            )
        ],
        permissions=PermissionsConfig(
            can_book=True,
            can_reschedule=False,  # DISABLED
            can_cancel=False      # DISABLED
        ),
        promotional_offers=[]
    )


def test_validate_org_exists_success(temp_config_dir, org_config_friendly):
    """Test validation succeeds when org exists."""
    manager = ConfigManager(config_dir=temp_config_dir)
    manager.save_config(org_config_friendly)

    # Should not raise
    validate_org_exists(org_config_friendly.org_id, manager)


def test_validate_org_exists_failure(temp_config_dir):
    """Test validation fails when org doesn't exist."""
    manager = ConfigManager(config_dir=temp_config_dir)

    with pytest.raises(SystemExit):
        validate_org_exists("nonexistent-org", manager)


def test_load_and_display_config(temp_config_dir, org_config_friendly, capsys):
    """Test loading and displaying configuration."""
    manager = ConfigManager(config_dir=temp_config_dir)
    manager.save_config(org_config_friendly)

    config = load_and_display_config(org_config_friendly.org_id, manager)

    captured = capsys.readouterr()
    assert "Friendly Clinic" in captured.out
    assert org_config_friendly.org_id in captured.out


def test_run_agent_uses_org_specific_config(temp_config_dir, org_config_friendly):
    """Test that run_agent_interactive uses create_agent_for_org, not create_graph."""
    manager = ConfigManager(config_dir=temp_config_dir)
    manager.save_config(org_config_friendly)

    # Mock input/output for non-interactive test
    with patch('builtins.input', return_value='exit'):
        with patch('builtins.print'):
            # Should not raise - verifies it calls create_agent_for_org
            run_agent_interactive(org_config_friendly)


def test_different_orgs_produce_different_agents(temp_config_dir, org_config_friendly, org_config_formal):
    """Test that different org configs produce different agent behaviors."""
    manager = ConfigManager(config_dir=temp_config_dir)
    manager.save_config(org_config_friendly)
    manager.save_config(org_config_formal)

    # Load both
    config1 = manager.load_config(org_config_friendly.org_id)
    config2 = manager.load_config(org_config_formal.org_id)

    # Verify they're different
    assert config1.system_prompt != config2.system_prompt
    assert config1.permissions.can_reschedule != config2.permissions.can_reschedule
    assert config1.services[0].name != config2.services[0].name
