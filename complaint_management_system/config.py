import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'

    SQLALCHEMY_DATABASE_URI = (
        "mysql+mysqlconnector://root:a123%4045%23@localhost/complaint_db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
