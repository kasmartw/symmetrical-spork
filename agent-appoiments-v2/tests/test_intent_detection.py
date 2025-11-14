"""Tests for improved intent detection."""
import pytest
from src.intent import ExitIntentDetector


class TestExitIntentDetector:
    """Test exit intent detection with contextual phrases."""

    def setup_method(self):
        """Initialize detector before each test."""
        self.detector = ExitIntentDetector()

    # Existing exact keyword tests
    def test_exact_exit_keywords_english(self):
        """Test exact exit keywords in English."""
        assert self.detector.is_exit_intent("bye")
        assert self.detector.is_exit_intent("goodbye")
        assert self.detector.is_exit_intent("exit")

    def test_exact_exit_keywords_spanish(self):
        """Test exact exit keywords in Spanish."""
        assert self.detector.is_exit_intent("adiós")
        assert self.detector.is_exit_intent("hasta luego")

    # NEW: Contextual exit intent tests
    def test_contextual_exit_thanks(self):
        """Test 'thanks + goodbye' pattern."""
        assert self.detector.is_exit_intent("Gracias, hasta luego")
        assert self.detector.is_exit_intent("Muchas gracias")
        assert self.detector.is_exit_intent("Thank you, bye")

    def test_contextual_exit_completion(self):
        """Test 'completion' phrases."""
        assert self.detector.is_exit_intent("Perfecto, eso es todo")
        assert self.detector.is_exit_intent("Ok listo, nos vemos")
        assert self.detector.is_exit_intent("Ya está, gracias")
        assert self.detector.is_exit_intent("That's all, thanks")
        assert self.detector.is_exit_intent("Perfect, that's it")

    def test_contextual_exit_done(self):
        """Test 'done' phrases."""
        assert self.detector.is_exit_intent("Ya terminé")
        assert self.detector.is_exit_intent("Listo, ya")
        assert self.detector.is_exit_intent("All done")

    def test_not_exit_intent(self):
        """Test phrases that should NOT trigger exit."""
        # "Thanks" alone without goodbye shouldn't exit
        assert not self.detector.is_exit_intent("Gracias por la información")
        assert not self.detector.is_exit_intent("Thanks for helping")
        # Questions shouldn't exit
        assert not self.detector.is_exit_intent("Qué horarios tienen?")
        # Confirmations shouldn't exit
        assert not self.detector.is_exit_intent("Perfecto, confirmado")
