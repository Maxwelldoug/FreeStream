"""
FreeStream - Configuration for pytest.
"""

import pytest
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def app():
    """Create a test Flask application."""
    from app import create_app
    
    app = create_app()
    app.config['TESTING'] = True
    
    yield app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def config():
    """Create a test configuration."""
    from app.config import Config
    return Config()
