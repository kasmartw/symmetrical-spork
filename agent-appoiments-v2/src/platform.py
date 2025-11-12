"""Platform detection for WhatsApp/Telegram integration.

Use Case:
- WhatsApp/Telegram bots provide user phone in context
- Skip phone collection step for these platforms
- Offer "use this number or different?" prompt

Pattern: Context-aware state transitions
"""
from enum import Enum
from typing import Optional, Dict, Any


class Platform(str, Enum):
    """Detected platform types."""
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    WEB = "web"
    UNKNOWN = "unknown"


class PlatformDetector:
    """
    Detect messaging platform from context.

    Supports:
    - WhatsApp Business API
    - Telegram Bot API
    - Web chat (default)
    """

    @staticmethod
    def detect(context: Dict[str, Any]) -> Platform:
        """
        Detect platform from context metadata.

        Args:
            context: Request context with platform info

        Returns:
            Detected platform

        Example context (WhatsApp):
            {
                "platform": "whatsapp",
                "phone_number": "+1234567890",
                "message_id": "...",
            }

        Example context (Telegram):
            {
                "platform": "telegram",
                "user_id": "12345",
                "chat_id": "67890",
            }
        """
        platform_hint = context.get("platform", "").lower()

        if platform_hint == "whatsapp" or "whatsapp" in platform_hint:
            return Platform.WHATSAPP
        elif platform_hint == "telegram" or "telegram" in platform_hint:
            return Platform.TELEGRAM
        elif context.get("phone_number") or context.get("from_number"):
            # Infer WhatsApp if phone number present
            return Platform.WHATSAPP
        elif context.get("user_id") and context.get("chat_id"):
            # Infer Telegram if user_id + chat_id present
            return Platform.TELEGRAM
        elif platform_hint == "web":
            return Platform.WEB
        else:
            return Platform.WEB  # Default fallback

    @staticmethod
    def extract_phone(context: Dict[str, Any]) -> Optional[str]:
        """
        Extract phone number from platform context.

        Args:
            context: Platform context

        Returns:
            Phone number if available
        """
        # WhatsApp pattern
        if "phone_number" in context:
            return context["phone_number"]

        if "from_number" in context:
            return context["from_number"]

        # Telegram doesn't provide phone by default
        return None

    @staticmethod
    def should_skip_phone_collection(platform: Platform) -> bool:
        """
        Determine if phone collection should be skipped.

        Args:
            platform: Detected platform

        Returns:
            True if phone collection should be skipped
        """
        return platform in [Platform.WHATSAPP, Platform.TELEGRAM]
