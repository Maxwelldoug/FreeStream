"""
FreeStream - Services package.
Initialize and manage all application services.
"""

import logging
from typing import Optional
from flask import Flask
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

# Service instances (initialized on app startup)
_tts_service = None
_queue_service = None
_event_processor = None
_twitch_service = None
_youtube_service = None
_token_manager = None


def get_tts_service():
    """Get the TTS service instance."""
    return _tts_service


def get_queue_service():
    """Get the queue service instance."""
    return _queue_service


def get_event_processor():
    """Get the event processor instance."""
    return _event_processor


def get_twitch_service():
    """Get the Twitch service instance."""
    return _twitch_service


def get_youtube_service():
    """Get the YouTube service instance."""
    return _youtube_service


def get_token_manager():
    """Get the token manager instance."""
    return _token_manager


def init_services(app: Flask, socketio: SocketIO):
    """Initialize all application services."""
    global _tts_service, _queue_service, _event_processor, _twitch_service, _youtube_service, _token_manager
    
    config = app.freestream_config
    
    # Initialize token manager
    from app.services.tokens import TokenManager
    _token_manager = TokenManager(config.TOKEN_STORAGE_PATH)
    logger.info("Token manager initialized")
    
    # Initialize TTS service
    from app.services.tts import TTSService
    _tts_service = TTSService(config)
    logger.info("TTS service initialized")
    
    # Initialize queue service
    from app.services.queue import QueueService
    _queue_service = QueueService(config, socketio)
    logger.info("Queue service initialized")
    
    # Initialize event processor
    from app.services.event_processor import EventProcessor
    _event_processor = EventProcessor(config, _tts_service, _queue_service)
    logger.info("Event processor initialized")
    
    # Initialize Twitch service if enabled
    if config.TWITCH_ENABLED:
        from app.services.twitch import TwitchService
        _twitch_service = TwitchService(config, _event_processor, _token_manager)
        logger.info("Twitch service initialized")
    
    # Initialize YouTube service if enabled
    if config.YOUTUBE_ENABLED:
        from app.services.youtube import YouTubeService
        _youtube_service = YouTubeService(config, _event_processor, _token_manager)
        logger.info("YouTube service initialized")
    
    # Store services in app context
    app.tts_service = _tts_service
    app.queue_service = _queue_service
    app.event_processor = _event_processor
    app.twitch_service = _twitch_service
    app.youtube_service = _youtube_service
    app.token_manager = _token_manager


def start_services(app: Flask):
    """Start background services that require the app context."""
    config = app.freestream_config
    
    # Start Twitch EventSub
    if config.TWITCH_ENABLED and _twitch_service:
        try:
            _twitch_service.start()
            logger.info("Twitch service started")
        except Exception as e:
            logger.error(f"Failed to start Twitch service: {e}")
    
    # Start YouTube polling
    if config.YOUTUBE_ENABLED and _youtube_service:
        try:
            _youtube_service.start()
            logger.info("YouTube service started")
        except Exception as e:
            logger.error(f"Failed to start YouTube service: {e}")


def stop_services():
    """Stop all background services."""
    if _twitch_service:
        _twitch_service.stop()
    
    if _youtube_service:
        _youtube_service.stop()
    
    logger.info("All services stopped")
