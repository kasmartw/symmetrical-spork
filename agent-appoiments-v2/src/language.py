"""Language detection for bilingual support.

Pattern: Regex-based detection from first 2-3 user messages.
Zero-cost detection (no LLM calls).
"""
import re
from typing import List


class LanguageDetector:
    """
    Detect user language from message patterns.

    Pattern: Analyze first messages for language-specific keywords.
    Default: Spanish (primary audience).
    """

    SPANISH_PATTERNS: List[str] = [
        r'\b(hola|buenos|buenas|días|tardes|noches)\b',
        r'\b(quiero|necesito|puedo|quisiera)\b',
        r'\b(cita|consulta|turno)\b',
        r'\b(cancelar|agendar|reservar)\b',
        r'\b(gracias|por\s+favor)\b',
        r'\b(sí|no|claro|vale)\b',
        r'\b(doctor|doctora)\b',
    ]

    ENGLISH_PATTERNS: List[str] = [
        r'\b(hello|hi|hey|good|morning|afternoon|evening)\b',
        r'\b(want|need|can|would\s+like)\b',
        r'\b(appointment|consultation|booking)\b',
        r'\b(cancel|book|schedule|reserve)\b',
        r'\b(thanks|thank\s+you|please)\b',
        r'\b(yes|no|sure|okay)\b',
        r'\b(doctor|dr)\b',
    ]

    def detect(self, messages: List[str], threshold: int = 2) -> str:
        """
        Detect language from list of messages.

        Args:
            messages: List of user messages (typically first 2-3)
            threshold: Minimum pattern matches to confirm language

        Returns:
            "es" for Spanish, "en" for English
            Default: "es" (primary audience)

        Example:
            >>> detector = LanguageDetector()
            >>> detector.detect(["hola", "quiero una cita"])
            'es'
            >>> detector.detect(["hello", "I need an appointment"])
            'en'
        """
        if not messages:
            return "es"  # Default to Spanish

        # Combine messages for analysis
        combined = " ".join(messages).lower()

        # Count pattern matches
        spanish_matches = sum(
            1 for pattern in self.SPANISH_PATTERNS
            if re.search(pattern, combined, re.IGNORECASE)
        )

        english_matches = sum(
            1 for pattern in self.ENGLISH_PATTERNS
            if re.search(pattern, combined, re.IGNORECASE)
        )

        # Determine language
        if english_matches >= threshold and english_matches > spanish_matches:
            return "en"

        # Default to Spanish (primary audience)
        return "es"

    def detect_from_single_message(self, message: str) -> str:
        """
        Quick detection from single message.

        Useful for initial greeting detection.

        Args:
            message: Single user message

        Returns:
            "es" or "en"
        """
        return self.detect([message], threshold=1)
