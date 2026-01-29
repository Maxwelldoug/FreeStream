"""
FreeStream - Tests for event models.
"""

import pytest
from datetime import datetime

from app.models.events import (
    Platform,
    EventType,
    TwitchBitsEvent,
    TwitchSubEvent,
    TwitchGiftSubEvent,
    TwitchChannelPointsEvent,
    YouTubeSuperChatEvent,
    YouTubeSuperStickerEvent,
    YouTubeMembershipEvent,
    TTSMessage,
)


class TestTwitchBitsEvent:
    """Tests for TwitchBitsEvent."""
    
    def test_create_bits_event(self):
        """Test creating a bits event."""
        event = TwitchBitsEvent(
            username="TestUser",
            amount=100,
            message="PogChamp"
        )
        
        assert event.platform == Platform.TWITCH
        assert event.event_type == EventType.TWITCH_BITS
        assert event.username == "TestUser"
        assert event.amount == 100
        assert event.message == "PogChamp"
    
    def test_from_eventsub(self):
        """Test creating from EventSub payload."""
        data = {
            "user_name": "CoolStreamer",
            "bits": 500,
            "message": "Here's some bits!",
            "is_anonymous": False
        }
        
        event = TwitchBitsEvent.from_eventsub(data)
        
        assert event.username == "CoolStreamer"
        assert event.amount == 500
        assert event.message == "Here's some bits!"
        assert not event.is_anonymous
    
    def test_anonymous_bits(self):
        """Test anonymous bits event."""
        data = {
            "user_name": "CoolStreamer",
            "bits": 100,
            "message": "",
            "is_anonymous": True
        }
        
        event = TwitchBitsEvent.from_eventsub(data)
        
        assert event.username == "Anonymous"
        assert event.is_anonymous


class TestTwitchSubEvent:
    """Tests for TwitchSubEvent."""
    
    def test_new_sub(self):
        """Test new subscription event."""
        event = TwitchSubEvent(
            username="NewSub",
            tier="1",
            is_resub=False
        )
        
        assert event.event_type == EventType.TWITCH_SUB_NEW
        assert event.tier == "1"
    
    def test_resub(self):
        """Test resub event."""
        event = TwitchSubEvent(
            username="Resub",
            tier="2",
            months=12,
            message="Thanks for the content!",
            is_resub=True
        )
        
        assert event.event_type == EventType.TWITCH_SUB_RESUB
        assert event.months == 12
        assert event.message == "Thanks for the content!"


class TestTwitchGiftSubEvent:
    """Tests for TwitchGiftSubEvent."""
    
    def test_single_gift(self):
        """Test single gift sub."""
        event = TwitchGiftSubEvent(
            username="Gifter",
            tier="1",
            count=1,
            recipient="LuckyViewer"
        )
        
        assert event.event_type == EventType.TWITCH_GIFT_SINGLE
        assert event.count == 1
    
    def test_multi_gift(self):
        """Test multi gift subs."""
        event = TwitchGiftSubEvent(
            username="BigGifter",
            tier="1",
            count=50
        )
        
        assert event.event_type == EventType.TWITCH_GIFT_MULTI
        assert event.count == 50


class TestYouTubeEvents:
    """Tests for YouTube events."""
    
    def test_superchat(self):
        """Test Super Chat event."""
        event = YouTubeSuperChatEvent(
            username="Supporter",
            amount=10.00,
            currency="$",
            message="Great stream!"
        )
        
        assert event.platform == Platform.YOUTUBE
        assert event.event_type == EventType.YOUTUBE_SUPERCHAT
        assert event.amount == 10.00
    
    def test_membership(self):
        """Test membership event."""
        event = YouTubeMembershipEvent(
            username="NewMember",
            level="Channel Member",
            is_milestone=False
        )
        
        assert event.event_type == EventType.YOUTUBE_MEMBERSHIP_NEW
    
    def test_membership_milestone(self):
        """Test membership milestone event."""
        event = YouTubeMembershipEvent(
            username="LoyalMember",
            level="VIP",
            months=12,
            is_milestone=True
        )
        
        assert event.event_type == EventType.YOUTUBE_MEMBERSHIP_MILESTONE
        assert event.months == 12


class TestTTSMessage:
    """Tests for TTSMessage."""
    
    def test_create_message(self):
        """Test creating a TTS message."""
        message = TTSMessage(
            text="Hello world",
            priority=2
        )
        
        assert message.text == "Hello world"
        assert message.priority == 2
        assert message.id is not None
    
    def test_to_dict(self):
        """Test converting message to dictionary."""
        event = TwitchBitsEvent(username="Test", amount=100)
        message = TTSMessage(
            text="Test message",
            display_text="Test display",
            priority=3,
            event=event
        )
        
        data = message.to_dict()
        
        assert data["text"] == "Test display"
        assert data["priority"] == 3
        assert data["event_type"] == "twitch_bits"
        assert data["platform"] == "twitch"
