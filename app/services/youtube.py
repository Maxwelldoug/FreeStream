"""
FreeStream - YouTube LiveChat service.
Handles YouTube API integration for live chat monetization events.
"""

import logging
import threading
import time
from typing import Dict, List, Optional
from datetime import datetime

import httpx
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.models.events import (
    YouTubeSuperChatEvent,
    YouTubeSuperStickerEvent,
    YouTubeMembershipEvent,
)

logger = logging.getLogger(__name__)

# YouTube API scopes
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

# OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class YouTubeService:
    """Service for YouTube LiveChat integration."""
    
    def __init__(self, config, event_processor, token_manager):
        self.config = config
        self.event_processor = event_processor
        self.token_manager = token_manager
        
        self._running = False
        self._poll_thread: Optional[threading.Thread] = None
        self._youtube = None
        self._live_chat_id: Optional[str] = None
        self._next_page_token: Optional[str] = None
        self._credentials: Optional[Credentials] = None
        
        logger.info("YouTube service initialized")
    
    def start(self):
        """Start the YouTube polling service."""
        if not self.config.YOUTUBE_CLIENT_ID or not self.config.YOUTUBE_CLIENT_SECRET:
            logger.warning("YouTube credentials not configured, service disabled")
            return
        
        self._running = True
        
        # Try to get/refresh access token
        if self._ensure_credentials():
            # Start polling thread
            self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._poll_thread.start()
            logger.info("YouTube polling started")
        else:
            logger.warning("No valid YouTube credentials, waiting for OAuth authentication")
    
    def stop(self):
        """Stop the YouTube polling service."""
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=5)
        logger.info("YouTube service stopped")
    
    def _ensure_credentials(self) -> bool:
        """Ensure we have valid credentials."""
        token_data = self.token_manager.get_token("youtube")
        
        if not token_data:
            # Try using refresh token from config
            if self.config.YOUTUBE_REFRESH_TOKEN:
                return self._refresh_token(self.config.YOUTUBE_REFRESH_TOKEN)
            return False
        
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        
        if not access_token:
            if refresh_token:
                return self._refresh_token(refresh_token)
            return False
        
        # Check if expired
        if self.token_manager.is_expired("youtube"):
            if refresh_token:
                return self._refresh_token(refresh_token)
            return False
        
        # Create credentials object
        self._credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=GOOGLE_TOKEN_URL,
            client_id=self.config.YOUTUBE_CLIENT_ID,
            client_secret=self.config.YOUTUBE_CLIENT_SECRET,
        )
        
        self._youtube = build("youtube", "v3", credentials=self._credentials)
        return True
    
    def _refresh_token(self, refresh_token: str) -> bool:
        """Refresh the access token."""
        try:
            response = httpx.post(
                GOOGLE_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.config.YOUTUBE_CLIENT_ID,
                    "client_secret": self.config.YOUTUBE_CLIENT_SECRET,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                access_token = data["access_token"]
                new_refresh = data.get("refresh_token", refresh_token)
                expires_in = data.get("expires_in")
                
                self.token_manager.set_token(
                    "youtube",
                    access_token,
                    new_refresh,
                    expires_in
                )
                
                # Create credentials object
                self._credentials = Credentials(
                    token=access_token,
                    refresh_token=new_refresh,
                    token_uri=GOOGLE_TOKEN_URL,
                    client_id=self.config.YOUTUBE_CLIENT_ID,
                    client_secret=self.config.YOUTUBE_CLIENT_SECRET,
                )
                
                self._youtube = build("youtube", "v3", credentials=self._credentials)
                
                logger.info("YouTube token refreshed successfully")
                return True
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False
    
    def get_auth_url(self, redirect_uri: str) -> str:
        """Get the OAuth authorization URL."""
        scopes = "+".join(YOUTUBE_SCOPES)
        
        return (
            f"{GOOGLE_AUTH_URL}"
            f"?client_id={self.config.YOUTUBE_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={scopes}"
            f"&access_type=offline"
            f"&prompt=consent"
        )
    
    def exchange_code(self, code: str, redirect_uri: str) -> bool:
        """Exchange authorization code for tokens."""
        try:
            response = httpx.post(
                GOOGLE_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.config.YOUTUBE_CLIENT_ID,
                    "client_secret": self.config.YOUTUBE_CLIENT_SECRET,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                access_token = data["access_token"]
                refresh_token = data.get("refresh_token", "")
                expires_in = data.get("expires_in")
                
                self.token_manager.set_token(
                    "youtube",
                    access_token,
                    refresh_token,
                    expires_in
                )
                
                # Create credentials
                self._credentials = Credentials(
                    token=access_token,
                    refresh_token=refresh_token,
                    token_uri=GOOGLE_TOKEN_URL,
                    client_id=self.config.YOUTUBE_CLIENT_ID,
                    client_secret=self.config.YOUTUBE_CLIENT_SECRET,
                )
                
                self._youtube = build("youtube", "v3", credentials=self._credentials)
                
                logger.info("YouTube OAuth completed successfully")
                
                # Start polling if not already running
                if self._running and not self._poll_thread:
                    self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
                    self._poll_thread.start()
                
                return True
            else:
                logger.error(f"Code exchange failed: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Code exchange error: {e}")
            return False
    
    def _poll_loop(self):
        """Main polling loop for live chat messages."""
        while self._running:
            try:
                # Get active live chat ID if we don't have one
                if not self._live_chat_id:
                    self._live_chat_id = self._get_live_chat_id()
                    if not self._live_chat_id:
                        logger.debug("No active live stream found")
                        time.sleep(30)  # Wait before retrying
                        continue
                
                # Poll for messages
                self._poll_messages()
                
            except HttpError as e:
                if e.resp.status == 403:
                    logger.error("YouTube API quota exceeded or forbidden")
                    time.sleep(60)
                elif e.resp.status == 404:
                    logger.info("Live chat ended, clearing chat ID")
                    self._live_chat_id = None
                    self._next_page_token = None
                else:
                    logger.error(f"YouTube API error: {e}")
                    time.sleep(10)
            
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(10)
            
            # Wait for next poll
            time.sleep(self.config.YOUTUBE_POLL_INTERVAL)
    
    def _get_live_chat_id(self) -> Optional[str]:
        """Get the live chat ID for the active broadcast."""
        if not self._youtube:
            return None
        
        try:
            # First try to get from configured channel
            if self.config.YOUTUBE_CHANNEL_ID:
                response = self._youtube.liveBroadcasts().list(
                    part="snippet",
                    broadcastStatus="active",
                    broadcastType="all"
                ).execute()
            else:
                # Get broadcasts for authenticated user
                response = self._youtube.liveBroadcasts().list(
                    part="snippet",
                    mine=True,
                    broadcastStatus="active"
                ).execute()
            
            broadcasts = response.get("items", [])
            
            if broadcasts:
                live_chat_id = broadcasts[0]["snippet"].get("liveChatId")
                logger.info(f"Found live chat: {live_chat_id}")
                return live_chat_id
            
            return None
        
        except HttpError as e:
            logger.error(f"Failed to get live chat ID: {e}")
            return None
    
    def _poll_messages(self):
        """Poll for new live chat messages."""
        if not self._youtube or not self._live_chat_id:
            return
        
        try:
            params = {
                "liveChatId": self._live_chat_id,
                "part": "snippet,authorDetails",
            }
            
            if self._next_page_token:
                params["pageToken"] = self._next_page_token
            
            response = self._youtube.liveChatMessages().list(**params).execute()
            
            # Update next page token
            self._next_page_token = response.get("nextPageToken")
            
            # Process messages
            for item in response.get("items", []):
                self._process_message(item)
        
        except HttpError as e:
            raise
    
    def _process_message(self, item: dict):
        """Process a live chat message for monetization events."""
        snippet = item.get("snippet", {})
        message_type = snippet.get("type", "")
        author = item.get("authorDetails", {})
        
        # Update username from author details
        username = author.get("displayName", "Someone")
        
        event = None
        
        if message_type == "superChatEvent":
            event = YouTubeSuperChatEvent.from_livechat(item)
            event.username = username
            logger.info(f"Super Chat from {username}")
        
        elif message_type == "superStickerEvent":
            event = YouTubeSuperStickerEvent.from_livechat(item)
            event.username = username
            logger.info(f"Super Sticker from {username}")
        
        elif message_type == "newSponsorEvent":
            event = YouTubeMembershipEvent.from_livechat(item, is_milestone=False)
            event.username = username
            logger.info(f"New member: {username}")
        
        elif message_type == "memberMilestoneChatEvent":
            event = YouTubeMembershipEvent.from_livechat(item, is_milestone=True)
            event.username = username
            logger.info(f"Member milestone: {username}")
        
        if event:
            self.event_processor.process_event(event)
    
    def get_channel_info(self) -> Optional[dict]:
        """Get information about the authenticated channel."""
        if not self._youtube:
            return None
        
        try:
            response = self._youtube.channels().list(
                part="snippet,statistics",
                mine=True
            ).execute()
            
            channels = response.get("items", [])
            if channels:
                return channels[0]
        
        except Exception as e:
            logger.error(f"Failed to get channel info: {e}")
        
        return None
    
    def is_authenticated(self) -> bool:
        """Check if the service is authenticated."""
        return self._youtube is not None and self._ensure_credentials()
