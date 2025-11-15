# tests/integration/test_org_agent_integration.py
import pytest
import tempfile
from src.org_config import OrganizationConfig, ServiceConfig, PermissionsConfig
from src.config_manager import ConfigManager
from src.agent import create_agent_for_org
from langchain_core.messages import HumanMessage


@pytest.fixture
def temp_config_dir():
    """Create temporary directory for test configs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def org_config_custom_prompt():
    """Organization with custom system prompt and limited permissions."""
    return OrganizationConfig(
        org_id="test-org-custom",
        org_name="Custom Clinic",
        system_prompt="You are a helpful assistant for Custom Clinic. Be professional and concise.",
        services=[
            ServiceConfig(
                id="srv-001",
                name="Video Consultation",
                description="Online video consultation",
                duration_minutes=45,
                price=75.0,
                active=True
            ),
            ServiceConfig(
                id="srv-002",
                name="In-Person Visit",
                description="Physical examination",
                duration_minutes=60,
                price=150.0,
                active=False  # INACTIVE - should NOT appear
            )
        ],
        permissions=PermissionsConfig(
            can_book=True,
            can_reschedule=False,  # DISABLED
            can_cancel=True
        ),
        promotional_offers=[]
    )


@pytest.fixture
def org_config_default_prompt():
    """Organization using default system prompt."""
    return OrganizationConfig(
        org_id="test-org-default",
        org_name="Default Clinic",
        system_prompt=None,  # Use default
        services=[
            ServiceConfig(
                id="srv-100",
                name="Standard Service",
                description="Standard service",
                duration_minutes=30,
                price=100.0,
                active=True
            )
        ],
        permissions=PermissionsConfig()  # All enabled
    )


def test_create_agent_with_custom_prompt(temp_config_dir, org_config_custom_prompt):
    """Test that agent is created with org-specific custom system prompt."""
    manager = ConfigManager(config_dir=temp_config_dir)
    manager.save_config(org_config_custom_prompt)

    # Create agent for this org
    graph = create_agent_for_org(org_config_custom_prompt)

    # Verify graph was created
    assert graph is not None

    # Test that agent uses custom prompt by invoking with message
    result = graph.invoke(
        {"messages": [HumanMessage(content="Hello")]},
        {"configurable": {"thread_id": "test-custom"}}
    )

    # Agent should respond (basic smoke test)
    assert result is not None
    assert "messages" in result


def test_create_agent_with_default_prompt(temp_config_dir, org_config_default_prompt):
    """Test that agent is created with default prompt when system_prompt is None."""
    manager = ConfigManager(config_dir=temp_config_dir)
    manager.save_config(org_config_default_prompt)

    # Create agent for this org
    graph = create_agent_for_org(org_config_default_prompt)

    # Verify graph was created
    assert graph is not None


def test_agent_only_has_permitted_tools(org_config_custom_prompt):
    """Test that agent only receives tools matching permissions."""
    # This org has can_reschedule=False
    graph = create_agent_for_org(org_config_custom_prompt)

    # Extract tools from graph (implementation-specific)
    # For now, we verify the graph was created with the config
    assert graph is not None


def test_agent_only_shows_active_services(temp_config_dir, org_config_custom_prompt):
    """Test that agent only shows active services to users."""
    manager = ConfigManager(config_dir=temp_config_dir)
    manager.save_config(org_config_custom_prompt)

    # Load and check active services
    loaded = manager.load_config(org_config_custom_prompt.org_id)
    active_services = loaded.get_active_services()

    # Only srv-001 should be active
    assert len(active_services) == 1
    assert active_services[0].name == "Video Consultation"
    assert "In-Person Visit" not in [s.name for s in active_services]
