"""API key authentication and management."""
import uuid
from datetime import datetime, UTC
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.api.database_models import Base, APIKey


class InvalidAPIKeyError(Exception):
    """Raised when API key is invalid or inactive."""
    pass


class APIKeyManager:
    """
    Manages API key generation, validation, and lifecycle.

    Pattern: Secure key generation with bcrypt hashing + prefix indexing.
    Performance: O(1) lookup using key prefix, then bcrypt verification.
    Keys are shown in plain text ONCE during generation.
    """

    def __init__(self, database_url: str):
        """Initialize with database connection."""
        self.engine = create_engine(database_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def generate_api_key(self, org_id: str, description: Optional[str] = None) -> str:
        """
        Generate new API key for organization.

        WARNING: Returns key in plain text ONCE.
        Store it securely - cannot be retrieved later.

        Args:
            org_id: Organization identifier
            description: Optional description/label

        Returns:
            API key in format: ak_<uuid>
        """
        # Generate secure random key
        api_key = f"ak_{uuid.uuid4().hex}"

        # Extract prefix for indexing (performance optimization)
        key_prefix = APIKey.get_key_prefix(api_key)

        # Hash key for storage
        key_hash = APIKey.hash_key(api_key)

        # Store in database
        with self.SessionLocal() as db:
            db_key = APIKey(
                key_prefix=key_prefix,
                key_hash=key_hash,
                org_id=org_id,
                created_at=datetime.now(UTC),
                last_used=datetime.now(UTC),
                is_active=True,
                description=description
            )
            db.add(db_key)
            db.commit()

        # Return plain text key (ONLY TIME IT'S VISIBLE)
        return api_key

    def validate_api_key(self, api_key: str) -> str:
        """
        Validate API key and return associated org_id.

        Performance: O(1) lookup by prefix, then bcrypt verification.
        Updates last_used timestamp on successful validation.

        Args:
            api_key: API key to validate

        Returns:
            org_id associated with this key

        Raises:
            InvalidAPIKeyError: If key is invalid or inactive
        """
        # Extract prefix for fast lookup
        key_prefix = APIKey.get_key_prefix(api_key)

        with self.SessionLocal() as db:
            # O(1) lookup by prefix index
            db_key = db.query(APIKey).filter(
                APIKey.key_prefix == key_prefix,
                APIKey.is_active == True
            ).first()

            if not db_key:
                raise InvalidAPIKeyError("Invalid or inactive API key")

            # Verify full key with bcrypt
            if not APIKey.verify_key(api_key, db_key.key_hash):
                raise InvalidAPIKeyError("Invalid or inactive API key")

            # Valid key - update last_used
            db_key.last_used = datetime.now(UTC)
            db.commit()

            return db_key.org_id

    def deactivate_api_key(self, api_key: str):
        """
        Deactivate API key (soft delete).

        Args:
            api_key: API key to deactivate

        Raises:
            InvalidAPIKeyError: If key not found
        """
        key_prefix = APIKey.get_key_prefix(api_key)

        with self.SessionLocal() as db:
            db_key = db.query(APIKey).filter(
                APIKey.key_prefix == key_prefix
            ).first()

            if not db_key or not APIKey.verify_key(api_key, db_key.key_hash):
                raise InvalidAPIKeyError("API key not found")

            db_key.is_active = False
            db.commit()

    def _get_last_used(self, api_key: str) -> datetime:
        """Helper for testing - get last_used timestamp."""
        key_prefix = APIKey.get_key_prefix(api_key)

        with self.SessionLocal() as db:
            db_key = db.query(APIKey).filter(
                APIKey.key_prefix == key_prefix
            ).first()

            if not db_key or not APIKey.verify_key(api_key, db_key.key_hash):
                raise InvalidAPIKeyError("API key not found")

            return db_key.last_used
