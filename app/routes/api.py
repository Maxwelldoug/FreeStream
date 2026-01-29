"""
FreeStream - API routes.
REST API endpoints for controlling the application.
"""

import logging
from flask import Blueprint, current_app, request, jsonify, send_file

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/settings")
def get_settings():
    """Get current settings (non-sensitive)."""
    config = current_app.freestream_config
    return jsonify(config.to_public_dict())


@api_bp.route("/queue")
def get_queue():
    """Get current queue status."""
    queue_service = current_app.queue_service
    return jsonify(queue_service.get_queue_status())


@api_bp.route("/queue/clear", methods=["POST"])
def clear_queue():
    """Clear the message queue."""
    queue_service = current_app.queue_service
    queue_service.clear_queue()
    return jsonify({"status": "ok"})


@api_bp.route("/queue/skip", methods=["POST"])
def skip_current():
    """Skip the currently playing message."""
    queue_service = current_app.queue_service
    queue_service.skip_current()
    return jsonify({"status": "ok"})


@api_bp.route("/audio/<audio_id>")
def get_audio(audio_id: str):
    """Get a generated audio file."""
    tts_service = current_app.tts_service
    
    # Sanitize audio_id to prevent path traversal
    audio_id = audio_id.replace("/", "").replace("\\", "").replace("..", "")
    
    audio_path = tts_service.get_audio_path(audio_id)
    
    if audio_path:
        return send_file(
            audio_path,
            mimetype="audio/wav",
            as_attachment=False
        )
    
    return "", 404


@api_bp.route("/test", methods=["POST"])
def inject_test_event():
    """Inject a test event for development/testing."""
    config = current_app.freestream_config
    
    # Only allow in debug mode
    if not config.WEB_DEBUG:
        return jsonify({"error": "Test events only available in debug mode"}), 403
    
    event_processor = current_app.event_processor
    
    data = request.get_json() or {}
    event_type = data.get("type", "twitch_bits")
    
    # Remove type from kwargs
    kwargs = {k: v for k, v in data.items() if k != "type"}
    
    success = event_processor.inject_test_event(event_type, **kwargs)
    
    return jsonify({
        "status": "ok" if success else "failed",
        "event_type": event_type
    })


@api_bp.route("/tts/test", methods=["POST"])
def test_tts():
    """Test TTS generation with custom text."""
    config = current_app.freestream_config
    
    # Only allow in debug mode
    if not config.WEB_DEBUG:
        return jsonify({"error": "TTS test only available in debug mode"}), 403
    
    tts_service = current_app.tts_service
    queue_service = current_app.queue_service
    
    data = request.get_json() or {}
    text = data.get("text", "This is a test message from FreeStream.")
    
    try:
        from app.models.events import TTSMessage
        
        audio_path = tts_service.synthesize(text)
        
        message = TTSMessage(
            text=text,
            display_text=text,
            priority=1,
            audio_path=audio_path,
        )
        
        queue_service.add_message(message)
        
        return jsonify({
            "status": "ok",
            "message_id": message.id
        })
    
    except Exception as e:
        logger.error(f"TTS test failed: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
