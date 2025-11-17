"""Organization configuration loading from database."""
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.api.database_models import Base, Organization
from src.org_config import OrganizationConfig, ServiceConfig, PermissionsConfig


class OrgNotFoundError(Exception):
    """Raised when organization not found or inactive."""
    pass


class OrgConfigLoader:
    """
    Loads organization configuration from database.

    Pattern: Separate database persistence from domain models.
    OrganizationConfig (domain) vs Organization (database).
    """

    def __init__(self, database_url: str):
        """Initialize with database connection."""
        self.engine = create_engine(database_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def load_org_config(self, org_id: str) -> OrganizationConfig:
        """
        Load organization configuration from database.

        Args:
            org_id: Organization identifier

        Returns:
            OrganizationConfig instance

        Raises:
            OrgNotFoundError: If org doesn't exist or is inactive
        """
        with self.SessionLocal() as db:
            org = db.query(Organization).filter(
                Organization.org_id == org_id,
                Organization.is_active == True
            ).first()

            if not org:
                raise OrgNotFoundError(f"Organization {org_id} not found or not active")

            # Convert database model to domain model
            return OrganizationConfig(
                org_id=org.org_id,
                org_name=org.org_name or org.org_id,
                system_prompt=org.system_prompt,
                services=[ServiceConfig(**svc) for svc in org.services] if org.services else [],
                permissions=PermissionsConfig(**org.permissions) if org.permissions else PermissionsConfig()
            )

    def validate_org_exists(self, org_id: str) -> bool:
        """
        Check if organization exists and is active.

        Args:
            org_id: Organization identifier

        Returns:
            True if active, False otherwise
        """
        try:
            self.load_org_config(org_id)
            return True
        except OrgNotFoundError:
            return False
