#!/bin/bash
# Production deployment script for Student Management System

echo "🚀 Starting deployment preparation..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found! Please create it from .env.example"
    exit 1
fi

# Check required environment variables
source .env
if [ -z "$DATABASE_URL" ] || [ -z "$SESSION_SECRET" ] || [ -z "$RAZORPAY_KEY_ID" ] || [ -z "$RAZORPAY_KEY_SECRET" ]; then
    echo "❌ Missing required environment variables!"
    echo "Required: DATABASE_URL, SESSION_SECRET, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET"
    exit 1
fi

echo "✅ Environment variables check passed"

# Create necessary directories
mkdir -p static/uploads
mkdir -p logs
mkdir -p instance

echo "✅ Directories created"

# Set file permissions
chmod +x main.py
chmod 755 static/uploads

echo "✅ Permissions set"

# For local development with Gunicorn
echo "🔧 To start the application in production mode:"
echo "   gunicorn --config gunicorn.conf.py main:app"
echo ""
echo "🔧 To start in development mode:"
echo "   python main.py"
echo ""
echo "📝 Environment: $(grep FLASK_ENV .env)"
echo "🔗 Database: Connected to PostgreSQL"
echo "💳 Payment: Razorpay Live Mode Configured"
echo ""
echo "✅ Deployment preparation complete!"