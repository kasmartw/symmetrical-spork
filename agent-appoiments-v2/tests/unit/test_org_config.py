# tests/unit/test_org_config.py
import pytest
from uuid import UUID
from src.org_config import (
    OrganizationConfig,
    ServiceConfig,
    PermissionsConfig,
    PromotionalOffer,
    validate_organization_config
)


def test_service_config_validation():
    """Test service configuration with required fields."""
    service = ServiceConfig(
        id="srv-001",
        name="General Consultation",
        description="Standard medical consultation",
        duration_minutes=30,
        price=100.0,
        active=True
    )
    assert service.active is True
    assert service.duration_minutes == 30


def test_service_config_cannot_exceed_max_services():
    """Test that we can't have more than 10 services."""
    services = [
        ServiceConfig(
            id=f"srv-{i:03d}",
            name=f"Service {i}",
            description=f"Description {i}",
            duration_minutes=30,
            price=100.0,
            active=True
        )
        for i in range(11)
    ]

    with pytest.raises(ValueError, match="Maximum 10 services allowed"):
        validate_organization_config(
            org_id="550e8400-e29b-41d4-a716-446655440000",
            services=services,
            permissions=PermissionsConfig()
        )


def test_permissions_at_least_one_active():
    """Test that at least one permission must be active."""
    with pytest.raises(ValueError, match="At least one permission must be active"):
        PermissionsConfig(
            can_book=False,
            can_reschedule=False,
            can_cancel=False
        )


def test_permissions_all_active_by_default():
    """Test default permissions are all enabled."""
    perms = PermissionsConfig()
    assert perms.can_book is True
    assert perms.can_reschedule is True
    assert perms.can_cancel is True


def test_organization_config_with_custom_prompt():
    """Test organization with custom system prompt."""
    config = OrganizationConfig(
        org_id="550e8400-e29b-41d4-a716-446655440000",
        org_name="Test Clinic",
        system_prompt="You are a friendly medical assistant.",
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
        permissions=PermissionsConfig()
    )
    assert "friendly" in config.system_prompt


def test_organization_config_with_default_prompt():
    """Test organization without custom prompt uses default."""
    config = OrganizationConfig(
        org_id="550e8400-e29b-41d4-a716-446655440000",
        org_name="Test Clinic",
        system_prompt=None,
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
        permissions=PermissionsConfig()
    )
    assert config.get_effective_system_prompt() is not None
    assert "appointment" in config.get_effective_system_prompt().lower()


def test_promotional_offer_optional():
    """Test that promotional offers are optional."""
    config = OrganizationConfig(
        org_id="550e8400-e29b-41d4-a716-446655440000",
        org_name="Test Clinic",
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
        permissions=PermissionsConfig(),
        promotional_offers=[]
    )
    assert len(config.promotional_offers) == 0
