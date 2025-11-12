"""Security layer for prompt injection detection.

Defense in depth:
1. Pattern matching (fast pre-filter)
2. Base64 decoding check
3. LLM-Guard deep scan
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
    Multi-layer prompt injection detector.

    Layers:
    1. Pattern matching (regex) - fast fail
    2. Base64 decoding - catch encoded attacks
    3. LLM-Guard - ML-based detection

    Pattern: Defense in depth
    Reference: OWASP LLM Top 10
    """

    # Suspicious patterns (case-insensitive)
    SUSPICIOUS_PATTERNS = [
        r'ignore\s+(all\s+)?previous\s+instructions',
        r'system\s*prompt',
        r'developer\s+mode',
        r'jailbreak',
        r'pretend\s+you\s+are',
        r'act\s+as\s+if',
        r'forget\s+(your\s+)?instructions',
        r'override\s+(your\s+)?rules',
    ]

    def __init__(self, threshold: float = 0.5):
        """
        Initialize detector.

        Args:
            threshold: Risk score threshold (0.0-1.0)
        """
        self.threshold = threshold
        self.scanner = PromptInjection(
            threshold=threshold,
            match_type=MatchType.FULL
        )

    def _check_patterns(self, text: str) -> bool:
        """Fast pattern-based check."""
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

        # Layer 3: LLM-Guard deep scan
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
