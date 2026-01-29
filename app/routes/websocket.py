"""
FreeStream - WebSocket event handlers.
Handles real-time communication with browser clients.
"""

import logging
from flask_socketio import SocketIO, emit

logger = logging.getLogger(__name__)


def register_handlers(socketio: SocketIO):
    """Register WebSocket event handlers."""
    
    @socketio.on("connect")
    def handle_connect():
        """Handle client connection."""
        logger.info("Browser client connected")
        emit("connected", {"status": "ok"})
    
    @socketio.on("disconnect")
    def handle_disconnect():
        """Handle client disconnection."""
        logger.info("Browser client disconnected")
    
    @socketio.on("play_complete")
    def handle_play_complete(data):
        """Handle audio playback completion."""
        from flask import current_app
        
        message_id = data.get("id")
        if message_id:
            queue_service = current_app.queue_service
            queue_service.mark_complete(message_id)
            logger.debug(f"Playback complete: {message_id}")
    
    @socketio.on("ready")
    def handle_ready():
        """Handle client ready signal."""
        logger.info("Browser client ready for audio")
    
    @socketio.on("error")
    def handle_error(data):
        """Handle client-side errors."""
        error = data.get("error", "Unknown error")
        message_id = data.get("id")
        logger.error(f"Client error for message {message_id}: {error}")
        
        # Mark as complete so we don't get stuck
        if message_id:
            from flask import current_app
            queue_service = current_app.queue_service
            queue_service.mark_complete(message_id)
