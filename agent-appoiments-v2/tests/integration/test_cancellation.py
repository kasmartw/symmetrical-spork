"""Test cancellation workflow (v1.2 - bilingual)."""
import pytest
from src.intent import CancellationIntentDetector, ReschedulingIntentDetector


class TestCancellationFlow:
    """Test appointment cancellation (bilingual support)."""

    def test_detect_cancellation_intent_english(self):
        """Detect cancellation from English messages."""
        detector = CancellationIntentDetector()

        messages = [
            "I need to cancel my appointment",
            "Cancel the booking please",
            "Delete my appointment",
            "cancel",
            "Remove my appointment",
        ]

        for msg in messages:
            assert detector.is_cancellation_intent(msg) is True

    def test_detect_cancellation_intent_spanish(self):
        """Detect cancellation from Spanish messages."""
        detector = CancellationIntentDetector()

        messages = [
            "Quiero cancelar mi cita",
            "Necesito cancelar",
            "Eliminar mi cita",
            "Cancelar",
            "No puedo ir a la cita",
            "Mejor otro día",
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
