# Student Management System - SaaS Application

## Overview

This is a Flask-based SaaS student management system designed for computer coaching centres. The application allows multiple coaching centres to register independently and manage their students, enquiries, courses, schemes, and fee payments. The system includes a subscription-based model with a 14-day free trial and monthly/yearly pricing plans.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with SQLite/PostgreSQL support
- **Authentication**: Flask-Login for session management
- **Form Handling**: Flask-WTF with WTForms for form validation
- **File Uploads**: Werkzeug for handling logo uploads with PIL for image processing

### Frontend Architecture
- **Template Engine**: Jinja2 (Flask's default)
- **CSS Framework**: Bootstrap 5 for responsive UI
- **Icons**: Font Awesome 6
- **JavaScript**: Vanilla JavaScript for interactive features
- **Theme Support**: Dark/light mode toggle with localStorage persistence

### Database Schema
The application uses SQLAlchemy with a declarative base model. Key entities include:
- **Centre**: Main tenant entity with subscription management
- **Student**: Enrolled students with complete academic and fee information
- **Enquiry**: Prospective students who haven't enrolled yet
- **Course**: Available courses with duration and fee structure
- **Scheme**: Discount schemes applicable to students
- **FeePayment**: Payment tracking for students
- **SubscriptionPayment**: SaaS subscription payment records

## Key Components

### Authentication & Authorization
- Multi-tenant architecture where each centre manages only their data
- Session-based authentication using Flask-Login
- User loader function for centre authentication
- Remember me functionality for persistent sessions

### Subscription Management
- 14-day free trial for new centres
- Two subscription tiers: Monthly (₹699) and Yearly (₹6999)
- Subscription middleware that checks access on every request
- Automatic restriction to subscription pages when expired
- Integration ready for Razorpay payment gateway

### Student Management
- Complete student lifecycle from enquiry to enrollment
- Auto-generated enrollment numbers based on datetime
- Comprehensive student information including academic and contact details
- Fee management with partial payment support
- Student status tracking and course assignment

### Data Export Capabilities
- Excel export functionality using pandas and openpyxl
- PDF export capability using WeasyPrint
- Configurable field selection for exports
- Fee status filtering for targeted exports

### File Management
- Logo upload functionality for centres
- Image processing and thumbnail generation using PIL
- Secure file handling with proper validation
- Static file serving for uploaded content

## Data Flow

### User Registration Flow
1. Centre registers with basic information
2. Automatic 14-day trial period activation
3. Password hashing using Werkzeug security
4. Redirect to dashboard with trial status display

### Student Management Flow
1. Add enquiry → Convert to student → Manage fees
2. Auto-generation of enrollment numbers if not provided
3. Course and scheme assignment during enrollment
4. Fee payment tracking with balance calculations

### Subscription Flow
1. Trial expiry triggers subscription requirement
2. Middleware blocks access to all features except payment
3. Plan selection and payment processing
4. Subscription activation and feature restoration

## External Dependencies

### Python Packages
- **Flask**: Core web framework
- **Flask-SQLAlchemy**: Database ORM
- **Flask-Login**: Authentication management
- **Flask-WTF**: Form handling and CSRF protection
- **WTForms**: Form validation
- **Werkzeug**: Password hashing and file uploads
- **Pandas**: Data manipulation for exports
- **Pillow (PIL)**: Image processing
- **WeasyPrint**: PDF generation
- **OpenPyXL**: Excel file generation

### Frontend Libraries
- **Bootstrap 5**: CSS framework loaded via CDN
- **Font Awesome 6**: Icon library loaded via CDN
- **Custom CSS**: Application-specific styling with dark mode support

### Payment Integration
- **Razorpay**: Payment gateway integration (configured but implementation pending)
- Subscription ID tracking for recurring payments
- Payment callback handling for subscription activation

## Deployment Strategy

### Development Setup
- **Entry Point**: `main.py` runs the Flask development server
- **Host**: 0.0.0.0 (allows external connections)
- **Port**: 5000
- **Debug Mode**: Enabled for development

### Production Considerations
- **Proxy Support**: ProxyFix middleware for proper header handling
- **Database Configuration**: Environment-based database URL configuration
- **Session Security**: Environment-based secret key management
- **File Upload Limits**: 16MB maximum file size limit
- **Database Connection Pooling**: Configured with pool recycling and ping

### Environment Variables Required
- `DATABASE_URL`: Database connection string
- `SESSION_SECRET`: Flask session encryption key

### Database Management
- SQLAlchemy models with proper relationships and cascading deletes
- Database connection pooling with health checks
- Migration-ready structure using SQLAlchemy's declarative base

The application is designed to be easily deployable on cloud platforms with minimal configuration changes, supporting both SQLite for development and PostgreSQL for production environments.