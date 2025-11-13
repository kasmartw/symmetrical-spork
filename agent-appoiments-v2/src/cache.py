"""Validation result caching and availability caching for performance.

Problem: Validation tools were calling LLM unnecessarily.
Solution: Regex-based validation with LRU cache.

Pattern: Cache validation results to avoid redundant computation.

v1.5: Added availability caching to prevent repeated API calls.
"""
import re
import time
from functools import lru_cache
from typing import Tuple, Dict, List, Optional


class ValidationCache:
    """
    Cache validation results.

    Performance:
    - Without cache: ~500-1000ms per validation (LLM call)
    - With cache: < 1ms (regex only)
    """

    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    @staticmethod
    @lru_cache(maxsize=1000)
    def validate_email(email: str) -> Tuple[bool, str]:
        """
        Validate email with caching.

        Args:
            email: Email to validate

        Returns:
            (is_valid, message)
        """
        is_valid = bool(ValidationCache.EMAIL_PATTERN.match(email))

        if is_valid:
            return True, f"✅ Email '{email}' is valid."
        else:
            return False, (
                f"❌ Email '{email}' is not valid. "
                "Please provide a valid email (e.g., name@example.com)."
            )

    @staticmethod
    @lru_cache(maxsize=1000)
    def validate_phone(phone: str) -> Tuple[bool, str]:
        """
        Validate phone with caching.

        Args:
            phone: Phone to validate

        Returns:
            (is_valid, message)
        """
        digits = re.sub(r'[^\d]', '', phone)
        is_valid = len(digits) >= 7

        if is_valid:
            return True, f"✅ Phone '{phone}' is valid."
        else:
            return False, (
                f"❌ Phone '{phone}' is not valid. "
                "Please provide at least 7 digits."
            )


# Singleton instance
validation_cache = ValidationCache()


class AvailabilityCache:
    """
    Cache availability results to avoid repeated API calls.

    Performance:
    - Without cache: ~100-500ms per API call
    - With cache: < 1ms (memory lookup)

    TTL: Configurable via config.AVAILABILITY_CACHE_TTL (default: 30 minutes)
    """

    def __init__(self):
        self._cache: Dict[str, Dict] = {}

    def get(self, service_id: str) -> Optional[Dict]:
        """
        Get cached availability for a service.

        Args:
            service_id: Service ID to get availability for

        Returns:
            Cached data with 'slots', 'service', 'location', 'assigned_person', 'timestamp'
            or None if not cached or expired
        """
        key = f"availability_{service_id}"

        if key not in self._cache:
            return None

        cached_data = self._cache[key]
        timestamp = cached_data.get("timestamp", 0)

        # Import here to avoid circular dependency
        from src.config import AVAILABILITY_CACHE_TTL

        # Check if cache is expired
        if time.time() - timestamp > AVAILABILITY_CACHE_TTL:
            del self._cache[key]
            return None

        return cached_data

    def set(self, service_id: str, slots: List[Dict], service: Dict,
            location: Dict, assigned_person: Dict) -> None:
        """
        Cache availability data for a service.

        Args:
            service_id: Service ID
            slots: List of available time slots
            service: Service information
            location: Location information
            assigned_person: Assigned person information
        """
        key = f"availability_{service_id}"

        self._cache[key] = {
            "slots": slots,
            "service": service,
            "location": location,
            "assigned_person": assigned_person,
            "timestamp": time.time()
        }

    def clear(self, service_id: Optional[str] = None) -> None:
        """
        Clear cache for a specific service or all services.

        Args:
            service_id: Service ID to clear, or None to clear all
        """
        if service_id:
            key = f"availability_{service_id}"
            if key in self._cache:
                del self._cache[key]
        else:
            self._cache.clear()


# Singleton instance
availability_cache = AvailabilityCache()
