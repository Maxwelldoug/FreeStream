"""
FreeStream - Event processor service.
Processes stream events into TTS messages.
"""

import logging
import re
from typing import Optional

from better_profanity import profanity

from app.models.events import (
    StreamEvent,
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

logger = logging.getLogger(__name__)


class EventProcessor:
    """Processes stream events into TTS messages."""
    
    def __init__(self, config, tts_service, queue_service):
        self.config = config
        self.tts_service = tts_service
        self.queue_service = queue_service
        
        # Initialize profanity filter
        if config.TTS_PROFANITY_FILTER:
            profanity.load_censor_words()
        
        logger.info("Event processor initialized")
    
    def process_event(self, event: StreamEvent) -> bool:
        """
        Process a stream event.
        
        Args:
            event: The stream event to process
            
        Returns:
            True if event was processed and queued, False otherwise
        """
        # Check if event type is enabled
        if not self._is_event_enabled(event):
            logger.debug(f"Event type disabled: {event.event_type}")
            return False
        
        # Check thresholds
        if not self._meets_threshold(event):
            logger.debug(f"Event below threshold: {event.event_type}")
            return False
        
        # Format message
        text = self._format_message(event)
        if not text:
            logger.warning(f"Failed to format message for event: {event.id}")
            return False
        
        # Apply profanity filter
        if self.config.TTS_PROFANITY_FILTER:
            text = profanity.censor(text)
        
        # Clean text for TTS
        text = self._clean_text(text)
        
        # Generate TTS audio
        try:
            audio_path = self.tts_service.synthesize(text)
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            return False
        
        # Create TTS message
        message = TTSMessage(
            text=text,
            display_text=text,
            priority=event.get_priority(self.config),
            event=event,
            audio_path=audio_path,
        )
        
        # Add to queue
        return self.queue_service.add_message(message)
    
    def _is_event_enabled(self, event: StreamEvent) -> bool:
        """Check if the event type is enabled in config."""
        enabled_map = {
            EventType.TWITCH_BITS: self.config.TWITCH_BITS_ENABLED,
            EventType.TWITCH_SUB_NEW: self.config.TWITCH_SUBS_ENABLED,
            EventType.TWITCH_SUB_RESUB: self.config.TWITCH_SUBS_ENABLED,
            EventType.TWITCH_GIFT_SINGLE: self.config.TWITCH_GIFT_SUBS_ENABLED,
            EventType.TWITCH_GIFT_MULTI: self.config.TWITCH_GIFT_SUBS_ENABLED,
            EventType.TWITCH_CHANNEL_POINTS: self.config.TWITCH_CHANNEL_POINTS_ENABLED,
            EventType.YOUTUBE_SUPERCHAT: self.config.YOUTUBE_SUPERCHAT_ENABLED,
            EventType.YOUTUBE_SUPERSTICKER: self.config.YOUTUBE_SUPERSTICKER_ENABLED,
            EventType.YOUTUBE_MEMBERSHIP_NEW: self.config.YOUTUBE_MEMBERSHIP_ENABLED,
            EventType.YOUTUBE_MEMBERSHIP_MILESTONE: self.config.YOUTUBE_MEMBERSHIP_MILESTONE_ENABLED,
        }
        return enabled_map.get(event.event_type, False)
    
    def _meets_threshold(self, event: StreamEvent) -> bool:
        """Check if the event meets minimum threshold requirements."""
        if isinstance(event, TwitchBitsEvent):
            return event.amount >= self.config.TWITCH_BITS_MINIMUM
        
        elif isinstance(event, TwitchGiftSubEvent):
            return event.count >= self.config.TWITCH_GIFT_SUBS_MINIMUM
        
        elif isinstance(event, TwitchChannelPointsEvent):
            # Check if reward is in allowed list (empty list = all allowed)
            if self.config.TWITCH_CHANNEL_POINTS_REWARDS:
                return event.reward_id in self.config.TWITCH_CHANNEL_POINTS_REWARDS
            return True
        
        elif isinstance(event, (YouTubeSuperChatEvent, YouTubeSuperStickerEvent)):
            # Convert to cents for comparison
            amount_cents = int(event.amount * 100)
            return amount_cents >= self.config.YOUTUBE_SUPERCHAT_MINIMUM_CENTS
        
        return True
    
    def _format_message(self, event: StreamEvent) -> Optional[str]:
        """Format the event into a TTS message using templates."""
        templates = self.config.TEMPLATES
        
        try:
            if isinstance(event, TwitchBitsEvent):
                if event.message and self.config.TWITCH_BITS_READ_MESSAGE:
                    template = templates.get("twitch_bits", "{username} cheered {amount} bits: {message}")
                    return template.format(
                        username=event.username,
                        amount=event.amount,
                        message=event.message
                    )
                else:
                    template = templates.get("twitch_bits_no_message", "{username} cheered {amount} bits!")
                    return template.format(
                        username=event.username,
                        amount=event.amount
                    )
            
            elif isinstance(event, TwitchSubEvent):
                if event.is_resub:
                    if event.message and self.config.TWITCH_SUBS_READ_MESSAGE:
                        template = templates.get("twitch_sub_resub")
                        return template.format(
                            username=event.username,
                            tier=event.tier,
                            months=event.months,
                            message=event.message
                        )
                    else:
                        template = templates.get("twitch_sub_resub_no_message")
                        return template.format(
                            username=event.username,
                            tier=event.tier,
                            months=event.months
                        )
                else:
                    template = templates.get("twitch_sub_new")
                    return template.format(
                        username=event.username,
                        tier=event.tier
                    )
            
            elif isinstance(event, TwitchGiftSubEvent):
                if event.count == 1:
                    template = templates.get("twitch_gift_single")
                    return template.format(
                        username=event.username,
                        tier=event.tier,
                        recipient=event.recipient or "someone"
                    )
                else:
                    template = templates.get("twitch_gift_multi")
                    return template.format(
                        username=event.username,
                        tier=event.tier,
                        count=event.count
                    )
            
            elif isinstance(event, TwitchChannelPointsEvent):
                if event.user_input:
                    template = templates.get("twitch_channel_points")
                    return template.format(
                        username=event.username,
                        reward_name=event.reward_name,
                        user_input=event.user_input,
                        cost=event.cost
                    )
                else:
                    template = templates.get("twitch_channel_points_no_input")
                    return template.format(
                        username=event.username,
                        reward_name=event.reward_name,
                        cost=event.cost
                    )
            
            elif isinstance(event, YouTubeSuperChatEvent):
                if event.message and self.config.YOUTUBE_SUPERCHAT_READ_MESSAGE:
                    template = templates.get("youtube_superchat")
                    return template.format(
                        username=event.username,
                        currency=event.currency,
                        amount=f"{event.amount:.2f}",
                        message=event.message
                    )
                else:
                    template = templates.get("youtube_superchat_no_message")
                    return template.format(
                        username=event.username,
                        currency=event.currency,
                        amount=f"{event.amount:.2f}"
                    )
            
            elif isinstance(event, YouTubeSuperStickerEvent):
                template = templates.get("youtube_supersticker")
                return template.format(
                    username=event.username,
                    currency=event.currency,
                    amount=f"{event.amount:.2f}"
                )
            
            elif isinstance(event, YouTubeMembershipEvent):
                if event.is_milestone:
                    template = templates.get("youtube_membership_milestone")
                    return template.format(
                        username=event.username,
                        level=event.level or "member",
                        months=event.months
                    )
                else:
                    template = templates.get("youtube_membership_new")
                    return template.format(
                        username=event.username,
                        level=event.level or "member"
                    )
            
            logger.warning(f"Unknown event type: {type(event)}")
            return None
        
        except KeyError as e:
            logger.error(f"Template formatting error: missing key {e}")
            return None
        except Exception as e:
            logger.error(f"Message formatting error: {e}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean text for TTS (remove emotes, special characters, etc.)."""
        # Remove Twitch emotes (words in the format :word:)
        text = re.sub(r':[a-zA-Z0-9_]+:', '', text)
        
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove special characters that might cause TTS issues
        text = re.sub(r'[<>{}[\]|\\^~`]', '', text)
        
        # Limit repeated characters (e.g., "yaaaay" -> "yaay")
        text = re.sub(r'(.)\1{3,}', r'\1\1', text)
        
        return text
    
    def inject_test_event(self, event_type: str, **kwargs) -> bool:
        """
        Inject a test event for development/testing.
        
        Args:
            event_type: Type of event to inject
            **kwargs: Event-specific parameters
            
        Returns:
            True if event was processed successfully
        """
        event = None
        
        if event_type == "twitch_bits":
            event = TwitchBitsEvent(
                username=kwargs.get("username", "TestUser"),
                amount=kwargs.get("amount", 100),
                message=kwargs.get("message", "Test cheer message!")
            )
        
        elif event_type == "twitch_sub":
            event = TwitchSubEvent(
                username=kwargs.get("username", "TestUser"),
                tier=kwargs.get("tier", "1"),
                months=kwargs.get("months", 1),
                message=kwargs.get("message", ""),
                is_resub=kwargs.get("is_resub", False)
            )
        
        elif event_type == "twitch_gift":
            event = TwitchGiftSubEvent(
                username=kwargs.get("username", "TestUser"),
                tier=kwargs.get("tier", "1"),
                count=kwargs.get("count", 1),
                recipient=kwargs.get("recipient", "LuckyViewer")
            )
        
        elif event_type == "youtube_superchat":
            event = YouTubeSuperChatEvent(
                username=kwargs.get("username", "TestUser"),
                amount=kwargs.get("amount", 5.00),
                currency=kwargs.get("currency", "$"),
                message=kwargs.get("message", "Test super chat!")
            )
        
        elif event_type == "youtube_membership":
            event = YouTubeMembershipEvent(
                username=kwargs.get("username", "TestUser"),
                level=kwargs.get("level", "Member"),
                months=kwargs.get("months", 1),
                is_milestone=kwargs.get("is_milestone", False)
            )
        
        if event:
            logger.info(f"Injecting test event: {event_type}")
            return self.process_event(event)
        
        logger.warning(f"Unknown test event type: {event_type}")
        return False
