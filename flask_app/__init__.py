# app/__init__.py
import atexit
import os
from datetime import datetime

from flask import Flask

try:
    from posthog import Posthog

    HAS_POSTHOG = True
except ImportError:
    HAS_POSTHOG = False

posthog_client = None


def create_app():
    global posthog_client

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "devsecret-key")

    app.config["STORAGE_BACKEND"] = os.getenv("STORAGE_BACKEND", "local")

    # Initialize PostHog if available
    if HAS_POSTHOG:
        posthog_token = os.getenv("POSTHOG_PROJECT_TOKEN", "")
        if posthog_token:
            posthog_client = Posthog(
                posthog_token,
                host=os.getenv("POSTHOG_HOST", "https://us.i.posthog.com"),
                enable_exception_autocapture=True,
            )
            atexit.register(posthog_client.shutdown)

    @app.template_filter("timestamp_to_date")
    def timestamp_to_date(timestamp):
        if not timestamp:
            return ""
        try:
            dt = datetime.fromtimestamp(timestamp / 1000)
            return dt.strftime("%Y-%m-%d")
        except:
            return ""

    from . import routes

    app.register_blueprint(routes.bp)

    return app


__all__ = ["create_app"]
