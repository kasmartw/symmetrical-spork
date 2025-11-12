"""Validation result caching for performance.

Problem: Validation tools were calling LLM unnecessarily.
Solution: Regex-based validation with LRU cache.

Pattern: Cache validation results to avoid redundant computation.
"""
import re
from functools import lru_cache
from typing import Tuple


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
