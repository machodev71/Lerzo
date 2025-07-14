#!/usr/bin/env python3
"""
Production-ready Student Management System
A comprehensive SaaS platform for computer coaching centres
"""

import os
import sys
from app import create_app

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Development server configuration
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    print(f"Starting Student Management System on {host}:{port}")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'production')}")
    print(f"Debug mode: {debug}")
    
    app.run(host=host, port=port, debug=debug)
