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
    # Production server configuration
    host = os.environ.get('HOST', '103.25.175.157')  # Default to your production IP
    port = int(os.environ.get('PORT',8000))         # Default to port 5000
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"Starting Student Management System on {host}:{port}")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'production')}")
    print(f"Debug mode: {debug}")
    
    # Production configuration
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True  # Enable threading for better performance
    )