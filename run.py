# run.py
from flask_app import create_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = create_app()

limiter = Limiter(
    key_func=get_remote_address, app=app, default_limits=["200 per day", "50 per hour"]
)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
