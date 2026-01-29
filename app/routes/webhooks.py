"""
FreeStream - Webhook routes.
Handles Twitch EventSub webhooks.
"""

import logging
from flask import Blueprint, current_app, request, jsonify

logger = logging.getLogger(__name__)

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/webhooks")


@webhooks_bp.route("/twitch", methods=["POST"])
def twitch_webhook():
    """Handle Twitch EventSub webhook notifications."""
    twitch_service = current_app.twitch_service
    
    if not twitch_service:
        logger.warning("Received Twitch webhook but service is disabled")
        return "", 404
    
    # Get headers
    message_id = request.headers.get("Twitch-Eventsub-Message-Id", "")
    timestamp = request.headers.get("Twitch-Eventsub-Message-Timestamp", "")
    signature = request.headers.get("Twitch-Eventsub-Message-Signature", "")
    message_type = request.headers.get("Twitch-Eventsub-Message-Type", "")
    
    # Get raw body for signature verification
    raw_body = request.get_data()
    
    # Verify signature
    if not twitch_service.verify_signature(message_id, timestamp, raw_body, signature):
        logger.warning("Invalid webhook signature")
        return "", 403
    
    # Parse body
    try:
        body = request.get_json()
    except Exception as e:
        logger.error(f"Failed to parse webhook body: {e}")
        return "", 400
    
    # Handle the webhook
    headers_dict = dict(request.headers)
    result = twitch_service.handle_webhook(headers_dict, body)
    
    # Return challenge for verification requests
    if message_type == "webhook_callback_verification" and result:
        return result, 200, {"Content-Type": "text/plain"}
    
    return "", 204
