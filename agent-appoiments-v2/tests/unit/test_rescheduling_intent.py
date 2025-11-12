"""Test rescheduling intent detection."""
import pytest
from src.intent import ReschedulingIntentDetector, CancellationIntentDetector


class TestReschedulingIntentDetection:
    """Test detecting when user wants to reschedule."""

    @pytest.fixture
    def detector(self):
        return ReschedulingIntentDetector()

    @pytest.mark.parametrize("message", [
        # Direct - English
        "I want to reschedule my appointment",
        "reschedule my booking",
        "can I change my appointment",
        "need to move my appointment to another day",
        "reschedule",
        "change time for my appointment",
        "modify my booking",
        "I need a different date",
        "different time",
        # Direct - Spanish
        "quiero reagendar mi cita",
        "necesito cambiar mi cita",
        "puedo mover mi cita para otro día",
        "reagendar",
        "cambiar hora de mi cita",
        "modificar mi reserva",
        "quiero otra fecha",
        "otra hora",
        "otro día",
    ])
    def test_rescheduling_phrases_detected(self, detector, message):
        """Common rescheduling phrases in English and Spanish are detected."""
        assert detector.is_rescheduling_intent(message) is True

    @pytest.mark.parametrize("message", [
        "I want to book an appointment",
        "What times are available?",
        "cancel my appointment",
        "cancelar mi cita",
        "Hello",
        "Quiero agendar una cita",
        "¿Qué horarios tienen?",
    ])
    def test_normal_messages_not_detected_as_rescheduling(self, detector, message):
        """Normal booking and cancellation messages are not rescheduling intent."""
        assert detector.is_rescheduling_intent(message) is False


def test_rescheduling_not_confused_with_cancel():
    """Ensure rescheduling doesn't trigger cancellation."""
    reschedule_detector = ReschedulingIntentDetector()
    cancel_detector = CancellationIntentDetector()

    reschedule_only = [
        "quiero reagendar mi cita",
        "I want to reschedule",
        "cambiar mi cita",
    ]

    for case in reschedule_only:
        assert reschedule_detector.is_rescheduling_intent(case)
        assert not cancel_detector.is_cancellation_intent(case)
