/**
 * FreeStream - OBS Browser Source Overlay JavaScript
 * Handles WebSocket communication and audio playback
 */

(function () {
    'use strict';

    // DOM Elements
    const alertBox = document.getElementById('alert-box');
    const alertText = document.getElementById('alert-text');
    const audioElement = document.getElementById('tts-audio');

    // State
    let socket = null;
    let currentMessageId = null;
    let hideTimeout = null;

    /**
     * Initialize the overlay
     */
    function init() {
        // Set up animation class
        alertBox.classList.add(`animation-${CONFIG.animation}`);

        // Connect to WebSocket
        connectSocket();

        // Set up audio event listeners
        setupAudioListeners();

        console.log('FreeStream overlay initialized');
    }

    /**
     * Connect to the WebSocket server
     */
    function connectSocket() {
        socket = io({
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            reconnectionAttempts: Infinity
        });

        socket.on('connect', () => {
            console.log('Connected to FreeStream server');
            socket.emit('ready');
        });

        socket.on('disconnect', () => {
            console.log('Disconnected from FreeStream server');
        });

        socket.on('connected', (data) => {
            console.log('Server acknowledged connection:', data);
        });

        socket.on('tts_ready', (data) => {
            console.log('TTS ready:', data);
            handleTTSReady(data);
        });

        socket.on('skip', () => {
            console.log('Skip requested');
            skipCurrent();
        });

        socket.on('queue_update', (data) => {
            console.log('Queue update:', data);
        });

        socket.on('error', (error) => {
            console.error('Socket error:', error);
        });
    }

    /**
     * Set up audio element event listeners
     */
    function setupAudioListeners() {
        audioElement.addEventListener('ended', () => {
            console.log('Audio playback ended');
            onPlaybackComplete();
        });

        audioElement.addEventListener('error', (e) => {
            console.error('Audio error:', e);
            if (currentMessageId) {
                socket.emit('error', {
                    id: currentMessageId,
                    error: 'Audio playback failed'
                });
            }
            onPlaybackComplete();
        });

        audioElement.addEventListener('canplaythrough', () => {
            console.log('Audio can play through');
        });
    }

    /**
     * Handle incoming TTS ready event
     */
    function handleTTSReady(data) {
        const { id, audio_id, text, event_type, platform } = data;

        currentMessageId = id;

        // Show text if enabled
        if (CONFIG.showText && text) {
            showAlert(text, event_type, platform);
        }

        // Load and play audio
        playAudio(audio_id);
    }

    /**
     * Show the alert text
     */
    function showAlert(text, eventType, platform) {
        // Clear any existing hide timeout
        if (hideTimeout) {
            clearTimeout(hideTimeout);
            hideTimeout = null;
        }

        // Set text
        alertText.textContent = text;

        // Add platform/event classes for styling
        alertBox.className = `alert-box animation-${CONFIG.animation}`;
        if (platform) {
            alertBox.classList.add(`platform-${platform}`);
        }
        if (eventType) {
            const eventClass = eventType.replace(/_/g, '-');
            alertBox.classList.add(`event-${eventClass}`);
        }

        // Show with animation
        alertBox.classList.remove('hidden');
        alertBox.classList.add('visible');
    }

    /**
     * Hide the alert text
     */
    function hideAlert() {
        alertBox.classList.remove('visible');
        alertBox.classList.add('hidden');
    }

    /**
     * Play audio from the server
     */
    function playAudio(audioId) {
        const audioUrl = `/api/audio/${audioId}`;

        audioElement.src = audioUrl;
        audioElement.load();

        // Play audio
        const playPromise = audioElement.play();

        if (playPromise !== undefined) {
            playPromise
                .then(() => {
                    console.log('Audio playing');
                })
                .catch((error) => {
                    console.error('Playback failed:', error);
                    // Might be blocked by autoplay policy
                    // Audio will still play when user interacts
                    onPlaybackComplete();
                });
        }
    }

    /**
     * Handle playback completion
     */
    function onPlaybackComplete() {
        const messageId = currentMessageId;
        currentMessageId = null;

        // Hide alert after duration (or immediately if duration is 0)
        if (CONFIG.textDuration > 0) {
            hideTimeout = setTimeout(hideAlert, CONFIG.textDuration);
        } else {
            // Hide after animation duration
            hideTimeout = setTimeout(hideAlert, CONFIG.animationDuration);
        }

        // Notify server
        if (messageId) {
            socket.emit('play_complete', { id: messageId });
        }
    }

    /**
     * Skip the currently playing audio
     */
    function skipCurrent() {
        audioElement.pause();
        audioElement.currentTime = 0;
        hideAlert();

        if (currentMessageId) {
            socket.emit('play_complete', { id: currentMessageId });
            currentMessageId = null;
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
