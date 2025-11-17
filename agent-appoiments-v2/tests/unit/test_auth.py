"""Test API key authentication."""
import pytest
from src.auth import APIKeyManager, InvalidAPIKeyError


@pytest.fixture
def api_key_manager():
    """Create APIKeyManager with in-memory database."""
    return APIKeyManager(database_url="sqlite:///:memory:")


def test_generate_api_key_creates_unique_key(api_key_manager):
    """Generating API key should return unique string."""
    org_id = "org-123"

    api_key = api_key_manager.generate_api_key(org_id)

    assert isinstance(api_key, str)
    assert len(api_key) > 20  # Should be UUID-based
    assert api_key.startswith("ak_")  # Prefix for identification


def test_validate_api_key_returns_org_id(api_key_manager):
    """Validating API key should return associated org_id."""
    org_id = "org-123"
    api_key = api_key_manager.generate_api_key(org_id)

    validated_org_id = api_key_manager.validate_api_key(api_key)

    assert validated_org_id == org_id


def test_validate_api_key_raises_for_invalid_key(api_key_manager):
    """Validating invalid API key should raise error."""
    with pytest.raises(InvalidAPIKeyError):
        api_key_manager.validate_api_key("invalid_key_12345")


def test_validate_api_key_raises_for_inactive_key(api_key_manager):
    """Validating inactive API key should raise error."""
    org_id = "org-123"
    api_key = api_key_manager.generate_api_key(org_id)

    # Deactivate key
    api_key_manager.deactivate_api_key(api_key)

    # Should raise error
    with pytest.raises(InvalidAPIKeyError) as exc_info:
        api_key_manager.validate_api_key(api_key)

    assert "inactive" in str(exc_info.value).lower()


def test_validate_api_key_updates_last_used(api_key_manager):
    """Validating API key should update last_used timestamp."""
    import time

    org_id = "org-123"
    api_key = api_key_manager.generate_api_key(org_id)

    # Get initial last_used
    initial_last_used = api_key_manager._get_last_used(api_key)

    time.sleep(0.1)

    # Validate (should update last_used)
    api_key_manager.validate_api_key(api_key)

    # Check last_used was updated
    updated_last_used = api_key_manager._get_last_used(api_key)
    assert updated_last_used > initial_last_used
