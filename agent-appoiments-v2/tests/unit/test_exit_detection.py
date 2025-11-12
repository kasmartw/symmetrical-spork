"""Test exit intent detection."""
import pytest
from src.intent import ExitIntentDetector


class TestExitIntentDetection:
    """Test detecting when user wants to exit."""

    @pytest.fixture
    def detector(self):
        return ExitIntentDetector()

    @pytest.mark.parametrize("message", [
        # English
        "bye",
        "goodbye",
        "exit",
        "quit",
        "no thanks",
        "I don't need help anymore",
        "nevermind",
        # Spanish
        "adios",
        "adiós",
        "chao",
        "hasta luego",
        "no gracias",
        "no necesito",
        "salir",
        "terminar",
        "finalizar",
        "ya no",
        # Note: "cancel"/"cancelar" handled by CancellationIntentDetector
    ])
    def test_exit_phrases_detected(self, detector, message):
        """Common exit phrases in English and Spanish are detected."""
        assert detector.is_exit_intent(message) is True

    @pytest.mark.parametrize("message", [
        "I want to book an appointment",
        "What times are available?",
        "Can you help me?",
        "Hello",
        "Quiero agendar una cita",
        "Hola, buenos días",
        "¿Qué horarios tienen?",
    ])
    def test_normal_messages_not_detected_as_exit(self, detector, message):
        """Normal messages in English and Spanish are not exit intent."""
        assert detector.is_exit_intent(message) is False
