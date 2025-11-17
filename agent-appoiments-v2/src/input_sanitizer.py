"""Input sanitization for user messages to prevent XSS and injection attacks."""
import re
from typing import Optional


class InputSanitizer:
    """
    Sanitizes user input to prevent security vulnerabilities.

    Protections:
    - XSS: Remove HTML/JavaScript
    - SQL Injection: Already handled by SQLAlchemy parameterized queries
    - Command Injection: Not applicable (no shell commands from user input)
    - Length limits: Enforced by Pydantic models
    """

    # Dangerous patterns to remove
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    SCRIPT_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)
    JAVASCRIPT_PATTERN = re.compile(r'javascript:', re.IGNORECASE)

    @staticmethod
    def sanitize_message(message: str) -> str:
        """
        Sanitize user message for safe processing.

        Removes:
        - HTML tags
        - JavaScript code
        - Excessive whitespace

        Args:
            message: Raw user input

        Returns:
            Sanitized message safe for processing
        """
        if not message:
            return message

        # Remove script tags and content
        message = InputSanitizer.SCRIPT_PATTERN.sub('', message)

        # Remove javascript: protocol
        message = InputSanitizer.JAVASCRIPT_PATTERN.sub('', message)

        # Remove all HTML tags
        message = InputSanitizer.HTML_TAG_PATTERN.sub('', message)

        # Normalize whitespace
        message = ' '.join(message.split())

        # Trim
        message = message.strip()

        return message

    @staticmethod
    def sanitize_org_id(org_id: str) -> str:
        """
        Sanitize organization ID.

        Only allows: letters, numbers, hyphens, underscores

        Args:
            org_id: Raw org ID

        Returns:
            Sanitized org ID

        Raises:
            ValueError: If org_id contains invalid characters
        """
        # Allow only alphanumeric, hyphens, underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', org_id):
            raise ValueError(
                f"Invalid org_id: '{org_id}'. Only alphanumeric, hyphens, and underscores allowed."
            )

        return org_id

    @staticmethod
    def validate_and_sanitize(message: str, org_id: str) -> tuple[str, str]:
        """
        Validate and sanitize all inputs.

        Args:
            message: User message
            org_id: Organization ID

        Returns:
            Tuple of (sanitized_message, sanitized_org_id)

        Raises:
            ValueError: If inputs are invalid
        """
        # Sanitize message
        clean_message = InputSanitizer.sanitize_message(message)

        # Validate org_id
        clean_org_id = InputSanitizer.sanitize_org_id(org_id)

        return clean_message, clean_org_id
