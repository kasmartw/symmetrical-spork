"""Channel detection for conditional streaming.

WhatsApp and similar messaging platforms don't support SSE streaming,
so we need to detect the client type and return appropriate response format.
"""
from enum import Enum
from typing import Dict, Optional


class ChannelType(Enum):
    """Client channel types."""
    WEB = "web"
    WHATSAPP = "whatsapp"
    UNKNOWN = "unknown"


def detect_channel(
    headers: Dict[str, str],
    query_params: Optional[Dict[str, str]] = None
) -> ChannelType:
    """
    Detect client channel from request metadata.

    Detection order (precedence high to low):
    1. X-Channel header (explicit)
    2. User-Agent header (implicit)
    3. source query parameter
    4. Default to WEB

    Args:
        headers: Request headers dict (case-insensitive keys)
        query_params: Optional query parameters dict

    Returns:
        Detected ChannelType

    Examples:
        >>> detect_channel({"X-Channel": "whatsapp"})
        ChannelType.WHATSAPP

        >>> detect_channel({"User-Agent": "WhatsApp/2.23.1"})
        ChannelType.WHATSAPP

        >>> detect_channel({}, {"source": "web"})
        ChannelType.WEB
    """
    # Normalize header keys to lowercase for case-insensitive lookup
    headers_lower = {k.lower(): v for k, v in headers.items()}

    # 1. Check X-Channel header (explicit, highest priority)
    channel_header = headers_lower.get("x-channel", "").lower()
    if channel_header == "whatsapp":
        return ChannelType.WHATSAPP
    elif channel_header == "web":
        return ChannelType.WEB

    # 2. Check User-Agent for WhatsApp indicators
    user_agent = headers_lower.get("user-agent", "").lower()
    if "whatsapp" in user_agent:
        return ChannelType.WHATSAPP

    # 3. Check query parameter
    if query_params:
        source = query_params.get("source", "").lower()
        if source == "whatsapp":
            return ChannelType.WHATSAPP
        elif source == "web":
            return ChannelType.WEB

    # 4. Default to web (safest - supports streaming)
    return ChannelType.WEB


def should_stream(channel: ChannelType) -> bool:
    """
    Determine if streaming should be enabled for this channel.

    Streaming support by channel:
    - WEB: ✅ Supports SSE streaming
    - WHATSAPP: ❌ No streaming support (needs complete response)
    - UNKNOWN: ✅ Default to streaming (web-compatible)

    Args:
        channel: Detected channel type

    Returns:
        True if streaming should be enabled, False otherwise
    """
    return channel in (ChannelType.WEB, ChannelType.UNKNOWN)
