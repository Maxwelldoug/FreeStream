"""
FreeStream - PiperTTS service.
Handles text-to-speech generation using Wyoming protocol.
"""

import asyncio
import hashlib
import io
import json
import logging
import os
import socket
import struct
import time
import wave
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)


class WyomingProtocol:
    """Wyoming protocol implementation for communicating with Piper TTS."""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
    
    def synthesize(self, text: str, voice: str = None) -> bytes:
        """Synthesize speech from text using Wyoming protocol."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(30)
                sock.connect((self.host, self.port))
                
                # Send synthesize request
                request = {
                    "type": "synthesize",
                    "data": {
                        "text": text,
                    }
                }
                
                if voice:
                    request["data"]["voice"] = {"name": voice}
                
                self._send_event(sock, request)
                
                # Receive audio data
                audio_chunks = []
                
                while True:
                    event = self._receive_event(sock)
                    if event is None:
                        break
                    
                    event_type = event.get("type", "")
                    
                    if event_type == "audio-chunk":
                        # Audio payload length is in the header's payload_length field
                        payload_length = event.get("payload_length", 0)
                        if payload_length > 0:
                            audio_data = self._receive_payload(sock, payload_length)
                            if audio_data:
                                audio_chunks.append(audio_data)
                    
                    elif event_type == "audio-stop":
                        # End of audio
                        break
                    
                    elif event_type == "error":
                        error_msg = event.get("data", {}).get("text", "Unknown error")
                        raise RuntimeError(f"TTS error: {error_msg}")
                
                if not audio_chunks:
                    raise RuntimeError("No audio data received")
                
                # Combine chunks into WAV
                raw_audio = b"".join(audio_chunks)
                return self._raw_to_wav(raw_audio)
        
        except socket.timeout:
            raise RuntimeError("TTS request timed out")
        except ConnectionRefusedError:
            raise RuntimeError(f"Cannot connect to TTS service at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            raise
    
    def _send_event(self, sock: socket.socket, event: dict):
        """Send a Wyoming event."""
        event_json = json.dumps(event)
        event_bytes = event_json.encode("utf-8")
        header = f"{len(event_bytes)}\n".encode("utf-8")
        sock.sendall(header + event_bytes)
    
    def _receive_event(self, sock: socket.socket) -> Optional[dict]:
        """Receive a Wyoming event."""
        # Read length header (terminated by newline)
        length_str = b""
        while True:
            char = sock.recv(1)
            if not char:
                return None
            if char == b"\n":
                break
            length_str += char
        
        try:
            length = int(length_str.decode("utf-8"))
        except ValueError:
            return None
        
        # Read event JSON
        event_bytes = b""
        while len(event_bytes) < length:
            chunk = sock.recv(length - len(event_bytes))
            if not chunk:
                return None
            event_bytes += chunk
        
        return json.loads(event_bytes.decode("utf-8"))
    
    def _receive_payload(self, sock: socket.socket, length: int) -> bytes:
        """Receive binary payload data."""
        data = b""
        while len(data) < length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                break
            data += chunk
        return data
    
    def _raw_to_wav(self, raw_audio: bytes, sample_rate: int = 22050, 
                    channels: int = 1, sample_width: int = 2) -> bytes:
        """Convert raw PCM audio to WAV format."""
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(sample_width)
            wav.setframerate(sample_rate)
            wav.writeframes(raw_audio)
        return wav_buffer.getvalue()


class TTSService:
    """Service for generating TTS audio from text."""
    
    def __init__(self, config):
        self.config = config
        self.host = os.environ.get("TTS_HOST", "piper")
        self.port = int(os.environ.get("TTS_PORT", "10200"))
        self.cache_path = Path(config.AUDIO_CACHE_PATH)
        self.cache_path.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._protocol = WyomingProtocol(self.host, self.port)
        
        logger.info(f"TTS service configured: {self.host}:{self.port}")
    
    def synthesize(self, text: str, cache: bool = True) -> str:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to convert to speech
            cache: Whether to cache the result
            
        Returns:
            Path to the generated audio file
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Truncate if needed
        if len(text) > self.config.TTS_MAX_MESSAGE_LENGTH:
            text = text[:self.config.TTS_MAX_MESSAGE_LENGTH] + "..."
        
        # Check cache
        cache_key = self._get_cache_key(text)
        cached_path = self.cache_path / f"{cache_key}.wav"
        
        if cache and cached_path.exists():
            logger.debug(f"Cache hit for TTS: {cache_key}")
            return str(cached_path)
        
        # Generate audio
        logger.info(f"Generating TTS for: {text[:50]}...")
        
        try:
            audio_data = self._protocol.synthesize(
                text,
                voice=self.config.TTS_VOICE
            )
            
            # Save to cache
            with self._lock:
                cached_path.write_bytes(audio_data)
            
            # Cleanup old cache files
            self._cleanup_cache()
            
            logger.debug(f"TTS generated: {cached_path}")
            return str(cached_path)
        
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            raise
    
    def _get_cache_key(self, text: str) -> str:
        """Generate a cache key for the given text."""
        # Include voice and speed in hash for uniqueness
        key_data = f"{text}|{self.config.TTS_VOICE}|{self.config.TTS_SPEED}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def _cleanup_cache(self):
        """Remove old cache files if cache is too large or files are expired."""
        try:
            cache_files = list(self.cache_path.glob("*.wav"))
            
            # Remove expired files
            ttl = timedelta(hours=self.config.AUDIO_CACHE_TTL_HOURS)
            now = datetime.now()
            
            for file_path in cache_files:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if now - mtime > ttl:
                    file_path.unlink()
                    logger.debug(f"Removed expired cache file: {file_path}")
            
            # Check total cache size
            cache_files = list(self.cache_path.glob("*.wav"))
            total_size = sum(f.stat().st_size for f in cache_files)
            max_size = self.config.AUDIO_CACHE_MAX_SIZE_MB * 1024 * 1024
            
            if total_size > max_size:
                # Remove oldest files until under limit
                sorted_files = sorted(cache_files, key=lambda f: f.stat().st_mtime)
                while total_size > max_size and sorted_files:
                    oldest = sorted_files.pop(0)
                    total_size -= oldest.stat().st_size
                    oldest.unlink()
                    logger.debug(f"Removed old cache file: {oldest}")
        
        except Exception as e:
            logger.warning(f"Cache cleanup failed: {e}")
    
    def get_audio_path(self, audio_id: str) -> Optional[str]:
        """Get the path to a cached audio file by ID."""
        audio_path = self.cache_path / f"{audio_id}.wav"
        if audio_path.exists():
            return str(audio_path)
        return None
    
    def health_check(self) -> bool:
        """Check if the TTS service is available."""
        try:
            # Try to connect to the service
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((self.host, self.port))
            return True
        except Exception:
            return False
