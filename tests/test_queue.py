"""
FreeStream - Tests for queue service.
"""

import pytest
from unittest.mock import Mock, MagicMock
import time

from app.models.events import TTSMessage, TwitchBitsEvent, Platform
from app.services.queue import QueueService, RateLimiter, DuplicateDetector


class MockConfig:
    """Mock configuration for testing."""
    QUEUE_MAX_SIZE = 5
    QUEUE_DUPLICATE_WINDOW = 2
    RATE_LIMIT_TWITCH = 5
    RATE_LIMIT_YOUTUBE = 5


@pytest.fixture
def mock_socketio():
    """Create a mock SocketIO instance."""
    return MagicMock()


@pytest.fixture
def queue_service(mock_socketio):
    """Create a queue service instance."""
    return QueueService(MockConfig(), mock_socketio)


class TestQueueService:
    """Tests for QueueService."""
    
    def test_add_message(self, queue_service):
        """Test adding a message to the queue."""
        message = TTSMessage(text="Test message", priority=1)
        
        result = queue_service.add_message(message)
        
        assert result is True
    
    def test_queue_max_size(self, queue_service):
        """Test that queue respects max size."""
        # Add messages up to max
        for i in range(6):
            message = TTSMessage(text=f"Message {i}", priority=1)
            queue_service.add_message(message)
        
        status = queue_service.get_queue_status()
        # Queue should not exceed max_size - 1 (one is current)
        assert status["size"] <= MockConfig.QUEUE_MAX_SIZE
    
    def test_priority_ordering(self, queue_service):
        """Test that higher priority messages are processed first."""
        low_priority = TTSMessage(text="Low priority", priority=1, audio_path="/test.wav")
        high_priority = TTSMessage(text="High priority", priority=5, audio_path="/test.wav")
        
        # Add low priority first
        queue_service.add_message(low_priority)
        queue_service.add_message(high_priority)
        
        # Get next should return high priority
        next_msg = queue_service.get_next()
        
        assert next_msg.priority == 5
    
    def test_duplicate_rejection(self, queue_service):
        """Test that duplicate messages are rejected."""
        message1 = TTSMessage(text="Same text", priority=1)
        message2 = TTSMessage(text="Same text", priority=1)
        
        result1 = queue_service.add_message(message1)
        result2 = queue_service.add_message(message2)
        
        assert result1 is True
        assert result2 is False  # Duplicate should be rejected


class TestRateLimiter:
    """Tests for RateLimiter."""
    
    def test_allows_under_limit(self):
        """Test that requests under limit are allowed."""
        limiter = RateLimiter(rate=5, window=60)
        
        for _ in range(5):
            assert limiter.is_allowed("test") is True
    
    def test_blocks_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = RateLimiter(rate=3, window=60)
        
        for _ in range(3):
            limiter.is_allowed("test")
        
        assert limiter.is_allowed("test") is False
    
    def test_separate_keys(self):
        """Test that different keys have separate limits."""
        limiter = RateLimiter(rate=2, window=60)
        
        assert limiter.is_allowed("key1") is True
        assert limiter.is_allowed("key1") is True
        assert limiter.is_allowed("key1") is False
        
        # Different key should still be allowed
        assert limiter.is_allowed("key2") is True


class TestDuplicateDetector:
    """Tests for DuplicateDetector."""
    
    def test_detects_duplicate(self):
        """Test that duplicates are detected."""
        detector = DuplicateDetector(window=5)
        
        assert detector.is_duplicate("Hello") is False
        assert detector.is_duplicate("Hello") is True
    
    def test_allows_different_text(self):
        """Test that different text is allowed."""
        detector = DuplicateDetector(window=5)
        
        assert detector.is_duplicate("Hello") is False
        assert detector.is_duplicate("World") is False
    
    def test_window_expiry(self):
        """Test that duplicates are allowed after window expires."""
        detector = DuplicateDetector(window=1)
        
        assert detector.is_duplicate("Hello") is False
        time.sleep(1.5)  # Wait for window to expire
        assert detector.is_duplicate("Hello") is False
