"""Test input sanitization."""
import pytest
from src.input_sanitizer import InputSanitizer


def test_sanitize_message_removes_html_tags():
    """Should remove HTML tags."""
    dirty = "Hello <b>world</b> <script>alert('xss')</script>"
    clean = InputSanitizer.sanitize_message(dirty)

    assert "<b>" not in clean
    assert "<script>" not in clean
    assert "Hello world" in clean


def test_sanitize_message_removes_javascript():
    """Should remove javascript: protocol."""
    dirty = "Click <a href='javascript:alert(1)'>here</a>"
    clean = InputSanitizer.sanitize_message(dirty)

    assert "javascript:" not in clean


def test_sanitize_message_normalizes_whitespace():
    """Should normalize excessive whitespace."""
    dirty = "Hello    world   \n\n  test"
    clean = InputSanitizer.sanitize_message(dirty)

    assert clean == "Hello world test"


def test_sanitize_org_id_allows_valid():
    """Should allow valid org IDs."""
    valid_ids = ["org-123", "org_test", "ORG123", "clinic-downtown"]

    for org_id in valid_ids:
        result = InputSanitizer.sanitize_org_id(org_id)
        assert result == org_id


def test_sanitize_org_id_rejects_invalid():
    """Should reject org IDs with special characters."""
    invalid_ids = ["org@123", "org 123", "org;drop", "org<script>"]

    for org_id in invalid_ids:
        with pytest.raises(ValueError) as exc_info:
            InputSanitizer.sanitize_org_id(org_id)
        assert "Invalid org_id" in str(exc_info.value)


def test_validate_and_sanitize_cleans_both():
    """Should sanitize both message and org_id."""
    message = "<b>Hello</b> world"
    org_id = "org-123"

    clean_msg, clean_org = InputSanitizer.validate_and_sanitize(message, org_id)

    assert "<b>" not in clean_msg
    assert "Hello world" in clean_msg
    assert clean_org == org_id
