# tests/unit/test_config_manager.py
import pytest
import os
import json
import tempfile
from pathlib import Path
from src.config_manager import ConfigManager
from src.org_config import OrganizationConfig, ServiceConfig, PermissionsConfig


@pytest.fixture
def temp_config_dir():
    """Create temporary directory for test configs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_org_config():
    """Create sample organization config."""
    return OrganizationConfig(
        org_id="550e8400-e29b-41d4-a716-446655440000",
        org_name="Test Medical Center",
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
        permissions=PermissionsConfig(),
        promotional_offers=[]
    )


def test_save_and_load_config(temp_config_dir, sample_org_config):
    """Test saving and loading configuration."""
    manager = ConfigManager(config_dir=temp_config_dir)

    # Save
    manager.save_config(sample_org_config)

    # Load
    loaded = manager.load_config(sample_org_config.org_id)

    assert loaded.org_id == sample_org_config.org_id
    assert loaded.org_name == sample_org_config.org_name
    assert len(loaded.services) == 1


def test_load_nonexistent_config_raises_error(temp_config_dir):
    """Test that loading non-existent config raises FileNotFoundError."""
    manager = ConfigManager(config_dir=temp_config_dir)

    with pytest.raises(FileNotFoundError):
        manager.load_config("nonexistent-org-id")


def test_list_all_organizations(temp_config_dir, sample_org_config):
    """Test listing all organization IDs."""
    manager = ConfigManager(config_dir=temp_config_dir)

    # Create multiple configs
    org1 = sample_org_config
    org2 = OrganizationConfig(
        org_id="660e8400-e29b-41d4-a716-446655440000",
        org_name="Another Clinic",
        services=[
            ServiceConfig(
                id="srv-001",
                name="Service",
                description="Desc",
                duration_minutes=30,
                price=50.0,
                active=True
            )
        ],
        permissions=PermissionsConfig()
    )

    manager.save_config(org1)
    manager.save_config(org2)

    orgs = manager.list_organizations()
    assert len(orgs) == 2
    assert org1.org_id in orgs
    assert org2.org_id in orgs


def test_delete_config(temp_config_dir, sample_org_config):
    """Test deleting an organization config."""
    manager = ConfigManager(config_dir=temp_config_dir)

    manager.save_config(sample_org_config)
    assert manager.config_exists(sample_org_config.org_id)

    manager.delete_config(sample_org_config.org_id)
    assert not manager.config_exists(sample_org_config.org_id)


def test_config_exists(temp_config_dir, sample_org_config):
    """Test checking if config exists."""
    manager = ConfigManager(config_dir=temp_config_dir)

    assert not manager.config_exists(sample_org_config.org_id)

    manager.save_config(sample_org_config)
    assert manager.config_exists(sample_org_config.org_id)
