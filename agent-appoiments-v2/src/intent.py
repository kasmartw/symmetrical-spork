"""Intent detection for conversation management.

Use Case:
- Detect when user wants to exit
- Detect cancellation intent
- Detect rescheduling intent
"""
import re
from typing import List


class ExitIntentDetector:
    """
    Detect exit/goodbye intents.

    Pattern: Pattern matching for common exit phrases.
    """

    EXIT_PATTERNS: List[str] = [
        r'\b(bye|goodbye|exit|quit)\b',
        r'\bno\s+thanks?\b',
        r'\bnevermind\b',
        r'\bdon\'?t\s+need\b',
        r'\bno\s+longer\b',
        r'\bcancel\b',
        r'\bstop\b',
    ]

    def is_exit_intent(self, message: str) -> bool:
        """
        Check if message expresses exit intent.

        Args:
            message: User message

        Returns:
            True if user wants to exit
        """
        message_lower = message.lower().strip()

        return any(
            re.search(pattern, message_lower, re.IGNORECASE)
            for pattern in self.EXIT_PATTERNS
        )


class CancellationIntentDetector:
    """Detect appointment cancellation intent."""

    CANCEL_PATTERNS: List[str] = [
        r'\bcancel\s+(my\s+)?appointment\b',
        r'\bcancel\s+(the\s+)?booking\b',
        r'\bdelete\s+(my\s+)?appointment\b',
        r'\bremove\s+(my\s+)?appointment\b',
    ]

    def is_cancellation_intent(self, message: str) -> bool:
        """Check if user wants to cancel appointment."""
        message_lower = message.lower().strip()

        return any(
            re.search(pattern, message_lower)
            for pattern in self.CANCEL_PATTERNS
        )


class ReschedulingIntentDetector:
    """Detect appointment rescheduling intent."""

    RESCHEDULE_PATTERNS: List[str] = [
        r'\breschedule\b',
        r'\bchange\s+(my\s+)?appointment\b',
        r'\bmove\s+(my\s+)?appointment\b',
        r'\bdifferent\s+(time|date)\b',
    ]

    def is_rescheduling_intent(self, message: str) -> bool:
        """Check if user wants to reschedule."""
        message_lower = message.lower().strip()

        return any(
            re.search(pattern, message_lower)
            for pattern in self.RESCHEDULE_PATTERNS
        )
