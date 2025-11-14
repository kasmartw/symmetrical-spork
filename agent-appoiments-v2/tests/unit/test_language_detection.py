"""Test language detection (v1.2)."""
import pytest
from src.language import LanguageDetector


class TestLanguageDetection:
    """Test bilingual language detection."""

    @pytest.fixture
    def detector(self):
        return LanguageDetector()

    def test_detect_spanish_from_multiple_messages(self, detector):
        """Spanish detected from multiple messages."""
        messages = ["hola", "quiero una cita"]
        assert detector.detect(messages) == "es"

    def test_detect_english_from_multiple_messages(self, detector):
        """English detected from multiple messages."""
        messages = ["hello", "I need an appointment"]
        assert detector.detect(messages) == "en"

    def test_detect_spanish_from_single_message(self, detector):
        """Spanish detected from single message."""
        assert detector.detect_from_single_message("Hola buenos días") == "es"
        assert detector.detect_from_single_message("Quiero agendar una cita") == "es"

    def test_detect_english_from_single_message(self, detector):
        """English detected from single message."""
        assert detector.detect_from_single_message("Hello good morning") == "en"
        assert detector.detect_from_single_message("I want to book") == "en"

    def test_default_to_spanish_on_empty(self, detector):
        """Defaults to Spanish when no messages."""
        assert detector.detect([]) == "es"
        assert detector.detect_from_single_message("") == "es"

    def test_default_to_spanish_on_ambiguous(self, detector):
        """Defaults to Spanish on ambiguous input."""
        # Numbers and symbols don't match any pattern
        assert detector.detect(["123", "456"]) == "es"

    @pytest.mark.parametrize("messages,expected", [
        (["hola", "cita"], "es"),
        (["hello", "appointment"], "en"),
        (["buenos días", "necesito ayuda"], "es"),
        (["good morning", "need help"], "en"),
        (["gracias"], "es"),
        (["hello", "thanks"], "en"),  # Need 2 matches for threshold
    ])
    def test_various_message_combinations(self, detector, messages, expected):
        """Test various message combinations."""
        assert detector.detect(messages) == expected
