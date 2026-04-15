# app.py - Vercel entry point
from flask_app import create_app

app = create_app()

import os

port = int(os.getenv("PORT", 5000))
