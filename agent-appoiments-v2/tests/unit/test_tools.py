"""Test agent tools (LangChain 1.0 @tool decorator)."""
import pytest
from src.tools import validate_email_tool, validate_phone_tool


class TestEmailValidation:
    """Test email validation tool."""

    @pytest.mark.parametrize("email", [
        "john.doe@example.com",
        "user+tag@domain.co.uk",
        "test_user@sub.domain.com",
    ])
    def test_valid_emails_pass(self, email):
        """Valid email formats pass validation."""
        result = validate_email_tool.invoke({"email": email})
        assert "[VALID]" in result
        assert "valid" in result.lower()

    @pytest.mark.parametrize("email", [
        "notanemail",
        "missing@domain",
        "@nodomain.com",
    ])
    def test_invalid_emails_fail(self, email):
        """Invalid email formats fail validation."""
        result = validate_email_tool.invoke({"email": email})
        assert "[INVALID]" in result
        assert "not valid" in result.lower()
        assert "@" in result  # Should show example


class TestPhoneValidation:
    """Test phone validation tool."""

    @pytest.mark.parametrize("phone", [
        "555-123-4567",
        "(555) 123-4567",
        "5551234567",
    ])
    def test_valid_phones_pass(self, phone):
        """Valid phone numbers pass validation."""
        result = validate_phone_tool.invoke({"phone": phone})
        assert "[VALID]" in result

    def test_short_phone_fails(self):
        """Phone with < 7 digits fails."""
        result = validate_phone_tool.invoke({"phone": "123"})
        assert "[INVALID]" in result
        assert "7 digits" in result.lower()
