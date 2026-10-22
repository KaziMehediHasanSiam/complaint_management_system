import os
import secrets
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEBUG_MODE = os.environ.get('FLASK_DEBUG') == '1'


class Config:
    # Set SECRET_KEY in the environment for any real deployment.
    # Without it: a fixed dev key in debug mode, otherwise a random key per start.
    SECRET_KEY = os.environ.get('SECRET_KEY') or (
        'dev-only-change-me' if DEBUG_MODE else secrets.token_hex(32)
    )

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(BASE_DIR, 'complaints.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
