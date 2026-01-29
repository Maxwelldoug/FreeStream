"""
FreeStream - OAuth authentication routes.
Handles OAuth flows for Twitch and YouTube.
"""

import logging
from flask import Blueprint, current_app, redirect, request, url_for, render_template_string

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


AUTH_STATUS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>FreeStream - Authentication</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
        }
        .container {
            text-align: center;
            padding: 2rem;
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            backdrop-filter: blur(10px);
        }
        h1 { margin-bottom: 0.5rem; }
        .status { font-size: 1.2rem; margin: 1rem 0; }
        .success { color: #4ade80; }
        .error { color: #f87171; }
        a {
            color: #60a5fa;
            text-decoration: none;
        }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ title }}</h1>
        <p class="status {{ status_class }}">{{ message }}</p>
        {% if redirect_url %}
        <p><a href="{{ redirect_url }}">{{ redirect_text }}</a></p>
        {% endif %}
    </div>
</body>
</html>
"""


@auth_bp.route("/twitch")
def twitch_auth():
    """Initiate Twitch OAuth flow."""
    twitch_service = current_app.twitch_service
    
    if not twitch_service:
        return render_template_string(
            AUTH_STATUS_TEMPLATE,
            title="Twitch Authentication",
            message="Twitch integration is not enabled",
            status_class="error",
            redirect_url="/",
            redirect_text="Go back"
        )
    
    redirect_uri = url_for("auth.twitch_callback", _external=True)
    auth_url = twitch_service.get_auth_url(redirect_uri)
    
    logger.info(f"Redirecting to Twitch OAuth: {auth_url}")
    return redirect(auth_url)


@auth_bp.route("/twitch/callback")
def twitch_callback():
    """Handle Twitch OAuth callback."""
    twitch_service = current_app.twitch_service
    
    if not twitch_service:
        return render_template_string(
            AUTH_STATUS_TEMPLATE,
            title="Twitch Authentication",
            message="Twitch integration is not enabled",
            status_class="error",
            redirect_url="/",
            redirect_text="Go back"
        )
    
    # Check for errors
    error = request.args.get("error")
    if error:
        error_desc = request.args.get("error_description", "Unknown error")
        logger.error(f"Twitch OAuth error: {error} - {error_desc}")
        return render_template_string(
            AUTH_STATUS_TEMPLATE,
            title="Twitch Authentication Failed",
            message=f"Error: {error_desc}",
            status_class="error",
            redirect_url="/auth/twitch",
            redirect_text="Try again"
        )
    
    # Exchange code for token
    code = request.args.get("code")
    if not code:
        return render_template_string(
            AUTH_STATUS_TEMPLATE,
            title="Twitch Authentication Failed",
            message="No authorization code received",
            status_class="error",
            redirect_url="/auth/twitch",
            redirect_text="Try again"
        )
    
    redirect_uri = url_for("auth.twitch_callback", _external=True)
    
    if twitch_service.exchange_code(code, redirect_uri):
        user_info = twitch_service.get_user_info()
        username = user_info.get("display_name", "Unknown") if user_info else "Unknown"
        
        return render_template_string(
            AUTH_STATUS_TEMPLATE,
            title="Twitch Authentication Successful",
            message=f"Authenticated as: {username}",
            status_class="success",
            redirect_url="/",
            redirect_text="Go to dashboard"
        )
    else:
        return render_template_string(
            AUTH_STATUS_TEMPLATE,
            title="Twitch Authentication Failed",
            message="Failed to exchange authorization code",
            status_class="error",
            redirect_url="/auth/twitch",
            redirect_text="Try again"
        )


@auth_bp.route("/youtube")
def youtube_auth():
    """Initiate YouTube OAuth flow."""
    youtube_service = current_app.youtube_service
    
    if not youtube_service:
        return render_template_string(
            AUTH_STATUS_TEMPLATE,
            title="YouTube Authentication",
            message="YouTube integration is not enabled",
            status_class="error",
            redirect_url="/",
            redirect_text="Go back"
        )
    
    redirect_uri = url_for("auth.youtube_callback", _external=True)
    auth_url = youtube_service.get_auth_url(redirect_uri)
    
    logger.info(f"Redirecting to YouTube OAuth: {auth_url}")
    return redirect(auth_url)


@auth_bp.route("/youtube/callback")
def youtube_callback():
    """Handle YouTube OAuth callback."""
    youtube_service = current_app.youtube_service
    
    if not youtube_service:
        return render_template_string(
            AUTH_STATUS_TEMPLATE,
            title="YouTube Authentication",
            message="YouTube integration is not enabled",
            status_class="error",
            redirect_url="/",
            redirect_text="Go back"
        )
    
    # Check for errors
    error = request.args.get("error")
    if error:
        logger.error(f"YouTube OAuth error: {error}")
        return render_template_string(
            AUTH_STATUS_TEMPLATE,
            title="YouTube Authentication Failed",
            message=f"Error: {error}",
            status_class="error",
            redirect_url="/auth/youtube",
            redirect_text="Try again"
        )
    
    # Exchange code for token
    code = request.args.get("code")
    if not code:
        return render_template_string(
            AUTH_STATUS_TEMPLATE,
            title="YouTube Authentication Failed",
            message="No authorization code received",
            status_class="error",
            redirect_url="/auth/youtube",
            redirect_text="Try again"
        )
    
    redirect_uri = url_for("auth.youtube_callback", _external=True)
    
    if youtube_service.exchange_code(code, redirect_uri):
        channel_info = youtube_service.get_channel_info()
        channel_name = channel_info.get("snippet", {}).get("title", "Unknown") if channel_info else "Unknown"
        
        return render_template_string(
            AUTH_STATUS_TEMPLATE,
            title="YouTube Authentication Successful",
            message=f"Authenticated as: {channel_name}",
            status_class="success",
            redirect_url="/",
            redirect_text="Go to dashboard"
        )
    else:
        return render_template_string(
            AUTH_STATUS_TEMPLATE,
            title="YouTube Authentication Failed",
            message="Failed to exchange authorization code",
            status_class="error",
            redirect_url="/auth/youtube",
            redirect_text="Try again"
        )


@auth_bp.route("/status")
def auth_status():
    """Get authentication status for both platforms."""
    twitch_service = current_app.twitch_service
    youtube_service = current_app.youtube_service
    
    status = {
        "twitch": {
            "enabled": twitch_service is not None,
            "authenticated": twitch_service.is_authenticated() if twitch_service else False,
        },
        "youtube": {
            "enabled": youtube_service is not None,
            "authenticated": youtube_service.is_authenticated() if youtube_service else False,
        }
    }
    
    return status
