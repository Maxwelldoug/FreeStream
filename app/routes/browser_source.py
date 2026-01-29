"""
FreeStream - Browser source routes.
Serves the OBS browser source overlay.
"""

import logging
from flask import Blueprint, current_app, render_template, send_from_directory

logger = logging.getLogger(__name__)

browser_bp = Blueprint("browser", __name__)


@browser_bp.route("/")
def index():
    """Serve the main browser source page."""
    config = current_app.freestream_config
    
    return render_template(
        "browser_source.html",
        config=config,
        css_vars=config.get_overlay_css_vars(),
    )


@browser_bp.route("/health")
def health_check():
    """Health check endpoint."""
    config = current_app.freestream_config
    
    if not config.HEALTH_CHECK_ENABLED:
        return "", 404
    
    # Check TTS service
    tts_service = current_app.tts_service
    tts_healthy = tts_service.health_check() if tts_service else False
    
    # Check Twitch service
    twitch_service = current_app.twitch_service
    twitch_auth = twitch_service.is_authenticated() if twitch_service else None
    
    # Check YouTube service
    youtube_service = current_app.youtube_service
    youtube_auth = youtube_service.is_authenticated() if youtube_service else None
    
    status = {
        "status": "healthy" if tts_healthy else "degraded",
        "services": {
            "tts": "healthy" if tts_healthy else "unhealthy",
            "twitch": {
                "enabled": twitch_service is not None,
                "authenticated": twitch_auth,
            } if twitch_service else {"enabled": False},
            "youtube": {
                "enabled": youtube_service is not None,
                "authenticated": youtube_auth,
            } if youtube_service else {"enabled": False},
        }
    }
    
    return status, 200 if tts_healthy else 503
