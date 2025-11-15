# src/config_manager.py
"""
Configuration manager for multi-tenant organization settings.

Handles:
- Saving configurations to JSON files
- Loading configurations by org_id
- Listing all organizations
- Deleting configurations
"""
import json
import os
from pathlib import Path
from typing import List, Optional
from src.org_config import OrganizationConfig


class ConfigManager:
    """Manages organization configuration files."""

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize config manager.

        Args:
            config_dir: Directory for storing config files.
                       Defaults to 'data/organizations' in project root.
        """
        if config_dir is None:
            # Default to data/organizations in project
            project_root = Path(__file__).parent.parent
            config_dir = project_root / "data" / "organizations"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _get_config_path(self, org_id: str) -> Path:
        """Get file path for organization config."""
        # Sanitize org_id to prevent path traversal
        safe_org_id = org_id.replace("/", "_").replace("\\", "_")
        return self.config_dir / f"{safe_org_id}.json"

    def save_config(self, config: OrganizationConfig) -> None:
        """
        Save organization configuration to file.

        Args:
            config: Organization configuration to save
        """
        path = self._get_config_path(config.org_id)

        # Convert to dict and save as JSON
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(
                config.model_dump(mode='json'),
                f,
                indent=2,
                ensure_ascii=False
            )

    def load_config(self, org_id: str) -> OrganizationConfig:
        """
        Load organization configuration from file.

        Args:
            org_id: Organization ID to load

        Returns:
            OrganizationConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        path = self._get_config_path(org_id)

        if not path.exists():
            raise FileNotFoundError(
                f"Configuration not found for organization: {org_id}"
            )

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return OrganizationConfig(**data)

    def config_exists(self, org_id: str) -> bool:
        """
        Check if configuration exists for organization.

        Args:
            org_id: Organization ID to check

        Returns:
            True if config exists, False otherwise
        """
        path = self._get_config_path(org_id)
        return path.exists()

    def list_organizations(self) -> List[str]:
        """
        List all organization IDs with configurations.

        Returns:
            List of organization IDs
        """
        org_ids = []

        for file_path in self.config_dir.glob("*.json"):
            # Extract org_id from filename (remove .json extension)
            org_id = file_path.stem
            org_ids.append(org_id)

        return sorted(org_ids)

    def delete_config(self, org_id: str) -> None:
        """
        Delete organization configuration.

        Args:
            org_id: Organization ID to delete

        Raises:
            FileNotFoundError: If config doesn't exist
        """
        path = self._get_config_path(org_id)

        if not path.exists():
            raise FileNotFoundError(
                f"Configuration not found for organization: {org_id}"
            )

        path.unlink()
