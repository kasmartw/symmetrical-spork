"""Test exit intent detection."""
import pytest
from src.intent import ExitIntentDetector


class TestExitIntentDetection:
    """Test detecting when user wants to exit."""

    @pytest.fixture
    def detector(self):
        return ExitIntentDetector()

    @pytest.mark.parametrize("message", [
        "bye",
        "goodbye",
        "exit",
        "quit",
        "no thanks",
        "I don't need help anymore",
        "cancel",
        "nevermind",
    ])
    def test_exit_phrases_detected(self, detector, message):
        """Common exit phrases are detected."""
        assert detector.is_exit_intent(message) is True

    @pytest.mark.parametrize("message", [
        "I want to book an appointment",
        "What times are available?",
        "Can you help me?",
        "Hello",
    ])
    def test_normal_messages_not_detected_as_exit(self, detector, message):
        """Normal messages are not exit intent."""
        assert detector.is_exit_intent(message) is False
