import os
import logging
from datetime import timedelta
from flask import Flask, session, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
load_dotenv()  # loads .env variables


# Load environment variables
load_dotenv()

class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()

def configure_logging(app):
    """Configure application logging"""
    if app.config['ENV'] == 'production':
        handler = RotatingFileHandler(
            'app.log',
            maxBytes=1024 * 1024 * 10,  # 10MB
            backupCount=5
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
    else:
        logging.basicConfig(level=logging.DEBUG)
    app.logger.setLevel(logging.DEBUG)

def create_app():
    """Application factory"""
    app = Flask(__name__)
    
    # Environment configuration
    env = os.environ.get('FLASK_ENV', 'production')
    app.config['ENV'] = env
    
    # Validate required environment variables
    required_vars = ['SESSION_SECRET', 'DATABASE_URL']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Core Configuration
    app.config.update({
        'SECRET_KEY': os.environ['SESSION_SECRET'],
        'SQLALCHEMY_DATABASE_URI': os.environ['DATABASE_URL'],
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        
        # Security Headers
        'SESSION_COOKIE_SECURE': env == 'production',
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
        'PERMANENT_SESSION_LIFETIME': timedelta(minutes=30),
        
        # CSRF Protection - DISABLED
        'WTF_CSRF_ENABLED': False,
        'WTF_CSRF_CHECK_DEFAULT': False,
        'WTF_CSRF_TIME_LIMIT': 3600,
        'WTF_CSRF_SSL_STRICT': False,
        
        # File Uploads
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,
        'UPLOAD_FOLDER': os.path.join(app.instance_path, 'uploads'),
        
        # Database Pool
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'pool_size': 10,
            'max_overflow': 20,
            'pool_recycle': 300,
            'pool_pre_ping': True,
            'pool_timeout': 30
        }
    })
    
    # Proxy Configuration
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1,
        x_prefix=1
    )
    
    # Initialize extensions (CSRF disabled)
    db.init_app(app)
    login_manager.init_app(app)
    # csrf.init_app(app)  # Commented out to disable CSRF
    
    # Login Manager Configuration
    login_manager.login_view = 'auth_login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = "strong"
    
    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        try:
            from models import Centre
            return Centre.query.get(int(user_id))
        except Exception as e:
            app.logger.error(f"Error loading user {user_id}: {e}")
            return None
    
    # Session initialization (CSRF disabled)
    @app.before_request
    def before_request():
        session.permanent = True
        # CSRF token generation removed since CSRF is disabled
        app.logger.debug("Session initialized without CSRF token")
    
    # Debug route for session inspection (CSRF disabled)
    @app.route('/debug/session')
    def debug_session():
        return {
            'session_id': session.get('_id'),
            'session_data': dict(session),
            'app_config': {
                'SECRET_KEY': bool(app.config.get('SECRET_KEY')),
                'WTF_CSRF_ENABLED': app.config.get('WTF_CSRF_ENABLED')
            }
        }
    
    # Configure logging
    configure_logging(app)
    
    # Register middleware
    try:
        from middleware import subscription_middleware
        app.before_request(subscription_middleware)
    except ImportError:
        app.logger.warning("Subscription middleware not found")
    
    # Register routes
    try:
        from routes import register_routes
        register_routes(app)
    except ImportError:
        app.logger.error("Failed to import routes")
    
    # Error handlers
    @app.errorhandler(400)
    def handle_bad_request(e):
        app.logger.warning(f"Bad request: {e}")
        flash('Invalid request. Please try again.', 'error')
        return redirect(url_for('auth_login'))
        
        context = {'error': e}
        if hasattr(current_user, 'is_authenticated'):
            context['current_user'] = current_user if current_user.is_authenticated else None
        return render_template('errors/400.html', **context), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        context = {'error': error}
        if hasattr(current_user, 'is_authenticated'):
            context['current_user'] = current_user if current_user.is_authenticated else None
        return render_template('errors/401.html', **context), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        context = {'error': error}
        if hasattr(current_user, 'is_authenticated'):
            context['current_user'] = current_user if current_user.is_authenticated else None
        return render_template('errors/403.html', **context), 403
    
    @app.errorhandler(404)
    def not_found(error):
        context = {'error': error}
        if hasattr(current_user, 'is_authenticated'):
            context['current_user'] = current_user if current_user.is_authenticated else None
        return render_template('errors/404.html', **context), 404
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        flash('File too large. Maximum size is 16MB.', 'error')
        return redirect(url_for('dashboard'))
    
    @app.errorhandler(500)
    def internal_server_error(error):
        db.session.rollback()
        context = {'error': error}
        if hasattr(current_user, 'is_authenticated'):
            context['current_user'] = current_user if current_user.is_authenticated else None
        return render_template('errors/500.html', **context), 500
    
    # Shell context
    @app.shell_context_processor
    def make_shell_context():
        try:
            from models import Centre, Student, Enquiry, Course, Scheme, FeePayment
            return {
                'db': db,
                'Centre': Centre,
                'Student': Student,
                'Enquiry': Enquiry,
                'Course': Course,
                'Scheme': Scheme,
                'FeePayment': FeePayment
            }
        except ImportError:
            return {'db': db}
    
    # Ensure directories exist
    with app.app_context():
        try:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            os.makedirs(app.instance_path, exist_ok=True)
            db.create_all()
        except Exception as e:
            app.logger.error(f"Startup error: {e}")
    
    return app

app = create_app()

if __name__ == '__main__':
    app.logger.info(f"Starting Student Management System on " f"{os.environ.get('HOST', '0.0.0.0')}:{os.environ.get('PORT', 8000)}")
    app.logger.info(f"Environment: {app.config['ENV']}")
    app.logger.info(f"Debug mode: {app.debug}")
    app.run(
        host=os.environ.get('HOST', '0.0.0.0'),
        port=int(os.environ.get('PORT', 8000)),
        debug=(app.config['ENV'] == 'development')
    )
