"""
FreeStream - Configuration loader.
Loads and validates settings from SETTINGS.py.
"""

import importlib.util
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# Default templates
DEFAULT_TEMPLATES = {
    # Twitch Templates
    "twitch_bits": "{username} cheered {amount} bits: {message}",
    "twitch_bits_no_message": "{username} cheered {amount} bits!",
    "twitch_sub_new": "{username} just subscribed at tier {tier}!",
    "twitch_sub_resub": "{username} resubscribed for {months} months at tier {tier}! {message}",
    "twitch_sub_resub_no_message": "{username} resubscribed for {months} months at tier {tier}!",
    "twitch_gift_single": "{username} gifted a tier {tier} sub to {recipient}!",
    "twitch_gift_multi": "{username} gifted {count} tier {tier} subs to the community!",
    "twitch_channel_points": "{username} redeemed {reward_name}: {user_input}",
    "twitch_channel_points_no_input": "{username} redeemed {reward_name}!",
    # YouTube Templates
    "youtube_superchat": "{username} sent {currency}{amount}: {message}",
    "youtube_superchat_no_message": "{username} sent a {currency}{amount} Super Chat!",
    "youtube_supersticker": "{username} sent a Super Sticker worth {currency}{amount}!",
    "youtube_membership_new": "{username} just became a {level} member!",
    "youtube_membership_milestone": "{username} has been a {level} member for {months} months!",
}


@dataclass
class Config:
    """Application configuration loaded from SETTINGS.py."""
    
    # Twitch API Configuration
    TWITCH_ENABLED: bool = True
    TWITCH_CLIENT_ID: str = ""
    TWITCH_CLIENT_SECRET: str = ""
    TWITCH_BROADCASTER_ID: str = ""
    TWITCH_REFRESH_TOKEN: str = ""
    TWITCH_WEBHOOK_CALLBACK_URL: str = ""
    TWITCH_WEBHOOK_SECRET: str = ""
    
    # Twitch Event Settings
    TWITCH_BITS_ENABLED: bool = True
    TWITCH_BITS_MINIMUM: int = 100
    TWITCH_BITS_READ_MESSAGE: bool = True
    TWITCH_SUBS_ENABLED: bool = True
    TWITCH_SUBS_READ_MESSAGE: bool = True
    TWITCH_GIFT_SUBS_ENABLED: bool = True
    TWITCH_GIFT_SUBS_MINIMUM: int = 1
    TWITCH_CHANNEL_POINTS_ENABLED: bool = False
    TWITCH_CHANNEL_POINTS_REWARDS: List[str] = field(default_factory=list)
    
    # YouTube API Configuration
    YOUTUBE_ENABLED: bool = True
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_CHANNEL_ID: str = ""
    YOUTUBE_REFRESH_TOKEN: str = ""
    YOUTUBE_POLL_INTERVAL: int = 5
    
    # YouTube Event Settings
    YOUTUBE_SUPERCHAT_ENABLED: bool = True
    YOUTUBE_SUPERCHAT_MINIMUM_CENTS: int = 100
    YOUTUBE_SUPERCHAT_READ_MESSAGE: bool = True
    YOUTUBE_SUPERSTICKER_ENABLED: bool = True
    YOUTUBE_MEMBERSHIP_ENABLED: bool = True
    YOUTUBE_MEMBERSHIP_MILESTONE_ENABLED: bool = True
    
    # TTS Configuration
    TTS_VOICE: str = "en_GB-alan-medium"
    TTS_SPEED: float = 1.0
    TTS_VOLUME: float = 1.0
    TTS_MAX_MESSAGE_LENGTH: int = 300
    TTS_PROFANITY_FILTER: bool = True
    
    # Message Templates
    TEMPLATES: Dict[str, str] = field(default_factory=lambda: DEFAULT_TEMPLATES.copy())
    
    # Web Server Configuration
    WEB_HOST: str = "0.0.0.0"
    WEB_PORT: int = 5000
    WEB_DEBUG: bool = False
    
    # OBS Overlay Settings
    OVERLAY_FONT_FAMILY: str = "Roboto, Arial, sans-serif"
    OVERLAY_FONT_SIZE: int = 24
    OVERLAY_TEXT_COLOR: str = "#FFFFFF"
    OVERLAY_TEXT_SHADOW: str = "2px 2px 4px rgba(0,0,0,0.8)"
    OVERLAY_BACKGROUND_COLOR: str = "transparent"
    OVERLAY_ANIMATION: str = "fade"
    OVERLAY_ANIMATION_DURATION: int = 300
    OVERLAY_SHOW_TEXT: bool = True
    OVERLAY_TEXT_DURATION: int = 0
    OVERLAY_TEXT_POSITION: str = "bottom"
    
    # Queue and Rate Limiting
    QUEUE_MAX_SIZE: int = 50
    QUEUE_DUPLICATE_WINDOW: int = 5
    RATE_LIMIT_TWITCH: int = 30
    RATE_LIMIT_YOUTUBE: int = 30
    
    # Priority Settings
    PRIORITY_TWITCH_BITS: int = 2
    PRIORITY_TWITCH_SUBS: int = 3
    PRIORITY_TWITCH_GIFT_SUBS: int = 2
    PRIORITY_TWITCH_CHANNEL_POINTS: int = 1
    PRIORITY_YOUTUBE_SUPERCHAT: int = 2
    PRIORITY_YOUTUBE_MEMBERSHIP: int = 3
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = ""
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Advanced Settings
    TOKEN_STORAGE_PATH: str = "/app/data/tokens.json"
    AUDIO_CACHE_PATH: str = "/app/data/audio_cache"
    AUDIO_CACHE_MAX_SIZE_MB: int = 100
    AUDIO_CACHE_TTL_HOURS: int = 24
    HEALTH_CHECK_ENABLED: bool = True
    HEALTH_CHECK_PATH: str = "/health"
    WEBSOCKET_PING_INTERVAL: int = 25
    WEBSOCKET_PING_TIMEOUT: int = 120
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_BACKOFF_BASE: int = 2
    RETRY_BACKOFF_MAX: int = 60
    
    def __post_init__(self):
        """Load settings from SETTINGS.py file."""
        self._load_settings()
        self._validate()
    
    def _load_settings(self):
        """Load settings from SETTINGS.py."""
        settings_paths = [
            "/app/SETTINGS.py",  # Docker mount path
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "SETTINGS.py"),  # Local path
        ]
        
        settings_module = None
        for path in settings_paths:
            if os.path.exists(path):
                logger.info(f"Loading settings from {path}")
                spec = importlib.util.spec_from_file_location("settings", path)
                settings_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(settings_module)
                break
        
        if settings_module is None:
            logger.warning("SETTINGS.py not found, using defaults")
            return
        
        # Load all settings from the module
        for attr in dir(self):
            if attr.isupper() and not attr.startswith('_'):
                if hasattr(settings_module, attr):
                    value = getattr(settings_module, attr)
                    setattr(self, attr, value)
                    logger.debug(f"Loaded setting: {attr}")
        
        # Merge templates with defaults
        if hasattr(settings_module, 'TEMPLATES'):
            merged_templates = DEFAULT_TEMPLATES.copy()
            merged_templates.update(settings_module.TEMPLATES)
            self.TEMPLATES = merged_templates
    
    def _validate(self):
        """Validate configuration values."""
        errors = []
        
        # Validate Twitch settings if enabled
        if self.TWITCH_ENABLED:
            if not self.TWITCH_CLIENT_ID:
                logger.warning("Twitch enabled but TWITCH_CLIENT_ID not set")
            if not self.TWITCH_CLIENT_SECRET:
                logger.warning("Twitch enabled but TWITCH_CLIENT_SECRET not set")
        
        # Validate YouTube settings if enabled
        if self.YOUTUBE_ENABLED:
            if not self.YOUTUBE_CLIENT_ID:
                logger.warning("YouTube enabled but YOUTUBE_CLIENT_ID not set")
            if not self.YOUTUBE_CLIENT_SECRET:
                logger.warning("YouTube enabled but YOUTUBE_CLIENT_SECRET not set")
        
        # Validate TTS settings
        if not 0.5 <= self.TTS_SPEED <= 2.0:
            errors.append(f"TTS_SPEED must be between 0.5 and 2.0, got {self.TTS_SPEED}")
        
        if not 0.0 <= self.TTS_VOLUME <= 1.0:
            errors.append(f"TTS_VOLUME must be between 0.0 and 1.0, got {self.TTS_VOLUME}")
        
        # Validate overlay settings
        valid_animations = ["fade", "slide-up", "slide-down", "slide-left", "slide-right", "none"]
        if self.OVERLAY_ANIMATION not in valid_animations:
            errors.append(f"OVERLAY_ANIMATION must be one of {valid_animations}")
        
        valid_positions = ["top", "center", "bottom"]
        if self.OVERLAY_TEXT_POSITION not in valid_positions:
            errors.append(f"OVERLAY_TEXT_POSITION must be one of {valid_positions}")
        
        # Log errors
        for error in errors:
            logger.error(f"Configuration error: {error}")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def get_overlay_css_vars(self) -> Dict[str, str]:
        """Get CSS variables for the overlay."""
        return {
            "--font-family": self.OVERLAY_FONT_FAMILY,
            "--font-size": f"{self.OVERLAY_FONT_SIZE}px",
            "--text-color": self.OVERLAY_TEXT_COLOR,
            "--text-shadow": self.OVERLAY_TEXT_SHADOW,
            "--background-color": self.OVERLAY_BACKGROUND_COLOR,
            "--animation-duration": f"{self.OVERLAY_ANIMATION_DURATION}ms",
        }
    
    def to_public_dict(self) -> Dict:
        """Return non-sensitive settings for the API."""
        return {
            "twitch_enabled": self.TWITCH_ENABLED,
            "youtube_enabled": self.YOUTUBE_ENABLED,
            "tts_voice": self.TTS_VOICE,
            "overlay": {
                "font_family": self.OVERLAY_FONT_FAMILY,
                "font_size": self.OVERLAY_FONT_SIZE,
                "text_color": self.OVERLAY_TEXT_COLOR,
                "animation": self.OVERLAY_ANIMATION,
                "show_text": self.OVERLAY_SHOW_TEXT,
                "text_position": self.OVERLAY_TEXT_POSITION,
            }
        }
