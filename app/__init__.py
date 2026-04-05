from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask import current_app

db = SQLAlchemy()
import os

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'devsecret-key'  # replace in prod
    # Using SQLite for MVP; swap to PostgreSQL (Supabase/Neon) later without API surface changes
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mun_saas.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # Storage: choose R2 if environment configured
    app.config['STORAGE_BACKEND'] = os.getenv('STORAGE_BACKEND', 'local')

    db.init_app(app)

    with app.app_context():
        # Import models here to ensure they’re registered with SQLAlchemy before create_all
        from . import models
        db.create_all()
        # Lightweight, idempotent migration: ensure delegate_assignments has committee_id column (SQLite in MVP)
        try:
            uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            is_sqlite = 'sqlite' in uri
            if is_sqlite:
                import sqlite3
                db_path = os.path.join(os.getcwd(), 'mun_saas.db')
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("PRAGMA table_info(delegate_assignments)")
                cols = [r[1] for r in cur.fetchall()]
                if 'committee_id' not in cols:
                    cur.execute("ALTER TABLE delegate_assignments ADD COLUMN committee_id INTEGER")
                    conn.commit()
                conn.close()
        except Exception as e:
            # If migration can't run (e.g., DB in use, not SQLite, etc.), emit a warning and continue
            print(f"Migration warning: {e}")

    from . import routes
    app.register_blueprint(routes.bp)

    return app

__all__ = ['create_app']
