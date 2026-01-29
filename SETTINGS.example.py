# =============================================================================
# FREESTREAM CONFIGURATION
# =============================================================================
# Copy this file to SETTINGS.py and fill in your values.
# SETTINGS.py is gitignored and will not be committed to version control.
# =============================================================================

# -----------------------------------------------------------------------------
# TWITCH API CONFIGURATION
# -----------------------------------------------------------------------------
# Set to False to completely disable Twitch integration
TWITCH_ENABLED = True

# Twitch Application Credentials
# Create an app at: https://dev.twitch.tv/console
# Set OAuth Redirect URL to: http://localhost:5000/auth/twitch/callback
TWITCH_CLIENT_ID = ""           # Your Twitch app Client ID
TWITCH_CLIENT_SECRET = ""       # Your Twitch app Client Secret

# Twitch Channel Configuration
TWITCH_BROADCASTER_ID = ""      # Your numeric broadcaster ID
                                 # Find it at: https://www.streamweasels.com/tools/convert-twitch-username-to-user-id/

# OAuth Tokens (Access token is auto-populated via the Refresh Token)
TWITCH_REFRESH_TOKEN = ""

# ----- Development Setup -----
# For local development, use ngrok: ngrok http 5000
# Then set the URL to your ngrok HTTPS URL
TWITCH_WEBHOOK_CALLBACK_URL = ""  # e.g., "https://abc123.ngrok.io/webhooks/twitch"
TWITCH_WEBHOOK_SECRET = ""        # Generate with: python -c "import secrets; print(secrets.token_hex(32))"

# -----------------------------------------------------------------------------
# TWITCH EVENT SETTINGS
# -----------------------------------------------------------------------------

# Bits Configuration
TWITCH_BITS_ENABLED = True          # Enable TTS for Bit cheers
TWITCH_BITS_MINIMUM = 100           # Minimum bits to trigger TTS (0 = all bits)
TWITCH_BITS_READ_MESSAGE = True     # Read the message attached to the cheer

# Subscription Configuration
TWITCH_SUBS_ENABLED = True          # Enable TTS for new subscriptions
TWITCH_SUBS_READ_MESSAGE = True     # Read the subscription message
TWITCH_GIFT_SUBS_ENABLED = True     # Enable TTS for gift subs
TWITCH_GIFT_SUBS_MINIMUM = 1        # Minimum gift count to trigger TTS

# Channel Points Configuration
TWITCH_CHANNEL_POINTS_ENABLED = False    # Enable TTS for channel point redemptions
TWITCH_CHANNEL_POINTS_REWARDS = []      # List of specific reward IDs to trigger TTS
                                         # Empty list = ALL rewards trigger TTS
                                         # Example: ["reward-uuid-1", "reward-uuid-2"]
                                         # Find IDs via Twitch API or browser dev tools

# -----------------------------------------------------------------------------
# YOUTUBE API CONFIGURATION
# -----------------------------------------------------------------------------
# Set to False to completely disable YouTube integration
YOUTUBE_ENABLED = True

# Google Cloud OAuth Credentials
# 1. Go to: https://console.cloud.google.com/
# 2. Create a project or select existing
# 3. Enable "YouTube Data API v3"
# 4. Go to Credentials > Create Credentials > OAuth 2.0 Client ID
# 5. Application type: Web application
# 6. Add authorized redirect URI: http://localhost:5000/auth/youtube/callback
YOUTUBE_CLIENT_ID = ""
YOUTUBE_CLIENT_SECRET = ""

# YouTube Channel Configuration
# Find your channel ID: https://www.youtube.com/account_advanced
YOUTUBE_CHANNEL_ID = ""

# OAuth Tokens (Access token is auto-populated via the Refresh Token)
YOUTUBE_REFRESH_TOKEN = ""

# Live Chat Polling Configuration
# YouTube API has daily quota limits (default 10,000 units/day)
# Each poll costs ~5 units, so 5 second interval = ~86,400 units/day
# Adjust based on your quota and responsiveness needs
YOUTUBE_POLL_INTERVAL = 5  # Seconds between polls (minimum recommended: 3)

# -----------------------------------------------------------------------------
# YOUTUBE EVENT SETTINGS
# -----------------------------------------------------------------------------

# Super Chat Configuration
YOUTUBE_SUPERCHAT_ENABLED = True        # Enable TTS for Super Chats
YOUTUBE_SUPERCHAT_MINIMUM_CENTS = 100   # Minimum amount in US cents ($100 = 100)
YOUTUBE_SUPERCHAT_READ_MESSAGE = True   # Read the Super Chat message

# Super Sticker Configuration
YOUTUBE_SUPERSTICKER_ENABLED = True     # Enable TTS for Super Stickers

# Membership Configuration
YOUTUBE_MEMBERSHIP_ENABLED = True       # Enable TTS for new memberships
YOUTUBE_MEMBERSHIP_MILESTONE_ENABLED = True  # Enable TTS for membership milestones

# -----------------------------------------------------------------------------
# TEXT-TO-SPEECH CONFIGURATION
# -----------------------------------------------------------------------------

# PiperTTS Voice Selection
# Browse available voices: https://rhasspy.github.io/piper-samples/
# Voice format: {language}_{COUNTRY}-{speaker}-{quality}
# Quality options: x_low, low, medium, high
# Examples:
#   en_US-lessac-medium    (American English, balanced)
#   en_US-amy-medium       (American English, female)
#   en_GB-alan-medium      (British English, male)
#   de_DE-thorsten-high    (German)
#   es_ES-carlfm-x_low     (Spanish)
TTS_VOICE = "en_GB-alan-medium"

# Speech Settings
TTS_SPEED = 1.0          # Speech rate: 0.5 (slow) to 2.0 (fast)
TTS_VOLUME = 1.0         # Volume: 0.0 (silent) to 1.0 (full)

# Message Processing
TTS_MAX_MESSAGE_LENGTH = 300    # Truncate messages longer than this
TTS_PROFANITY_FILTER = True     # Replace common profanity with asterisks

# -----------------------------------------------------------------------------
# MESSAGE TEMPLATES
# -----------------------------------------------------------------------------
# Customize how alerts are read aloud.
#
# Available placeholders by event type:
#
# Twitch Bits:
#   {username}  - Cheerer's display name
#   {amount}    - Number of bits
#   {message}   - Cheer message (if any)
#
# Twitch Subscription:
#   {username}  - Subscriber's display name
#   {tier}      - Sub tier (1, 2, or 3)
#   {months}    - Total months subscribed (resubs)
#   {message}   - Sub message (if any)
#
# Twitch Gift Sub:
#   {username}  - Gifter's display name
#   {count}     - Number of gifts
#   {recipient} - Gift recipient (single gift only)
#   {tier}      - Sub tier
#
# Twitch Channel Points:
#   {username}    - Redeemer's display name
#   {reward_name} - Name of the reward
#   {user_input}  - User's input text (if reward requires input)
#   {cost}        - Point cost of the reward
#
# YouTube Super Chat:
#   {username}  - Sender's display name
#   {amount}    - Numeric amount
#   {currency}  - Currency symbol ($, €, £, etc.)
#   {message}   - Super Chat message (if any)
#
# YouTube Membership:
#   {username}  - Member's display name
#   {level}     - Membership level name
#   {months}    - Months as member (milestones)
#
# "{message}" is a valid template, if you want to read only the message content.

TEMPLATES = {
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

# -----------------------------------------------------------------------------
# WEB SERVER CONFIGURATION
# -----------------------------------------------------------------------------
WEB_HOST = "0.0.0.0"        # Bind address (0.0.0.0 for Docker, 127.0.0.1 for local only)
WEB_PORT = 5000             # Web server port
WEB_DEBUG = False           # Flask debug mode (disable in production!)

# -----------------------------------------------------------------------------
# OBS BROWSER SOURCE SETTINGS
# -----------------------------------------------------------------------------
# These settings control the appearance of the alert overlay in OBS.

# Text Styling
OVERLAY_FONT_FAMILY = "Roboto, Arial, sans-serif"
OVERLAY_FONT_SIZE = 24              # Font size in pixels
OVERLAY_TEXT_COLOR = "#FFFFFF"      # Text color (CSS color value)
OVERLAY_TEXT_SHADOW = "2px 2px 4px rgba(0,0,0,0.8)"  # Text shadow for readability
OVERLAY_BACKGROUND_COLOR = "transparent"  # Background (use "transparent" for none)

# Animation Settings
# Options: "fade", "slide-up", "slide-down", "slide-left", "slide-right", "none"
OVERLAY_ANIMATION = "fade"
OVERLAY_ANIMATION_DURATION = 300    # Animation duration in milliseconds

# Text Display
OVERLAY_SHOW_TEXT = True            # Show text while audio plays
OVERLAY_TEXT_DURATION = 0           # Text display duration in ms (0 = match audio length)
OVERLAY_TEXT_POSITION = "bottom"    # Position: "top", "center", "bottom"

# -----------------------------------------------------------------------------
# QUEUE AND RATE LIMITING
# -----------------------------------------------------------------------------
# Message Queue Settings
QUEUE_MAX_SIZE = 50             # Max queued messages (oldest dropped when full)
QUEUE_DUPLICATE_WINDOW = 5      # Ignore duplicate messages within this many seconds

# Rate Limiting (messages processed per minute)
# Prevents rapid-fire alerts from overwhelming the stream
RATE_LIMIT_TWITCH = 30          # Max Twitch alerts per minute
RATE_LIMIT_YOUTUBE = 30         # Max YouTube alerts per minute

# Priority Settings (higher = processed first when queue has multiple messages)
PRIORITY_TWITCH_BITS = 2
PRIORITY_TWITCH_SUBS = 3
PRIORITY_TWITCH_GIFT_SUBS = 2
PRIORITY_TWITCH_CHANNEL_POINTS = 1
PRIORITY_YOUTUBE_SUPERCHAT = 2
PRIORITY_YOUTUBE_MEMBERSHIP = 3

# -----------------------------------------------------------------------------
# LOGGING
# -----------------------------------------------------------------------------
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = "INFO"

# Log to file (leave empty for stdout only)
LOG_FILE = ""  # e.g., "/app/data/freestream.log"

# Log format (Python logging format string)
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# -----------------------------------------------------------------------------
# ADVANCED SETTINGS
# -----------------------------------------------------------------------------
# Only modify these if you know what you're doing!

# Token Storage (persists OAuth tokens between restarts)
# This path is inside the Docker container
TOKEN_STORAGE_PATH = "/app/data/tokens.json"

# Audio Cache Configuration
AUDIO_CACHE_PATH = "/app/data/audio_cache"
AUDIO_CACHE_MAX_SIZE_MB = 100   # Max cache size (oldest files deleted when exceeded)
AUDIO_CACHE_TTL_HOURS = 24      # Delete cached audio older than this

# Health Check Endpoint
HEALTH_CHECK_ENABLED = True
HEALTH_CHECK_PATH = "/health"

# WebSocket Configuration
WEBSOCKET_PING_INTERVAL = 25    # Seconds between ping frames
WEBSOCKET_PING_TIMEOUT = 120    # Seconds before considering connection dead

# Retry Configuration (for API failures)
RETRY_MAX_ATTEMPTS = 3          # Max retry attempts for failed API calls
RETRY_BACKOFF_BASE = 2          # Exponential backoff base (seconds)
RETRY_BACKOFF_MAX = 60          # Maximum backoff time (seconds)
