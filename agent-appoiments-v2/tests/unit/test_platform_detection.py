"""Test platform detection for WhatsApp/Telegram."""
import pytest
from src.platform import PlatformDetector, Platform


class TestPlatformDetection:
    """Test platform detection from context."""

    def test_detect_whatsapp_from_metadata(self):
        """Detect WhatsApp from metadata."""
        detector = PlatformDetector()

        context = {
            "platform": "whatsapp",
            "phone_number": "+1234567890"
        }

        platform = detector.detect(context)
        assert platform == Platform.WHATSAPP

    def test_detect_telegram_from_metadata(self):
        """Detect Telegram from metadata."""
        detector = PlatformDetector()

        context = {
            "platform": "telegram",
            "user_id": "12345"
        }

        platform = detector.detect(context)
        assert platform == Platform.TELEGRAM

    def test_detect_web_as_fallback(self):
        """Web chat is fallback when no platform detected."""
        detector = PlatformDetector()

        context = {}

        platform = detector.detect(context)
        assert platform == Platform.WEB

    def test_extract_phone_from_whatsapp_context(self):
        """Extract phone number from WhatsApp context."""
        detector = PlatformDetector()

        context = {
            "platform": "whatsapp",
            "phone_number": "+1234567890"
        }

        phone = detector.extract_phone(context)
        assert phone == "+1234567890"
