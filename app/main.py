"""
FreeStream - Application entry point.
"""

import logging
from app import create_app, socketio

logger = logging.getLogger(__name__)


def main():
    """Main entry point for FreeStream."""
    app = create_app()
    config = app.freestream_config
    
    logger.info(f"Starting FreeStream on {config.WEB_HOST}:{config.WEB_PORT}")
    
    # Start platform services
    from app.services import start_services
    start_services(app)
    
    # Run the Flask-SocketIO server
    socketio.run(
        app,
        host=config.WEB_HOST,
        port=config.WEB_PORT,
        debug=config.WEB_DEBUG,
        use_reloader=False  # Disable reloader in production
    )


if __name__ == "__main__":
    main()
