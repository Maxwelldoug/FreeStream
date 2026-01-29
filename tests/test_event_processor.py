"""
FreeStream - Tests for event processor.
"""

import pytest
from unittest.mock import Mock, MagicMock

from app.models.events import (
    TwitchBitsEvent,
    TwitchSubEvent,
    TwitchGiftSubEvent,
    YouTubeSuperChatEvent,
    YouTubeMembershipEvent,
)
from app.services.event_processor import EventProcessor


class MockConfig:
    """Mock configuration for testing."""
    
    TWITCH_BITS_ENABLED = True
    TWITCH_BITS_MINIMUM = 100
    TWITCH_BITS_READ_MESSAGE = True
    TWITCH_SUBS_ENABLED = True
    TWITCH_SUBS_READ_MESSAGE = True
    TWITCH_GIFT_SUBS_ENABLED = True
    TWITCH_GIFT_SUBS_MINIMUM = 1
    TWITCH_CHANNEL_POINTS_ENABLED = False
    TWITCH_CHANNEL_POINTS_REWARDS = []
    
    YOUTUBE_SUPERCHAT_ENABLED = True
    YOUTUBE_SUPERCHAT_MINIMUM_CENTS = 100
    YOUTUBE_SUPERCHAT_READ_MESSAGE = True
    YOUTUBE_SUPERSTICKER_ENABLED = True
    YOUTUBE_MEMBERSHIP_ENABLED = True
    YOUTUBE_MEMBERSHIP_MILESTONE_ENABLED = True
    
    TTS_MAX_MESSAGE_LENGTH = 300
    TTS_PROFANITY_FILTER = True
    
    PRIORITY_TWITCH_BITS = 2
    PRIORITY_TWITCH_SUBS = 3
    PRIORITY_TWITCH_GIFT_SUBS = 2
    PRIORITY_TWITCH_CHANNEL_POINTS = 1
    PRIORITY_YOUTUBE_SUPERCHAT = 2
    PRIORITY_YOUTUBE_MEMBERSHIP = 3
    
    TEMPLATES = {
        "twitch_bits": "{username} cheered {amount} bits: {message}",
        "twitch_bits_no_message": "{username} cheered {amount} bits!",
        "twitch_sub_new": "{username} just subscribed at tier {tier}!",
        "twitch_sub_resub": "{username} resubscribed for {months} months: {message}",
        "twitch_sub_resub_no_message": "{username} resubscribed for {months} months!",
        "twitch_gift_single": "{username} gifted a sub to {recipient}!",
        "twitch_gift_multi": "{username} gifted {count} subs!",
        "youtube_superchat": "{username} sent {currency}{amount}: {message}",
        "youtube_superchat_no_message": "{username} sent {currency}{amount}!",
        "youtube_membership_new": "{username} became a {level} member!",
        "youtube_membership_milestone": "{username} has been a member for {months} months!",
    }


@pytest.fixture
def mock_tts_service():
    """Create a mock TTS service."""
    service = Mock()
    service.synthesize.return_value = "/path/to/audio.wav"
    return service


@pytest.fixture
def mock_queue_service():
    """Create a mock queue service."""
    service = Mock()
    service.add_message.return_value = True
    return service


@pytest.fixture
def processor(mock_tts_service, mock_queue_service):
    """Create an event processor with mocked services."""
    return EventProcessor(MockConfig(), mock_tts_service, mock_queue_service)


class TestEventProcessing:
    """Tests for event processing."""
    
    def test_process_bits_event(self, processor, mock_tts_service, mock_queue_service):
        """Test processing a bits event."""
        event = TwitchBitsEvent(
            username="Cheerer",
            amount=100,
            message="Great stream!"
        )
        
        result = processor.process_event(event)
        
        assert result is True
        mock_tts_service.synthesize.assert_called_once()
        mock_queue_service.add_message.assert_called_once()
    
    def test_bits_below_minimum(self, processor, mock_tts_service):
        """Test bits below minimum threshold are ignored."""
        event = TwitchBitsEvent(
            username="SmallCheerer",
            amount=50,
            message="Small cheer"
        )
        
        result = processor.process_event(event)
        
        assert result is False
        mock_tts_service.synthesize.assert_not_called()
    
    def test_process_sub_event(self, processor, mock_tts_service, mock_queue_service):
        """Test processing a subscription event."""
        event = TwitchSubEvent(
            username="NewSub",
            tier="1",
            is_resub=False
        )
        
        result = processor.process_event(event)
        
        assert result is True
        mock_tts_service.synthesize.assert_called_once()
    
    def test_process_superchat(self, processor, mock_tts_service, mock_queue_service):
        """Test processing a Super Chat event."""
        event = YouTubeSuperChatEvent(
            username="BigDonor",
            amount=5.00,
            currency="$",
            message="Amazing content!"
        )
        
        result = processor.process_event(event)
        
        assert result is True
        mock_tts_service.synthesize.assert_called_once()
    
    def test_superchat_below_minimum(self, processor, mock_tts_service):
        """Test Super Chat below minimum is ignored."""
        event = YouTubeSuperChatEvent(
            username="SmallDonor",
            amount=0.50,  # 50 cents < 100 cents minimum
            currency="$",
            message="Small donation"
        )
        
        result = processor.process_event(event)
        
        assert result is False
        mock_tts_service.synthesize.assert_not_called()


class TestTextCleaning:
    """Tests for text cleaning."""
    
    def test_clean_emotes(self, processor):
        """Test that emotes are removed."""
        text = "Hello :PogChamp: world :Kappa:"
        cleaned = processor._clean_text(text)
        
        assert ":PogChamp:" not in cleaned
        assert ":Kappa:" not in cleaned
        assert "Hello" in cleaned
    
    def test_clean_urls(self, processor):
        """Test that URLs are removed."""
        text = "Check out https://example.com for more!"
        cleaned = processor._clean_text(text)
        
        assert "https://example.com" not in cleaned
        assert "Check out" in cleaned
    
    def test_clean_repeated_chars(self, processor):
        """Test that repeated characters are limited."""
        text = "Yaaaaaaaay"
        cleaned = processor._clean_text(text)
        
        # Should be reduced to max 2 repeated chars
        assert cleaned == "Yaay"


class TestMessageFormatting:
    """Tests for message formatting."""
    
    def test_format_bits_with_message(self, processor):
        """Test formatting bits with a message."""
        event = TwitchBitsEvent(
            username="Cheerer",
            amount=100,
            message="Nice!"
        )
        
        text = processor._format_message(event)
        
        assert "Cheerer" in text
        assert "100" in text
        assert "Nice!" in text
    
    def test_format_bits_no_message(self, processor):
        """Test formatting bits without a message."""
        event = TwitchBitsEvent(
            username="Cheerer",
            amount=100,
            message=""
        )
        
        text = processor._format_message(event)
        
        assert "Cheerer" in text
        assert "100" in text
    
    def test_format_gift_sub(self, processor):
        """Test formatting gift sub."""
        event = TwitchGiftSubEvent(
            username="Gifter",
            tier="1",
            count=1,
            recipient="Lucky"
        )
        
        text = processor._format_message(event)
        
        assert "Gifter" in text
        assert "Lucky" in text
