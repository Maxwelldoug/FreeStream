"""
FreeStream - Tests for TTS service.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from app.services.tts import TTSService, WyomingProtocol


class MockConfig:
    """Mock configuration for testing."""
    AUDIO_CACHE_PATH = tempfile.mkdtemp()
    AUDIO_CACHE_MAX_SIZE_MB = 10
    AUDIO_CACHE_TTL_HOURS = 1
    TTS_VOICE = "en_GB-alan-medium"
    TTS_SPEED = 1.0
    TTS_MAX_MESSAGE_LENGTH = 300


@pytest.fixture
def tts_service():
    """Create a TTS service instance with mocked protocol."""
    with patch.object(WyomingProtocol, 'synthesize') as mock_synth:
        # Create a simple WAV file content
        mock_synth.return_value = b'RIFF' + b'\x00' * 100
        
        service = TTSService(MockConfig())
        yield service


class TestTTSService:
    """Tests for TTSService."""
    
    def test_synthesize_creates_file(self, tts_service):
        """Test that synthesize creates an audio file."""
        with patch.object(tts_service._protocol, 'synthesize') as mock_synth:
            mock_synth.return_value = b'RIFF' + b'\x00' * 100
            
            result = tts_service.synthesize("Hello world")
            
            assert result is not None
            assert result.endswith('.wav')
    
    def test_truncates_long_messages(self, tts_service):
        """Test that long messages are truncated."""
        with patch.object(tts_service._protocol, 'synthesize') as mock_synth:
            mock_synth.return_value = b'RIFF' + b'\x00' * 100
            
            long_text = "A" * 500
            tts_service.synthesize(long_text)
            
            # Check the text passed to synthesize was truncated
            call_args = mock_synth.call_args
            text_arg = call_args[0][0]
            assert len(text_arg) <= MockConfig.TTS_MAX_MESSAGE_LENGTH + 3  # +3 for "..."
    
    def test_empty_text_raises(self, tts_service):
        """Test that empty text raises an error."""
        with pytest.raises(ValueError):
            tts_service.synthesize("")
        
        with pytest.raises(ValueError):
            tts_service.synthesize("   ")
    
    def test_cache_key_includes_voice(self, tts_service):
        """Test that cache key includes voice setting."""
        key1 = tts_service._get_cache_key("Hello")
        
        # Change voice
        tts_service.config.TTS_VOICE = "different-voice"
        key2 = tts_service._get_cache_key("Hello")
        
        # Keys should be different
        assert key1 != key2


class TestWyomingProtocol:
    """Tests for Wyoming protocol implementation."""
    
    def test_raw_to_wav(self):
        """Test converting raw audio to WAV format."""
        protocol = WyomingProtocol("localhost", 10200)
        
        raw_audio = b'\x00' * 1000  # 1000 bytes of silence
        wav_data = protocol._raw_to_wav(raw_audio)
        
        # WAV files start with RIFF header
        assert wav_data[:4] == b'RIFF'
        # Contains WAVE format
        assert b'WAVE' in wav_data
