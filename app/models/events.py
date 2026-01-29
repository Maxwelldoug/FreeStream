"""
FreeStream - Event data models.
Dataclasses for platform events and TTS messages.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class Platform(str, Enum):
    """Supported streaming platforms."""
    TWITCH = "twitch"
    YOUTUBE = "youtube"


class EventType(str, Enum):
    """Types of monetization events."""
    # Twitch events
    TWITCH_BITS = "twitch_bits"
    TWITCH_SUB_NEW = "twitch_sub_new"
    TWITCH_SUB_RESUB = "twitch_sub_resub"
    TWITCH_GIFT_SINGLE = "twitch_gift_single"
    TWITCH_GIFT_MULTI = "twitch_gift_multi"
    TWITCH_CHANNEL_POINTS = "twitch_channel_points"
    
    # YouTube events
    YOUTUBE_SUPERCHAT = "youtube_superchat"
    YOUTUBE_SUPERSTICKER = "youtube_supersticker"
    YOUTUBE_MEMBERSHIP_NEW = "youtube_membership_new"
    YOUTUBE_MEMBERSHIP_MILESTONE = "youtube_membership_milestone"


@dataclass
class StreamEvent:
    """Base class for all stream events."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    platform: Platform = Platform.TWITCH
    event_type: EventType = EventType.TWITCH_BITS
    username: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    raw_data: dict = field(default_factory=dict)
    
    def get_priority(self, config) -> int:
        """Get the priority for this event type."""
        priority_map = {
            EventType.TWITCH_BITS: config.PRIORITY_TWITCH_BITS,
            EventType.TWITCH_SUB_NEW: config.PRIORITY_TWITCH_SUBS,
            EventType.TWITCH_SUB_RESUB: config.PRIORITY_TWITCH_SUBS,
            EventType.TWITCH_GIFT_SINGLE: config.PRIORITY_TWITCH_GIFT_SUBS,
            EventType.TWITCH_GIFT_MULTI: config.PRIORITY_TWITCH_GIFT_SUBS,
            EventType.TWITCH_CHANNEL_POINTS: config.PRIORITY_TWITCH_CHANNEL_POINTS,
            EventType.YOUTUBE_SUPERCHAT: config.PRIORITY_YOUTUBE_SUPERCHAT,
            EventType.YOUTUBE_SUPERSTICKER: config.PRIORITY_YOUTUBE_SUPERCHAT,
            EventType.YOUTUBE_MEMBERSHIP_NEW: config.PRIORITY_YOUTUBE_MEMBERSHIP,
            EventType.YOUTUBE_MEMBERSHIP_MILESTONE: config.PRIORITY_YOUTUBE_MEMBERSHIP,
        }
        return priority_map.get(self.event_type, 1)


@dataclass
class TwitchBitsEvent(StreamEvent):
    """Twitch bits cheer event."""
    platform: Platform = Platform.TWITCH
    event_type: EventType = EventType.TWITCH_BITS
    amount: int = 0
    message: str = ""
    is_anonymous: bool = False
    
    @classmethod
    def from_eventsub(cls, data: dict) -> "TwitchBitsEvent":
        """Create from Twitch EventSub payload."""
        return cls(
            username=data.get("user_name", "Anonymous") if not data.get("is_anonymous") else "Anonymous",
            amount=data.get("bits", 0),
            message=data.get("message", ""),
            is_anonymous=data.get("is_anonymous", False),
            raw_data=data
        )


@dataclass
class TwitchSubEvent(StreamEvent):
    """Twitch subscription event."""
    platform: Platform = Platform.TWITCH
    event_type: EventType = EventType.TWITCH_SUB_NEW
    tier: str = "1"  # "1", "2", or "3"
    months: int = 1
    message: str = ""
    is_resub: bool = False
    
    def __post_init__(self):
        if self.is_resub:
            self.event_type = EventType.TWITCH_SUB_RESUB
    
    @classmethod
    def from_eventsub_subscribe(cls, data: dict) -> "TwitchSubEvent":
        """Create from channel.subscribe EventSub payload."""
        tier_map = {"1000": "1", "2000": "2", "3000": "3"}
        return cls(
            username=data.get("user_name", ""),
            tier=tier_map.get(data.get("tier", "1000"), "1"),
            is_resub=False,
            raw_data=data
        )
    
    @classmethod
    def from_eventsub_message(cls, data: dict) -> "TwitchSubEvent":
        """Create from channel.subscription.message EventSub payload."""
        tier_map = {"1000": "1", "2000": "2", "3000": "3"}
        return cls(
            username=data.get("user_name", ""),
            tier=tier_map.get(data.get("tier", "1000"), "1"),
            months=data.get("cumulative_months", 1),
            message=data.get("message", {}).get("text", ""),
            is_resub=True,
            raw_data=data
        )


@dataclass
class TwitchGiftSubEvent(StreamEvent):
    """Twitch gift subscription event."""
    platform: Platform = Platform.TWITCH
    event_type: EventType = EventType.TWITCH_GIFT_SINGLE
    tier: str = "1"
    count: int = 1
    recipient: str = ""
    cumulative_total: int = 0
    is_anonymous: bool = False
    
    def __post_init__(self):
        if self.count > 1:
            self.event_type = EventType.TWITCH_GIFT_MULTI
    
    @classmethod
    def from_eventsub(cls, data: dict) -> "TwitchGiftSubEvent":
        """Create from channel.subscription.gift EventSub payload."""
        tier_map = {"1000": "1", "2000": "2", "3000": "3"}
        count = data.get("total", 1)
        return cls(
            username=data.get("user_name", "Anonymous") if not data.get("is_anonymous") else "Anonymous",
            tier=tier_map.get(data.get("tier", "1000"), "1"),
            count=count,
            cumulative_total=data.get("cumulative_total", 0),
            is_anonymous=data.get("is_anonymous", False),
            raw_data=data
        )


@dataclass
class TwitchChannelPointsEvent(StreamEvent):
    """Twitch channel points redemption event."""
    platform: Platform = Platform.TWITCH
    event_type: EventType = EventType.TWITCH_CHANNEL_POINTS
    reward_id: str = ""
    reward_name: str = ""
    cost: int = 0
    user_input: str = ""
    
    @classmethod
    def from_eventsub(cls, data: dict) -> "TwitchChannelPointsEvent":
        """Create from channel.channel_points_custom_reward_redemption.add EventSub payload."""
        reward = data.get("reward", {})
        return cls(
            username=data.get("user_name", ""),
            reward_id=reward.get("id", ""),
            reward_name=reward.get("title", ""),
            cost=reward.get("cost", 0),
            user_input=data.get("user_input", ""),
            raw_data=data
        )


@dataclass
class YouTubeSuperChatEvent(StreamEvent):
    """YouTube Super Chat event."""
    platform: Platform = Platform.YOUTUBE
    event_type: EventType = EventType.YOUTUBE_SUPERCHAT
    amount: float = 0.0
    currency: str = "$"
    message: str = ""
    
    @classmethod
    def from_livechat(cls, data: dict) -> "YouTubeSuperChatEvent":
        """Create from YouTube LiveChat API response."""
        snippet = data.get("snippet", {})
        details = snippet.get("superChatDetails", {})
        author = data.get("authorDetails", {})
        
        # Extract currency symbol
        amount_display = details.get("amountDisplayString", "$0")
        currency = amount_display[0] if amount_display else "$"
        
        return cls(
            username=author.get("displayName", ""),
            amount=details.get("amountMicros", 0) / 1_000_000,
            currency=currency,
            message=details.get("userComment", ""),
            raw_data=data
        )


@dataclass
class YouTubeSuperStickerEvent(StreamEvent):
    """YouTube Super Sticker event."""
    platform: Platform = Platform.YOUTUBE
    event_type: EventType = EventType.YOUTUBE_SUPERSTICKER
    amount: float = 0.0
    currency: str = "$"
    sticker_id: str = ""
    
    @classmethod
    def from_livechat(cls, data: dict) -> "YouTubeSuperStickerEvent":
        """Create from YouTube LiveChat API response."""
        snippet = data.get("snippet", {})
        details = snippet.get("superStickerDetails", {})
        author = data.get("authorDetails", {})
        
        amount_display = details.get("amountDisplayString", "$0")
        currency = amount_display[0] if amount_display else "$"
        
        return cls(
            username=author.get("displayName", ""),
            amount=details.get("amountMicros", 0) / 1_000_000,
            currency=currency,
            sticker_id=details.get("superStickerMetadata", {}).get("stickerId", ""),
            raw_data=data
        )


@dataclass
class YouTubeMembershipEvent(StreamEvent):
    """YouTube membership event."""
    platform: Platform = Platform.YOUTUBE
    event_type: EventType = EventType.YOUTUBE_MEMBERSHIP_NEW
    level: str = ""
    months: int = 0
    is_milestone: bool = False
    
    def __post_init__(self):
        if self.is_milestone:
            self.event_type = EventType.YOUTUBE_MEMBERSHIP_MILESTONE
    
    @classmethod
    def from_livechat(cls, data: dict, is_milestone: bool = False) -> "YouTubeMembershipEvent":
        """Create from YouTube LiveChat API response."""
        snippet = data.get("snippet", {})
        author = data.get("authorDetails", {})
        
        if is_milestone:
            details = snippet.get("memberMilestoneChatDetails", {})
            months = details.get("memberMonth", 0)
            level = details.get("memberLevelName", "")
        else:
            details = snippet.get("newSponsorDetails", {})
            months = 1
            level = details.get("memberLevelName", "")
        
        return cls(
            username=author.get("displayName", ""),
            level=level,
            months=months,
            is_milestone=is_milestone,
            raw_data=data
        )


@dataclass
class TTSMessage:
    """A message ready for text-to-speech conversion."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    display_text: str = ""  # Text shown in overlay (may differ from spoken text)
    priority: int = 1
    event: Optional[StreamEvent] = None
    audio_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "text": self.display_text or self.text,
            "priority": self.priority,
            "event_type": self.event.event_type.value if self.event else None,
            "platform": self.event.platform.value if self.event else None,
            "created_at": self.created_at.isoformat(),
        }
