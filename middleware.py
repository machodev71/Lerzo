from flask import request, redirect, url_for, session, flash, g
from flask_login import current_user
from functools import wraps

def subscription_middleware():
    """Middleware to check subscription status before each request"""
    
    # Skip subscription check for certain routes
    exempt_routes = [
        'auth.login', 
        'auth.register', 
        'auth.logout',
        'subscription.plans',
        'subscription.payment',
        'subscription.callback',
        'static'
    ]
    
    # Skip for static files and exempt routes
    if request.endpoint in exempt_routes or request.endpoint is None:
        return
        
    # Skip if user is not authenticated
    if not current_user.is_authenticated:
        return
    
    # Check subscription status
    if not current_user.is_subscription_active():
        # Allow access only to subscription pages
        if not request.endpoint.startswith('subscription.'):
            flash('Your subscription has expired. Please renew to continue using the service.', 'warning')
            return redirect(url_for('subscription.plans'))

def subscription_required(f):
    """Decorator to require active subscription for specific routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if not current_user.is_subscription_active():
            flash('Active subscription required to access this feature.', 'warning')
            return redirect(url_for('subscription.plans'))
        
        return f(*args, **kwargs)
    return decorated_function
