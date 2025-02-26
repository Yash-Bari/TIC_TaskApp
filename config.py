import os
from datetime import timedelta

class Config:
    # Flask Configuration
    SECRET_KEY = 'dev-secret-key-123'  # Change this in production
    SERVER_NAME = 'ana.ticlub.in'
    
    # SQLite Database Configuration
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tic_taskapp.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Google OAuth Configuration
    GOOGLE_OAUTH_CLIENT_ID = '835505640934-h0jv7uj2dbgt1p1eijsvbm7dkiag80g9.apps.googleusercontent.com'
    GOOGLE_OAUTH_CLIENT_SECRET = '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'
    
    # OAuth Settings
    OAUTHLIB_INSECURE_TRANSPORT = True  # Only for development
    OAUTHLIB_RELAX_TOKEN_SCOPE = True
    
    # Session Settings
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Mail Configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'omlate3@gmail.com'
    MAIL_PASSWORD = 'oizhtejaznoltgeq'
    MAIL_DEFAULT_SENDER = 'omlate3@gmail.com'
    
    # Domain Configuration
    ALLOWED_DOMAINS = ['srttc.ac.in']
    COORDINATOR_EMAIL = 'saiprasad.221290@srttc.ac.in'
    ADMIN_EMAIL = 'yash.211128@srttc.ac.in'
