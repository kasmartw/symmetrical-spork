# tests/integration/test_org_aware_api.py
import pytest
import requests
from src.org_config import OrganizationConfig, ServiceConfig, PermissionsConfig
from src.config_manager import ConfigManager


@pytest.fixture
def org_config():
    """Sample org configuration."""
    return OrganizationConfig(
        org_id="api-test-org",
        org_name="API Test Clinic",
        services=[
            ServiceConfig(
                id="srv-custom-001",
                name="Custom Service",
                description="Org-specific service",
                duration_minutes=45,
                price=125.0,
                active=True
            )
        ],
        permissions=PermissionsConfig()
    )


def test_get_services_with_org_header(org_config):
    """Test that API returns org-specific services when X-Org-ID header provided."""
    # Save config
    manager = ConfigManager()
    manager.save_config(org_config)

    # Call API with org header
    response = requests.get(
        "http://localhost:5000/services",
        headers={"X-Org-ID": org_config.org_id}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    services = data["services"]
    assert len(services) == 1
    assert services[0]["name"] == "Custom Service"
