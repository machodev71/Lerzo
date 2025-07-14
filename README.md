# Student Management System - Production Ready

A comprehensive Flask-based SaaS student management platform for computer coaching centres, featuring multi-tenant architecture, subscription management, and integrated payment processing.

## 🚀 Features

- **Multi-tenant Architecture**: Each coaching centre manages their own data
- **Student Lifecycle Management**: From enquiry to enrollment to graduation
- **Fee Management**: Payment tracking, partial payments, and balance management
- **Course & Scheme Management**: Flexible course offerings and discount schemes
- **Subscription Management**: 14-day trial, monthly/yearly plans with Razorpay
- **Data Export**: Excel and PDF exports with customizable fields
- **Invoice Generation**: Professional PDF invoices for subscriptions
- **Dark/Light Mode**: User preference based theme switching

## 🛠 Technology Stack

- **Backend**: Flask 3.0, SQLAlchemy, PostgreSQL
- **Authentication**: Flask-Login with session management
- **Payment**: Razorpay Live Integration
- **Frontend**: Bootstrap 5, Font Awesome, Vanilla JavaScript
- **PDF Generation**: WeasyPrint
- **Data Processing**: Pandas, OpenPyXL

## 📋 Requirements

- Python 3.11+
- PostgreSQL
- Razorpay Account (Live Mode)

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd student-management-system

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` file with your settings:

```env
DATABASE_URL=postgresql://username:password@localhost/database_name
SESSION_SECRET=your-very-long-and-random-secret-key-here
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
FLASK_ENV=production
FLASK_DEBUG=False
```

### 3. Database Setup

```bash
# Create database tables
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"
```

### 4. Run Application

#### Development Mode
```bash
python main.py
```

#### Production Mode
```bash
# Using Gunicorn
gunicorn --config gunicorn.conf.py main:app

# Or using the deployment script
chmod +x deploy.sh
./deploy.sh
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `SESSION_SECRET` | Flask session encryption key | Yes |
| `RAZORPAY_KEY_ID` | Razorpay API key ID | Yes |
| `RAZORPAY_KEY_SECRET` | Razorpay API key secret | Yes |
| `FLASK_ENV` | Environment (production/development) | No |
| `FLASK_DEBUG` | Debug mode (True/False) | No |
| `HOST` | Server host (default: 0.0.0.0) | No |
| `PORT` | Server port (default: 5000) | No |

### Security Features

- CSRF protection on all forms
- Session security with HttpOnly cookies
- Password hashing with Werkzeug
- SQL injection prevention with SQLAlchemy ORM
- File upload validation and size limits
- Environment-based configuration

## 📊 Subscription Plans

- **Trial**: 14-day free trial for all new centres
- **Monthly**: ₹699/month with monthly billing
- **Yearly**: ₹6999/year with annual billing

## 🏗 Architecture

### Database Schema
- **Centre**: Multi-tenant entity with subscription management
- **Student**: Complete student information and enrollment details
- **Enquiry**: Prospective student tracking
- **Course**: Available courses with fee structure
- **Scheme**: Discount schemes and offers
- **FeePayment**: Payment tracking and history
- **SubscriptionPayment**: SaaS billing and invoice generation

### File Structure
```
├── app.py                 # Flask application factory
├── main.py               # Application entry point
├── models.py             # Database models
├── routes.py             # URL routes and handlers
├── forms.py              # WTForms form definitions
├── utils.py              # Utility functions
├── middleware.py         # Custom middleware
├── templates/            # Jinja2 templates
├── static/              # CSS, JS, images
├── gunicorn.conf.py     # Production server config
└── requirements.txt     # Python dependencies
```

## 🚀 Deployment

### Heroku
```bash
git add .
git commit -m "Production ready deployment"
git push heroku main
```

### Digital Ocean / AWS / GCP
1. Use the provided `gunicorn.conf.py` for production
2. Set up PostgreSQL database
3. Configure environment variables
4. Use reverse proxy (Nginx) for static files

### Docker (Optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "--config", "gunicorn.conf.py", "main:app"]
```

## 🔄 Database Migrations

The application uses SQLAlchemy for database management. Tables are automatically created on first run.

For production updates:
```bash
# Backup database before changes
pg_dump $DATABASE_URL > backup.sql

# Update application code
git pull origin main

# Restart application (tables auto-update)
```

## 📈 Monitoring

Production logging is configured in `gunicorn.conf.py`:
- Access logs: Standard format
- Error logs: Detailed application errors
- Process monitoring: Worker restart policies

## 🔐 Security Checklist

- [x] Environment variables for secrets
- [x] CSRF protection enabled
- [x] Secure session cookies
- [x] Password hashing
- [x] SQL injection prevention
- [x] File upload validation
- [x] HTTPS ready (ProxyFix configured)

## 🤝 Support

For issues and support:
1. Check logs in production environment
2. Verify environment variables
3. Test database connectivity
4. Confirm Razorpay configuration

## 📄 License

This project is proprietary software for computer coaching centres.