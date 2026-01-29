"""
FreeStream - Twitch EventSub service.
Handles Twitch API integration using EventSub for real-time events.
"""

import asyncio
import hashlib
import hmac
import logging
import threading
import time
from typing import Callable, Dict, List, Optional
from datetime import datetime

import httpx

from app.models.events import (
    TwitchBitsEvent,
    TwitchSubEvent,
    TwitchGiftSubEvent,
    TwitchChannelPointsEvent,
)

logger = logging.getLogger(__name__)

# Twitch API endpoints
TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2"
TWITCH_API_URL = "https://api.twitch.tv/helix"
TWITCH_EVENTSUB_URL = f"{TWITCH_API_URL}/eventsub/subscriptions"


class TwitchService:
    """Service for Twitch EventSub integration."""
    
    # EventSub subscription types
    SUBSCRIPTION_TYPES = [
        "channel.cheer",
        "channel.subscribe",
        "channel.subscription.message",
        "channel.subscription.gift",
        "channel.channel_points_custom_reward_redemption.add",
    ]
    
    def __init__(self, config, event_processor, token_manager):
        self.config = config
        self.event_processor = event_processor
        self.token_manager = token_manager
        
        self._running = False
        self._access_token: Optional[str] = None
        self._subscriptions: Dict[str, str] = {}  # type -> subscription_id
        
        logger.info("Twitch service initialized")
    
    def start(self):
        """Start the Twitch service."""
        if not self.config.TWITCH_CLIENT_ID or not self.config.TWITCH_CLIENT_SECRET:
            logger.warning("Twitch credentials not configured, service disabled")
            return
        
        self._running = True
        
        # Try to get/refresh access token
        if self._ensure_token():
            # Set up EventSub subscriptions
            self._setup_subscriptions()
        else:
            logger.warning("No valid Twitch token, waiting for OAuth authentication")
    
    def stop(self):
        """Stop the Twitch service."""
        self._running = False
        logger.info("Twitch service stopped")
    
    def _ensure_token(self) -> bool:
        """Ensure we have a valid access token."""
        # Check stored token
        if self.token_manager.has_valid_token("twitch"):
            self._access_token = self.token_manager.get_access_token("twitch")
            return True
        
        # Try to refresh
        refresh_token = (
            self.token_manager.get_refresh_token("twitch") or 
            self.config.TWITCH_REFRESH_TOKEN
        )
        
        if refresh_token:
            if self._refresh_token(refresh_token):
                return True
        
        return False
    
    def _refresh_token(self, refresh_token: str) -> bool:
        """Refresh the access token."""
        try:
            response = httpx.post(
                f"{TWITCH_AUTH_URL}/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.config.TWITCH_CLIENT_ID,
                    "client_secret": self.config.TWITCH_CLIENT_SECRET,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self._access_token = data["access_token"]
                new_refresh = data.get("refresh_token", refresh_token)
                expires_in = data.get("expires_in")
                
                self.token_manager.set_token(
                    "twitch",
                    self._access_token,
                    new_refresh,
                    expires_in
                )
                
                logger.info("Twitch token refreshed successfully")
                return True
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False
    
    def get_auth_url(self, redirect_uri: str) -> str:
        """Get the OAuth authorization URL."""
        from urllib.parse import urlencode, quote
        
        scopes = [
            "bits:read",
            "channel:read:subscriptions",
            "channel:read:redemptions",
        ]
        
        params = {
            "client_id": self.config.TWITCH_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
        }
        
        return f"{TWITCH_AUTH_URL}/authorize?{urlencode(params)}"
    
    def exchange_code(self, code: str, redirect_uri: str) -> bool:
        """Exchange authorization code for tokens."""
        try:
            response = httpx.post(
                f"{TWITCH_AUTH_URL}/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.config.TWITCH_CLIENT_ID,
                    "client_secret": self.config.TWITCH_CLIENT_SECRET,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self._access_token = data["access_token"]
                refresh_token = data["refresh_token"]
                expires_in = data.get("expires_in")
                
                self.token_manager.set_token(
                    "twitch",
                    self._access_token,
                    refresh_token,
                    expires_in
                )
                
                logger.info("Twitch OAuth completed successfully")
                
                # Set up subscriptions now that we have a token
                self._setup_subscriptions()
                
                return True
            else:
                logger.error(f"Code exchange failed: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Code exchange error: {e}")
            return False
    
    def _setup_subscriptions(self):
        """Set up EventSub subscriptions."""
        if not self._access_token:
            logger.warning("No access token, cannot set up subscriptions")
            return
        
        if not self.config.TWITCH_WEBHOOK_CALLBACK_URL:
            logger.warning("No webhook callback URL configured")
            return
        
        if not self.config.TWITCH_BROADCASTER_ID:
            logger.warning("No broadcaster ID configured")
            return
        
        # First, clean up any existing subscriptions
        self._cleanup_subscriptions()
        
        # Create new subscriptions
        for sub_type in self.SUBSCRIPTION_TYPES:
            self._create_subscription(sub_type)
    
    def _cleanup_subscriptions(self):
        """Remove existing EventSub subscriptions."""
        try:
            headers = self._get_headers()
            response = httpx.get(TWITCH_EVENTSUB_URL, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                for sub in data.get("data", []):
                    # Delete subscriptions for our callback URL
                    if sub.get("transport", {}).get("callback") == self.config.TWITCH_WEBHOOK_CALLBACK_URL:
                        sub_id = sub["id"]
                        httpx.delete(
                            f"{TWITCH_EVENTSUB_URL}?id={sub_id}",
                            headers=headers
                        )
                        logger.debug(f"Deleted subscription: {sub_id}")
        
        except Exception as e:
            logger.error(f"Failed to cleanup subscriptions: {e}")
    
    def _create_subscription(self, sub_type: str) -> bool:
        """Create an EventSub subscription."""
        try:
            headers = self._get_headers()
            
            # Build condition based on subscription type
            condition = {"broadcaster_user_id": self.config.TWITCH_BROADCASTER_ID}
            
            payload = {
                "type": sub_type,
                "version": "1",
                "condition": condition,
                "transport": {
                    "method": "webhook",
                    "callback": self.config.TWITCH_WEBHOOK_CALLBACK_URL,
                    "secret": self.config.TWITCH_WEBHOOK_SECRET,
                }
            }
            
            response = httpx.post(
                TWITCH_EVENTSUB_URL,
                json=payload,
                headers=headers
            )
            
            if response.status_code in (200, 202):
                data = response.json()
                sub_id = data["data"][0]["id"]
                self._subscriptions[sub_type] = sub_id
                logger.info(f"Created subscription: {sub_type} ({sub_id})")
                return True
            else:
                logger.error(f"Failed to create subscription {sub_type}: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Subscription creation error: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Twitch API requests."""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Client-Id": self.config.TWITCH_CLIENT_ID,
            "Content-Type": "application/json",
        }
    
    def verify_signature(self, message_id: str, timestamp: str, body: bytes, signature: str) -> bool:
        """Verify EventSub webhook signature."""
        if not self.config.TWITCH_WEBHOOK_SECRET:
            logger.warning("No webhook secret configured, skipping verification")
            return True
        
        message = message_id.encode() + timestamp.encode() + body
        expected_signature = "sha256=" + hmac.new(
            self.config.TWITCH_WEBHOOK_SECRET.encode(),
            message,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def handle_webhook(self, headers: Dict[str, str], body: dict) -> Optional[str]:
        """
        Handle an EventSub webhook notification.
        
        Returns:
            Challenge string for verification requests, None otherwise
        """
        message_type = headers.get("Twitch-Eventsub-Message-Type", "")
        
        if message_type == "webhook_callback_verification":
            challenge = body.get("challenge", "")
            logger.info("EventSub webhook verified")
            return challenge
        
        elif message_type == "notification":
            self._process_notification(body)
            return None
        
        elif message_type == "revocation":
            sub_type = body.get("subscription", {}).get("type")
            logger.warning(f"Subscription revoked: {sub_type}")
            return None
        
        return None
    
    def _process_notification(self, body: dict):
        """Process an EventSub notification."""
        sub_type = body.get("subscription", {}).get("type", "")
        event_data = body.get("event", {})
        
        logger.info(f"Received Twitch event: {sub_type}")
        logger.debug(f"Event data: {event_data}")
        
        event = None
        
        if sub_type == "channel.cheer":
            event = TwitchBitsEvent.from_eventsub(event_data)
        
        elif sub_type == "channel.subscribe":
            event = TwitchSubEvent.from_eventsub_subscribe(event_data)
        
        elif sub_type == "channel.subscription.message":
            event = TwitchSubEvent.from_eventsub_message(event_data)
        
        elif sub_type == "channel.subscription.gift":
            event = TwitchGiftSubEvent.from_eventsub(event_data)
        
        elif sub_type == "channel.channel_points_custom_reward_redemption.add":
            event = TwitchChannelPointsEvent.from_eventsub(event_data)
        
        if event:
            self.event_processor.process_event(event)
        else:
            logger.warning(f"Unknown event type: {sub_type}")
    
    def get_user_info(self) -> Optional[dict]:
        """Get information about the authenticated user."""
        if not self._access_token:
            return None
        
        try:
            response = httpx.get(
                f"{TWITCH_API_URL}/users",
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                users = data.get("data", [])
                if users:
                    return users[0]
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
        
        return None
    
    def is_authenticated(self) -> bool:
        """Check if the service is authenticated."""
        return self._access_token is not None and self._ensure_token()
