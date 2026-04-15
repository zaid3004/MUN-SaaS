# flask_app/__init__.py
import os
from datetime import datetime
from flask import Flask


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "devsecret-key")
    app.config["STORAGE_BACKEND"] = os.getenv("STORAGE_BACKEND", "local")

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
