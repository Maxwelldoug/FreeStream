# FreeStream - TTS Alert Reader for OBS

A Docker-based Python application that uses PiperTTS to read aloud stream alerts (donations, subscriptions, memberships) from Twitch and YouTube as an OBS Browser Source. More features to come.

## Overview

FreeStream connects to the Twitch and YouTube APIs to listen for monetization events and converts them to speech using PiperTTS. The application serves a web interface that can be added as a Browser Source in OBS, providing real-time text-to-speech alerts for:

### Twitch Events
- **Bits** - Cheers with configurable minimum threshold
- **Channel Points** - Custom reward redemptions
- **Subscriptions** - New subs, resubs, and gift subs

### YouTube Events
- **Memberships** - New and recurring memberships
- **Super Chats** - Paid chat messages
- **Super Stickers** - Paid sticker messages

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Compose                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │   Web Server    │    │   PiperTTS      │                     │
│  │   (Flask)       │◄──►│   Service       │                     │
│  │   Port 5000     │    │                 │                     │
│  └────────┬────────┘    └─────────────────┘                     │
│           │                                                     │
│  ┌────────▼────────┐    ┌─────────────────┐                     │
│  │  Event Handler  │◄──►│  Message Queue  │                     │
│  │                 │    │                 │                     │
│  └────────┬────────┘    └─────────────────┘                     │
│           │                                                     │
│  ┌────────▼────────────────────────────────┐                    │
│  │         Platform Connectors             │                    │
│  │  ┌─────────────┐    ┌─────────────────┐ │                    │
│  │  │   Twitch    │    │    YouTube      │ │                    │
│  │  │  EventSub   │    │   LiveChat API  │ │                    │
│  │  └─────────────┘    └─────────────────┘ │                    │
│  └─────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Host Machine                                                   │
│  ┌─────────────────┐                                            │
│  │   SETTINGS.py   │  (Mounted volume)                          │
│  └─────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Docker and Docker Compose
- Twitch Developer Application (for Twitch integration)
- Google Cloud Project with YouTube Data API v3 enabled (for YouTube integration)
- OBS Studio

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/FreeStream.git
   cd FreeStream
   ```

2. **Configure settings**
   ```bash
   cp SETTINGS.example.py SETTINGS.py
   # Edit SETTINGS.py with your API credentials and preferences
   ```

3. **Start the application**
   ```bash
   docker compose up -d
   ```

4. **Add to OBS**
   - Add a new Browser Source in OBS
   - Set URL to `http://localhost:5000`
   - Set width to and height as desired (adjustable)
   - Check "Control audio via OBS"

## Configuration

All configuration is done via the `SETTINGS.py` file, which is mounted into the Docker container. See `SETTINGS.example.py` for a complete template with all options documented.

### API Credentials

#### Twitch Setup
1. Go to [Twitch Developer Console](https://dev.twitch.tv/console)
2. Create a new application
3. Set OAuth Redirect URL to `http://localhost:5000/auth/twitch/callback`
4. Copy Client ID and Client Secret to `SETTINGS.py`

#### YouTube Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials (Web application type)
5. Set authorized redirect URI to `http://localhost:5000/auth/youtube/callback`
6. Download credentials and copy values to `SETTINGS.py`

### Voice Configuration

PiperTTS supports multiple voices. Configure your preferred voice in `SETTINGS.py`:

```python
TTS_VOICE = "en_GB-alan-medium"  # Default voice
TTS_SPEED = 1.0                     # Speech rate multiplier
```

Available voices can be found at: https://rhasspy.github.io/piper-samples/

## File Structure

```
FreeStream/
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # Application container definition
├── requirements.txt         # Python dependencies
├── SETTINGS.py              # User configuration (gitignored)
├── SETTINGS.example.py      # Configuration template
├── AGENTS.md                # AI implementation guide
├── app/
│   ├── __init__.py          # Flask application factory
│   ├── main.py              # Application entry point
│   ├── config.py            # Loads and validates SETTINGS.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py          # OAuth callback handlers
│   │   ├── webhooks.py      # Webhook receivers
│   │   └── browser_source.py # OBS browser source endpoint
│   ├── services/
│   │   ├── __init__.py
│   │   ├── tts.py           # PiperTTS integration
│   │   ├── twitch.py        # Twitch EventSub client
│   │   ├── youtube.py       # YouTube LiveChat poller
│   │   ├── queue.py         # Message queue manager
│   │   └── event_processor.py  # Event to TTS message processor
│   ├── models/
│   │   ├── __init__.py
│   │   └── events.py        # Event data classes
│   ├── templates/
│   │   └── browser_source.html  # OBS overlay template
│   └── static/
│       ├── css/
│       │   └── overlay.css  # Overlay styling
│       └── js/
│           └── overlay.js   # Audio playback & animations
├── tests/
│   ├── __init__.py
│   ├── test_twitch.py
│   ├── test_youtube.py
│   └── test_tts.py
└── data/                    # Docker volume mount point
    ├── tokens.json          # OAuth token storage
    └── audio_cache/         # Generated TTS audio files
```

## Docker Compose Services

The `docker-compose.yml` defines the following services:

### `freestream` (Main Application)
- Python Flask web server
- Handles OAuth flows
- Serves OBS browser source
- Manages event subscriptions
- Mounts `SETTINGS.py` from host

### `piper` (TTS Engine)
- PiperTTS server for text-to-speech conversion
- Exposes internal API for the main application
- Voice models stored in Docker volume

## Environment Variables

The following environment variables can be set in `docker-compose.yml` or `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Flask environment | `production` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `TTS_HOST` | PiperTTS service host | `piper` |
| `TTS_PORT` | PiperTTS service port | `5500` |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | OBS Browser Source page |
| `/health` | GET | Health check endpoint |
| `/auth/twitch` | GET | Initiate Twitch OAuth |
| `/auth/twitch/callback` | GET | Twitch OAuth callback |
| `/auth/youtube` | GET | Initiate YouTube OAuth |
| `/auth/youtube/callback` | GET | YouTube OAuth callback |
| `/webhooks/twitch` | POST | Twitch EventSub webhook receiver |
| `/api/queue` | GET | Get pending TTS messages |
| `/api/audio/<id>` | GET | Get generated audio file |
| `/api/settings` | GET | Get current settings (non-sensitive) |
| `/ws` | WebSocket | Real-time browser source connection |

## WebSocket Events

The browser source connects via WebSocket to receive real-time updates:

| Event | Direction | Description |
|-------|-----------|-------------|
| `tts_ready` | Server → Client | New TTS audio is ready to play |
| `play_complete` | Client → Server | Audio finished playing |
| `skip` | Server → Client | Skip current audio |

## Message Templates

Customize how alerts are read aloud in `SETTINGS.py`. See `SETTINGS.example.py` for all available placeholders:

```python
TEMPLATES = {
    "twitch_bits": "{username} cheered {amount} bits: {message}",
    "twitch_sub_new": "{username} just subscribed at tier {tier}!",
    "youtube_superchat": "{username} sent {currency}{amount}: {message}",
    "youtube_membership_new": "{username} became a channel member!",
    # ... see SETTINGS.example.py for all templates
}
```

## Troubleshooting

### No audio in OBS
- Ensure "Control audio via OBS" is checked in Browser Source properties
- Check that the browser source is not muted in OBS Audio Mixer
- Verify the browser source width/height are not zero

### Twitch events not working
- Verify your Twitch app has the required scopes
- Check that EventSub webhooks can reach your callback URL
- For local development, use ngrok: `ngrok http 5000`
- Ensure `TWITCH_WEBHOOK_CALLBACK_URL` is set to your public HTTPS URL
- Check logs: `docker compose logs freestream`

### YouTube events not working
- Ensure YouTube Data API v3 is enabled in Google Cloud Console
- Verify OAuth consent screen is configured
- Check that you're authenticated (visit `/auth/youtube`)
- Confirm you have an active live stream running
- Monitor API quota usage in Google Cloud Console

### TTS not generating
- Check PiperTTS container logs: `docker compose logs piper`
- Verify the selected voice model is valid
- Ensure the piper service is healthy: `docker compose ps`

### Connection issues
- Verify Docker containers are running: `docker compose ps`
- Check that port 5000 is not in use by another application
- Review logs for errors: `docker compose logs -f`

## Development

### Running locally without Docker
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

### Running tests
```bash
docker compose exec freestream pytest
```

### Viewing logs
```bash
docker compose logs -f freestream
docker compose logs -f piper
```

## License

See [LICENSE](LICENSE) file.

## Contributing

Contributions are welcome! Please read the `AGENTS.md` file for implementation details and architecture decisions.

## Acknowledgments

- [PiperTTS](https://github.com/rhasspy/piper) - Fast, local neural text-to-speech
- [TwitchAPI](https://github.com/Teekeks/pyTwitchAPI) - Twitch API wrapper for Python
- [Google API Python Client](https://github.com/googleapis/google-api-python-client) - YouTube API access
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/) - WebSocket support for Flask
