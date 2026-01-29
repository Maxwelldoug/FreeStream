"""
FreeStream - Token management service.
Handles OAuth token storage and refresh.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from threading import Lock

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages OAuth tokens for Twitch and YouTube."""
    
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self._tokens: Dict[str, dict] = {}
        self._lock = Lock()
        self._load_tokens()
    
    def _load_tokens(self):
        """Load tokens from storage file."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    self._tokens = json.load(f)
                logger.info("Loaded tokens from storage")
        except Exception as e:
            logger.warning(f"Failed to load tokens: {e}")
            self._tokens = {}
    
    def _save_tokens(self):
        """Save tokens to storage file."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(self._tokens, f, indent=2)
            logger.debug("Saved tokens to storage")
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
    
    def get_token(self, platform: str) -> Optional[dict]:
        """Get tokens for a platform."""
        with self._lock:
            return self._tokens.get(platform)
    
    def set_token(self, platform: str, access_token: str, refresh_token: str, 
                  expires_in: Optional[int] = None):
        """Store tokens for a platform."""
        with self._lock:
            expires_at = None
            if expires_in:
                expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
            
            self._tokens[platform] = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "updated_at": datetime.utcnow().isoformat()
            }
            self._save_tokens()
            logger.info(f"Stored tokens for {platform}")
    
    def get_access_token(self, platform: str) -> Optional[str]:
        """Get the access token for a platform."""
        token_data = self.get_token(platform)
        if token_data:
            return token_data.get("access_token")
        return None
    
    def get_refresh_token(self, platform: str) -> Optional[str]:
        """Get the refresh token for a platform."""
        token_data = self.get_token(platform)
        if token_data:
            return token_data.get("refresh_token")
        return None
    
    def is_expired(self, platform: str) -> bool:
        """Check if the access token is expired."""
        token_data = self.get_token(platform)
        if not token_data:
            return True
        
        expires_at = token_data.get("expires_at")
        if not expires_at:
            return False  # No expiry info, assume valid
        
        try:
            expiry = datetime.fromisoformat(expires_at)
            # Consider expired 5 minutes before actual expiry
            return datetime.utcnow() > (expiry - timedelta(minutes=5))
        except ValueError:
            return True
    
    def delete_token(self, platform: str):
        """Delete tokens for a platform."""
        with self._lock:
            if platform in self._tokens:
                del self._tokens[platform]
                self._save_tokens()
                logger.info(f"Deleted tokens for {platform}")
    
    def has_valid_token(self, platform: str) -> bool:
        """Check if we have a valid (non-expired) token."""
        token_data = self.get_token(platform)
        if not token_data or not token_data.get("access_token"):
            return False
        return not self.is_expired(platform)
