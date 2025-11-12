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
        # English patterns
        r'\b(bye|goodbye|exit|quit)\b',
        r'\bno\s+thanks?\b',
        r'\bnevermind\b',
        r'\bdon\'?t\s+need\b',
        r'\bno\s+longer\b',
        r'\bstop\b',
        # Spanish patterns
        r'\b(adios|adiós|chao|chau)\b',
        r'\b(hasta\s+luego|hasta\s+pronto)\b',
        r'\bno\s+gracias\b',
        r'\bno\s+necesito\b',
        r'\bno\s+importa\b',
        r'\bsalir\b',
        r'\bterminar\b',
        r'\bfinalizar\b',
        r'\bya\s+no\b',
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
    """
    Detect appointment cancellation intent (bilingual).

    Pattern: Regex matching for English and Spanish phrases.
    Supports direct, indirect, and contextual cancellation expressions.
    """

    CANCEL_PATTERNS: List[str] = [
        # Direct - English
        r'\bcancel\s+(my\s+)?(appointment|booking)\b',
        r'\bdelete\s+(my\s+)?appointment\b',
        r'\bremove\s+(my\s+)?appointment\b',
        r'\bcancel\b',  # Standalone "cancel"

        # Direct - Spanish
        r'\bcancelar\s+(mi\s+)?(cita|reserva|turno)\b',
        r'\beliminar\s+(mi\s+)?cita\b',
        r'\bborrar\s+(mi\s+)?cita\b',
        r'\bcancelar\b',  # Standalone "cancelar"

        # Indirect expressions
        r'\b(olvida|forget|olvídate)\b',
        r'\bmejor\s+(no|otro\s+día)\b',
        r'\bya\s+no\b',

        # Contextual (with "appointment"/"cita" mentioned)
        r'\bno\s+(voy|puedo|podre)\b.*\b(cita|appointment)\b',
        r'\bno\s+necesito\b.*\b(cita|appointment)\b',
    ]

    def is_cancellation_intent(self, message: str) -> bool:
        """Check if user wants to cancel appointment."""
        message_lower = message.lower().strip()

        return any(
            re.search(pattern, message_lower)
            for pattern in self.CANCEL_PATTERNS
        )


class ReschedulingIntentDetector:
    """
    Detect appointment rescheduling intent (bilingual).

    Pattern: Regex matching for English and Spanish phrases.
    Supports direct and contextual rescheduling expressions.
    """

    RESCHEDULE_PATTERNS: List[str] = [
        # Direct - English
        r'\breschedule\s+(my\s+)?(appointment|booking)\b',
        r'\bchange\s+(my\s+)?(appointment|booking|time|date)\b',
        r'\bmove\s+(my\s+)?(appointment|booking)\b',
        r'\bmodify\s+(my\s+)?(appointment|booking)\b',
        r'\breschedule\b',  # Standalone

        # Direct - Spanish
        r'\breagendar\s+(mi\s+)?(cita|reserva|turno)\b',
        r'\bcambiar\s+(mi\s+)?(cita|reserva|turno|hora|fecha)\b',
        r'\bmover\s+(mi\s+)?cita\b',
        r'\bmodificar\s+(mi\s+)?(cita|reserva)\b',
        r'\breagendar\b',  # Standalone

        # Contextual
        r'\b(different|otra)\s+(time|date|hora|fecha)\b',
        r'\banother\s+(day|time)\b',
        r'\botro\s+(día|horario)\b',
    ]

    def is_rescheduling_intent(self, message: str) -> bool:
        """Check if user wants to reschedule."""
        message_lower = message.lower().strip()

        return any(
            re.search(pattern, message_lower)
            for pattern in self.RESCHEDULE_PATTERNS
        )
