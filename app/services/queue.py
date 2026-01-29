"""
FreeStream - Message queue service.
Manages the TTS message queue with priority and rate limiting.
"""

import hashlib
import logging
import heapq
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, List, Optional

from flask_socketio import SocketIO

from app.models.events import TTSMessage, Platform

logger = logging.getLogger(__name__)


@dataclass(order=True)
class PriorityItem:
    """Wrapper for priority queue items."""
    priority: int
    timestamp: float = field(compare=False)
    message: TTSMessage = field(compare=False)
    
    def __init__(self, message: TTSMessage):
        # Negate priority so higher priority comes first
        self.priority = -message.priority
        self.timestamp = message.created_at.timestamp()
        self.message = message


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, rate: int, window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            rate: Maximum number of tokens per window
            window: Time window in seconds
        """
        self.rate = rate
        self.window = window
        self.tokens: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()
    
    def is_allowed(self, key: str) -> bool:
        """Check if an action is allowed under the rate limit."""
        with self._lock:
            now = time.time()
            cutoff = now - self.window
            
            # Remove old tokens
            self.tokens[key] = [t for t in self.tokens[key] if t > cutoff]
            
            # Check if under limit
            if len(self.tokens[key]) < self.rate:
                self.tokens[key].append(now)
                return True
            
            return False
    
    def get_remaining(self, key: str) -> int:
        """Get remaining tokens for a key."""
        with self._lock:
            now = time.time()
            cutoff = now - self.window
            self.tokens[key] = [t for t in self.tokens[key] if t > cutoff]
            return max(0, self.rate - len(self.tokens[key]))


class DuplicateDetector:
    """Detects duplicate messages within a time window."""
    
    def __init__(self, window: int = 5):
        """
        Initialize duplicate detector.
        
        Args:
            window: Time window in seconds for duplicate detection
        """
        self.window = window
        self.seen: Dict[str, float] = {}
        self._lock = Lock()
    
    def is_duplicate(self, text: str) -> bool:
        """Check if the text is a duplicate of a recent message."""
        with self._lock:
            now = time.time()
            text_hash = hashlib.md5(text.encode()).hexdigest()
            
            # Clean old entries
            self.seen = {k: v for k, v in self.seen.items() if now - v < self.window}
            
            if text_hash in self.seen:
                return True
            
            self.seen[text_hash] = now
            return False


class QueueService:
    """Manages the TTS message queue."""
    
    def __init__(self, config, socketio: SocketIO):
        self.config = config
        self.socketio = socketio
        
        self._queue: List[PriorityItem] = []
        self._queue_lock = Lock()
        self._current_message: Optional[TTSMessage] = None
        self._messages: Dict[str, TTSMessage] = {}
        
        # Rate limiters per platform
        self._rate_limiters = {
            Platform.TWITCH: RateLimiter(config.RATE_LIMIT_TWITCH),
            Platform.YOUTUBE: RateLimiter(config.RATE_LIMIT_YOUTUBE),
        }
        
        # Duplicate detector
        self._duplicate_detector = DuplicateDetector(config.QUEUE_DUPLICATE_WINDOW)
        
        logger.info(f"Queue service initialized (max_size={config.QUEUE_MAX_SIZE})")
    
    def add_message(self, message: TTSMessage) -> bool:
        """
        Add a message to the queue.
        
        Args:
            message: The TTS message to queue
            
        Returns:
            True if message was added, False if rejected
        """
        # Check for duplicates
        if self._duplicate_detector.is_duplicate(message.text):
            logger.debug(f"Rejected duplicate message: {message.text[:50]}")
            return False
        
        # Check rate limit
        if message.event:
            platform = message.event.platform
            if not self._rate_limiters[platform].is_allowed(platform.value):
                logger.warning(f"Rate limit exceeded for {platform.value}")
                return False
        
        with self._queue_lock:
            # Check queue size
            if len(self._queue) >= self.config.QUEUE_MAX_SIZE:
                # Remove lowest priority item
                if self._queue:
                    removed = heapq.heappop(self._queue)
                    del self._messages[removed.message.id]
                    logger.warning(f"Queue full, dropped: {removed.message.text[:30]}")
            
            # Add to queue
            heapq.heappush(self._queue, PriorityItem(message))
            self._messages[message.id] = message
            
            logger.info(f"Queued message: {message.text[:50]}... (priority={message.priority})")
        
        # Notify browser clients
        self._notify_queue_update()
        
        # If no current message, send next
        if self._current_message is None:
            self._send_next()
        
        return True
    
    def get_next(self) -> Optional[TTSMessage]:
        """Get the next message from the queue."""
        with self._queue_lock:
            if not self._queue:
                return None
            
            item = heapq.heappop(self._queue)
            message = item.message
            
            if message.id in self._messages:
                del self._messages[message.id]
            
            self._current_message = message
            return message
    
    def mark_complete(self, message_id: str):
        """Mark a message as completed and send the next one."""
        with self._queue_lock:
            if self._current_message and self._current_message.id == message_id:
                logger.debug(f"Message completed: {message_id}")
                self._current_message = None
        
        # Send next message
        self._send_next()
    
    def skip_current(self):
        """Skip the currently playing message."""
        with self._queue_lock:
            if self._current_message:
                logger.info(f"Skipping message: {self._current_message.id}")
                self._current_message = None
        
        # Notify clients to skip
        self.socketio.emit("skip", {}, namespace="/")
        
        # Send next message
        self._send_next()
    
    def clear_queue(self):
        """Clear all queued messages."""
        with self._queue_lock:
            self._queue.clear()
            self._messages.clear()
            logger.info("Queue cleared")
        
        self._notify_queue_update()
    
    def get_queue_status(self) -> dict:
        """Get current queue status."""
        with self._queue_lock:
            return {
                "size": len(self._queue),
                "max_size": self.config.QUEUE_MAX_SIZE,
                "current": self._current_message.to_dict() if self._current_message else None,
                "rate_limits": {
                    "twitch": self._rate_limiters[Platform.TWITCH].get_remaining("twitch"),
                    "youtube": self._rate_limiters[Platform.YOUTUBE].get_remaining("youtube"),
                }
            }
    
    def get_message(self, message_id: str) -> Optional[TTSMessage]:
        """Get a message by ID."""
        with self._queue_lock:
            if self._current_message and self._current_message.id == message_id:
                return self._current_message
            return self._messages.get(message_id)
    
    def _send_next(self):
        """Send the next message to browser clients."""
        message = self.get_next()
        
        if message and message.audio_path:
            # Extract audio ID from path
            audio_id = message.audio_path.split("/")[-1].replace(".wav", "")
            
            self.socketio.emit("tts_ready", {
                "id": message.id,
                "audio_id": audio_id,
                "text": message.display_text or message.text,
                "event_type": message.event.event_type.value if message.event else None,
                "platform": message.event.platform.value if message.event else None,
            }, namespace="/")
            
            logger.info(f"Sent message to browser: {message.id}")
    
    def _notify_queue_update(self):
        """Notify clients of queue status change."""
        self.socketio.emit("queue_update", self.get_queue_status(), namespace="/")
