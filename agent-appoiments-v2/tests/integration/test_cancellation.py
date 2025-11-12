"""Test cancellation workflow."""
import pytest
from src.intent import CancellationIntentDetector, ReschedulingIntentDetector


class TestCancellationFlow:
    """Test appointment cancellation."""

    def test_detect_cancellation_intent(self):
        """Detect cancellation from user message."""
        detector = CancellationIntentDetector()

        messages = [
            "I need to cancel my appointment",
            "Cancel the booking please",
            "Delete my appointment",
        ]

        for msg in messages:
            assert detector.is_cancellation_intent(msg) is True

    def test_detect_rescheduling_intent(self):
        """Detect rescheduling from user message."""
        detector = ReschedulingIntentDetector()

        messages = [
            "I need to reschedule",
            "Change my appointment please",
            "Move my appointment to a different time",
        ]

        for msg in messages:
            assert detector.is_rescheduling_intent(msg) is True

    def test_normal_messages_not_detected_as_cancellation(self):
        """Normal messages are not cancellation intent."""
        detector = CancellationIntentDetector()

        messages = [
            "I want to book an appointment",
            "What times are available?",
            "Can you help me?",
        ]

        for msg in messages:
            assert detector.is_cancellation_intent(msg) is False
