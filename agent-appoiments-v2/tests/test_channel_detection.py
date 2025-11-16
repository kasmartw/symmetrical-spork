"""Test channel detection logic."""
import pytest
from src.channel_detector import detect_channel, ChannelType, should_stream


def test_detect_whatsapp_from_header():
    """Detect WhatsApp from X-Channel header."""
    headers = {"X-Channel": "whatsapp"}
    assert detect_channel(headers) == ChannelType.WHATSAPP


def test_detect_web_from_header():
    """Detect web from X-Channel header."""
    headers = {"X-Channel": "web"}
    assert detect_channel(headers) == ChannelType.WEB


def test_detect_whatsapp_from_user_agent():
    """Detect WhatsApp from User-Agent."""
    headers = {"User-Agent": "WhatsApp/2.23.1"}
    assert detect_channel(headers) == ChannelType.WHATSAPP


def test_detect_web_default():
    """Default to web when no channel indicators."""
    headers = {}
    assert detect_channel(headers) == ChannelType.WEB


def test_detect_from_source_param():
    """Detect channel from source query parameter."""
    params = {"source": "whatsapp"}
    assert detect_channel({}, query_params=params) == ChannelType.WHATSAPP


def test_header_precedence_over_param():
    """X-Channel header takes precedence over query param."""
    headers = {"X-Channel": "web"}
    params = {"source": "whatsapp"}
    assert detect_channel(headers, query_params=params) == ChannelType.WEB


def test_should_stream_web():
    """Web channel should enable streaming."""
    assert should_stream(ChannelType.WEB) is True


def test_should_not_stream_whatsapp():
    """WhatsApp channel should disable streaming."""
    assert should_stream(ChannelType.WHATSAPP) is False


def test_case_insensitive_detection():
    """Channel detection should be case-insensitive."""
    assert detect_channel({"x-channel": "WHATSAPP"}) == ChannelType.WHATSAPP
    assert detect_channel({"X-CHANNEL": "web"}) == ChannelType.WEB
