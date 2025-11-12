"""Agent tools with @tool decorator (LangChain 1.0 pattern).

Best Practices:
- Use @tool decorator from langchain_core.tools
- Full type hints for args and return
- Descriptive docstrings (LLM reads these!)
- Return strings (LLM-friendly format)
"""
import re
from langchain_core.tools import tool


@tool
def validate_email_tool(email: str) -> str:
    """
    Validate email address format.

    Checks for:
    - @ symbol present
    - Domain with TLD
    - Valid characters only

    Args:
        email: Email address to validate

    Returns:
        Validation result message

    Example:
        >>> validate_email_tool.invoke({"email": "user@example.com"})
        "[VALID] Email 'user@example.com' is valid."
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    is_valid = re.match(pattern, email) is not None

    if is_valid:
        return f"[VALID] Email '{email}' is valid."
    else:
        return (
            f"[INVALID] Email '{email}' is not valid. "
            "Please provide a valid email (e.g., name@example.com)."
        )


@tool
def validate_phone_tool(phone: str) -> str:
    """
    Validate phone number (minimum 7 digits).

    Ignores formatting characters (spaces, hyphens, parentheses).
    Counts only numeric digits.

    Args:
        phone: Phone number to validate

    Returns:
        Validation result message
    """
    digits = re.sub(r'[^\d]', '', phone)
    is_valid = len(digits) >= 7

    if is_valid:
        return f"[VALID] Phone '{phone}' is valid."
    else:
        return (
            f"[INVALID] Phone '{phone}' is not valid. "
            "Please provide at least 7 digits."
        )
