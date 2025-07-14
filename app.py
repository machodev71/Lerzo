import os
import logging
from flask import Flask, session, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging based on environment
env = os.environ.get('FLASK_ENV', 'production')
if env == 'production':
    logging.basicConfig(level=logging.INFO)
else:
    logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Validate required environment variables
    secret_key = os.environ.get("SESSION_SECRET")
    database_url = os.environ.get("DATABASE_URL")
    
    if not secret_key:
        raise ValueError("SESSION_SECRET environment variable is required")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    app.secret_key = secret_key
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Environment-specific configuration
    if env == 'production':
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
    else:
        app.config['DEBUG'] = True
    
    # Database configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Security configuration
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # CSRF token valid for 1 hour
    app.config['SESSION_COOKIE_SECURE'] = env == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth_login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = "strong"
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import Centre
        return Centre.query.get(int(user_id))
    
    # Register middleware
    from middleware import subscription_middleware
    app.before_request(subscription_middleware)
    
    # Register routes
    from routes import register_routes
    register_routes(app)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(413)
    def file_too_large(error):
        from flask import flash, redirect, url_for
        flash('File too large. Maximum size is 16MB.', 'error')
        return redirect(url_for('dashboard'))
    
    with app.app_context():
        # Import models to ensure tables are created
        import models
        db.create_all()
        
        # Create upload directory
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    return app

# Create the app instance
app = create_app()
