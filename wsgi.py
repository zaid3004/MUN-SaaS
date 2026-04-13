# wsgi.py
import os
from app import create_app

app = create_app()

# WSGI entrypoint for production
application = app