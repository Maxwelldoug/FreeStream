"""
FreeStream - Routes package.
"""

from app.routes.auth import auth_bp
from app.routes.webhooks import webhooks_bp
from app.routes.browser_source import browser_bp
from app.routes.api import api_bp

__all__ = ["auth_bp", "webhooks_bp", "browser_bp", "api_bp"]
