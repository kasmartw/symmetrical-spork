"""Security layer for prompt injection detection.

Language-agnostic detection system that works across all languages.
Focus on behavioral patterns rather than specific keywords.

Defense layers:
1. Pattern matching (behavioral, not language-specific)
2. Base64 decoding check
3. LLM-Guard deep scan (optional, disabled by default)
"""
import re
import base64
from dataclasses import dataclass
from typing import Optional
from llm_guard.input_scanners import PromptInjection
from llm_guard.input_scanners.prompt_injection import MatchType


@dataclass
class ScanResult:
    """Result of security scan."""
    is_safe: bool
    risk_score: float
    threat_type: Optional[str] = None
    sanitized_text: str = ""


class PromptInjectionDetector:
    """
    Language-agnostic prompt injection detector.

    Design Philosophy:
    - Detects BEHAVIORAL patterns, not keywords
    - Works across ALL languages (English, Spanish, Chinese, etc.)
    - Avoids false positives with legitimate conversation
    - Focuses on structural attack patterns

    Layers:
    1. Pattern matching (behavioral patterns)
    2. Base64 decoding (encoded attacks)
    3. LLM-Guard (optional ML, disabled by default)

    Pattern: Defense in depth
    Reference: OWASP LLM Top 10
    """

    # Suspicious patterns - LANGUAGE AGNOSTIC
    # Focus on structural patterns that indicate attacks, not normal conversation
    SUSPICIOUS_PATTERNS = [
        # Command injection patterns (English)
        r'ignore\s+(all\s+)?(previous|prior)\s+(instructions?|commands?|directives?)',
        r'disregard\s+(all\s+)?(previous|prior)\s+(instructions?|commands?)',
        r'forget\s+(all\s+)?(your|the)\s+(previous\s+)?(instructions?|commands?|directives?)',

        # Command injection patterns (Spanish)
        r'ignora\s+(todas?\s+)?(las?\s+)?(instrucciones?|comandos?|directivas?)\s+(anteriores?|previas?)',
        r'olvida\s+(todas?\s+)?(tus?|las?)\s*(instrucciones?|comandos?|directivas?)\s*(anteriores?|previas?)?',

        # System manipulation (English + Spanish)
        r'(system|sistema)\s*(prompt|mensaje)',
        r'(reveal|show|display|muestra|revela)\s+(your|tu|tus)\s+(prompt|instructions|instrucciones)',

        # Role manipulation (English)
        r'(pretend|act|behave)\s+(you\s+are|as\s+if|like)\s+(a\s+)?(different|another|new|an?\s+)?(\w+\s+)?(AI|assistant|bot)',
        r'(you\s+are\s+now|from\s+now\s+on|now\s+you\s+are)\s+(a\s+|in\s+)?(different|another)',

        # Role manipulation (Spanish)
        r'(finge|actúa|actua|comportate|comporta)\s+(que\s+eres|como\s+si|como)\s+(un\s+)?(\w+\s+)?(diferente|otro|nueva?)',
        r'(ahora\s+eres|ahora\s+estás|ahora\s+estas|desde\s+ahora)\s+(un\s+|en\s+)?(diferente|otro|modo)',

        # Mode switching (English + Spanish)
        r'(developer|debug|admin|root|administrador|administrator)\s+(mode|modo)',
        r'(you\s+are\s+now|now\s+you\s+are|ahora\s+estás|ahora\s+estas)\s+in\s+(developer|debug|admin)\s+(mode|modo)',
        r'jailbreak',

        # Override attempts (English + Spanish)
        r'(override|bypass|skip|saltate)\s+(your|all|any|tu|tus|todas?)\s+(rules?|restrictions?|reglas?|restricciones?)',
        r'(ignora|omite|salta|ignore|skip|bypass)\s+(todas?\s+)?(tus?|your|all)\s+(rules?|reglas?|restrictions?|restricciones?)',

        # Direct command attempts (English + Spanish)
        r'<\s*(system|sistema|admin|root)\s*>',
        r'\[\s*(system|sistema|admin|root)\s*\]',
    ]

    def __init__(self, threshold: float = 0.5, use_ml_scanner: bool = False):
        """
        Initialize language-agnostic detector.

        Args:
            threshold: Risk score threshold (0.0-1.0), only used if ML scanner enabled
            use_ml_scanner: Enable ML-based LLM-Guard scanner
                          WARNING: ML scanner trained primarily on English,
                          may cause false positives in other languages.
                          Recommended: False (default)

        Design:
            - Pattern matching works across all languages
            - Detects behavioral attack patterns, not keywords
            - No language-specific bias
        """
        self.threshold = threshold
        self.use_ml_scanner = use_ml_scanner

        if use_ml_scanner:
            self.scanner = PromptInjection(
                threshold=threshold,
                match_type=MatchType.FULL
            )
        else:
            self.scanner = None

    def _check_patterns(self, text: str) -> bool:
        """
        Fast pattern-based check.

        Language-agnostic: Detects behavioral attack patterns in any language.
        Patterns include English, Spanish, and structural markers.
        """
        text_lower = text.lower()
        return any(
            re.search(pattern, text_lower, re.IGNORECASE)
            for pattern in self.SUSPICIOUS_PATTERNS
        )

    def _check_base64(self, text: str) -> bool:
        """Check for base64 encoded attacks."""
        base64_pattern = r'[A-Za-z0-9+/]{20,}={0,2}'
        matches = re.findall(base64_pattern, text)

        for match in matches:
            try:
                decoded = base64.b64decode(match).decode('utf-8', errors='ignore')
                if self._check_patterns(decoded):
                    return True
            except Exception:
                continue
        return False

    def scan(self, user_input: str) -> ScanResult:
        """
        Scan input for threats.

        Args:
            user_input: Raw user input

        Returns:
            ScanResult with safety assessment
        """
        # Layer 1: Pattern check (fast)
        if self._check_patterns(user_input):
            return ScanResult(
                is_safe=False,
                risk_score=1.0,
                threat_type="pattern_match",
                sanitized_text=user_input
            )

        # Layer 2: Base64 check
        if self._check_base64(user_input):
            return ScanResult(
                is_safe=False,
                risk_score=1.0,
                threat_type="encoded_injection",
                sanitized_text=user_input
            )

        # Layer 3: LLM-Guard deep scan (optional, can have false positives)
        if self.use_ml_scanner and self.scanner:
            try:
                sanitized, is_valid, risk_score = self.scanner.scan(user_input)
                return ScanResult(
                    is_safe=is_valid,
                    risk_score=risk_score,
                    threat_type="llm_guard" if not is_valid else None,
                    sanitized_text=sanitized
                )
            except Exception as e:
                # Fail secure
                return ScanResult(
                    is_safe=False,
                    risk_score=1.0,
                    threat_type=f"scanner_error: {str(e)}",
                    sanitized_text=user_input
                )

        # If ML scanner disabled, pass through (pattern + base64 already checked)
        return ScanResult(
            is_safe=True,
            risk_score=0.0,
            threat_type=None,
            sanitized_text=user_input
        )
