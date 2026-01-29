"""
FreeStream - TTS Alert Reader for OBS
Flask application factory and initialization.
"""

import logging
import os
from flask import Flask
from flask_socketio import SocketIO

# Global SocketIO instance
socketio = SocketIO()


def create_app(config_object=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    from app.config import Config
    config = Config()
    
    # Apply Flask config
    app.config['SECRET_KEY'] = os.urandom(32).hex()
    app.config['DEBUG'] = config.WEB_DEBUG
    
    # Store our config object
    app.freestream_config = config
    
    # Setup logging
    setup_logging(config)
    
    # Initialize SocketIO
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode='gevent',
        ping_interval=config.WEBSOCKET_PING_INTERVAL,
        ping_timeout=config.WEBSOCKET_PING_TIMEOUT
    )
    
    # Initialize services
    from app.services import init_services
    init_services(app, socketio)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register WebSocket handlers
    register_websocket_handlers(socketio)
    
    app.logger.info("FreeStream application initialized")
    
    return app


def setup_logging(config):
    """Configure application logging."""
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=config.LOG_FORMAT
    )
    
    # Add file handler if configured
    if config.LOG_FILE:
        file_handler = logging.FileHandler(config.LOG_FILE)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
        logging.getLogger().addHandler(file_handler)


def register_blueprints(app):
    """Register Flask blueprints."""
    from app.routes.auth import auth_bp
    from app.routes.webhooks import webhooks_bp
    from app.routes.browser_source import browser_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(webhooks_bp)
    app.register_blueprint(browser_bp)
    app.register_blueprint(api_bp)


def register_websocket_handlers(sio):
    """Register WebSocket event handlers."""
    from app.routes.websocket import register_handlers
    register_handlers(sio)
