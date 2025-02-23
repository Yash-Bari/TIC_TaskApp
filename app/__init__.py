from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_dance.contrib.google import make_google_blueprint, google
from config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

# Configure login manager
@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # Configure Google OAuth
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    
    google_bp = make_google_blueprint(
        client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
        client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
        scope=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile'],
        redirect_url='/login/google/authorized',
        authorized_url='/login/google/authorized',
        offline=True,
        reprompt_consent=True
    )
    
    # Register blueprints
    from app.auth import auth_bp
    from app.main import main_bp
    from app.admin import admin_bp
    from app.coordinator import coordinator_bp
    from app.student import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(google_bp, url_prefix='/login')
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(coordinator_bp, url_prefix='/coordinator')
    app.register_blueprint(student_bp, url_prefix='/student')

    # Create database tables
    with app.app_context():
        db.create_all()
        
    @app.before_request
    def before_request():
        session.permanent = True

    return app
