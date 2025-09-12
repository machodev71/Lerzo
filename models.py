from datetime import datetime, timedelta
from flask_login import UserMixin
from sqlalchemy import func
from app import db

class Centre(UserMixin, db.Model):
    __tablename__ = 'centres'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    logo_filename = db.Column(db.String(255))
    
    # Subscription fields
    trial_start_date = db.Column(db.DateTime, default=datetime.utcnow)
    trial_end_date = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=14))
    subscription_type = db.Column(db.String(20))  # 'trial', 'monthly', 'yearly', 'expired'
    subscription_start_date = db.Column(db.DateTime)
    subscription_end_date = db.Column(db.DateTime)
    razorpay_subscription_id = db.Column(db.String(100))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    students = db.relationship('Student', backref='centre', lazy=True, cascade='all, delete-orphan')
    enquiries = db.relationship('Enquiry', backref='centre', lazy=True, cascade='all, delete-orphan')
    courses = db.relationship('Course', backref='centre', lazy=True, cascade='all, delete-orphan')
    schemes = db.relationship('Scheme', backref='centre', lazy=True, cascade='all, delete-orphan')
    fee_payments = db.relationship('FeePayment', backref='centre', lazy=True, cascade='all, delete-orphan')
    
    def is_subscription_active(self):
        now = datetime.utcnow()
        if self.subscription_type == 'trial':
            return now <= self.trial_end_date
        elif self.subscription_type in ['monthly', 'yearly']:
            return now <= self.subscription_end_date if self.subscription_end_date else False
        return False
    
    def get_subscription_status(self):
        if self.is_subscription_active():
            if self.subscription_type == 'trial':
                days_left = (self.trial_end_date - datetime.utcnow()).days
                return f"Trial - {days_left} days left"
            else:
                return f"{self.subscription_type.title()} - Active"
        return "Subscription Expired"

class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    duration_months = db.Column(db.Integer)
    fees = db.Column(db.Float, default=0)
    centre_id = db.Column(db.Integer, db.ForeignKey('centres.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    students = db.relationship('Student', backref='course', lazy=True)
    enquiries = db.relationship('Enquiry', backref='course_interested', lazy=True)

class Scheme(db.Model):
    __tablename__ = 'schemes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    discount_percentage = db.Column(db.Float, default=0)
    centre_id = db.Column(db.Integer, db.ForeignKey('centres.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    students = db.relationship('Student', backref='scheme', lazy=True)
    enquiries = db.relationship('Enquiry', backref='scheme', lazy=True)

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    enrollment_number = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    father_name = db.Column(db.String(200))
    sex = db.Column(db.String(10))
    age = db.Column(db.Integer)
    date_of_birth = db.Column(db.Date)
    date_of_joining = db.Column(db.Date, nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'))
    # Contact Information
    mobile1 = db.Column(db.String(15), nullable=False)
    mobile2 = db.Column(db.String(15))
    address_line1 = db.Column(db.String(255))
    address_line2 = db.Column(db.String(255))
    city = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    
    # Academic Information
    qualification = db.Column(db.String(200))
    
    # Fee Information
    total_fees = db.Column(db.Float, nullable=False)
    net_fees = db.Column(db.Float, nullable=False)
    concession = db.Column(db.Float, default=0)
    bill_number = db.Column(db.String(50))
    
    # Foreign Keys
    centre_id = db.Column(db.Integer, db.ForeignKey('centres.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    scheme_id = db.Column(db.Integer, db.ForeignKey('schemes.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    fee_payments = db.relationship('FeePayment', backref='student', lazy=True, cascade='all, delete-orphan')
    
    def get_total_paid(self):
        return sum(payment.amount for payment in self.fee_payments)
    
    def get_balance_fees(self):
        return self.net_fees - self.get_total_paid()
    
    def get_fee_status(self):
        balance = self.get_balance_fees()
        if balance <= 0:
            return "Paid"
        elif balance == self.net_fees:
            return "Unpaid"
        else:
            return "Partial"

class Enquiry(db.Model):
    __tablename__ = 'enquiries'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    father_name = db.Column(db.String(200))
    sex = db.Column(db.String(10))
    
    # Contact Information
    mobile1 = db.Column(db.String(15), nullable=False)
    mobile2 = db.Column(db.String(15))
    address = db.Column(db.Text)
    pincode = db.Column(db.String(10))
    
    # Additional Information
    employment_status = db.Column(db.String(100))
    qualification = db.Column(db.String(200))
    reason_for_interest = db.Column(db.Text)
    joining_plan = db.Column(db.String(200))
    source_of_information = db.Column(db.String(200))
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, converted, closed
    
    # Foreign Keys
    centre_id = db.Column(db.Integer, db.ForeignKey('centres.id'), nullable=False)
    course_interested_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    scheme_id = db.Column(db.Integer, db.ForeignKey('schemes.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FeePayment(db.Model):
    __tablename__ = 'fee_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(50))  # cash, card, online, cheque
    receipt_number = db.Column(db.String(50))
    notes = db.Column(db.Text)
    
    # Foreign Keys
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    centre_id = db.Column(db.Integer, db.ForeignKey('centres.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SubscriptionPayment(db.Model):
    __tablename__ = 'subscription_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    centre_id = db.Column(db.Integer, db.ForeignKey('centres.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    plan_type = db.Column(db.String(20), nullable=False)  # monthly, yearly
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    razorpay_payment_id = db.Column(db.String(100))
    razorpay_order_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    
    centre = db.relationship('Centre', backref='subscription_payments')


class Batch(db.Model):
    __tablename__ = 'batches'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Morning Batch"
    start_time = db.Column(db.Time, nullable=False)   # e.g., 09:00:00
    end_time = db.Column(db.Time, nullable=False)     # e.g., 11:00:00
    centre_id = db.Column(db.Integer, db.ForeignKey('centres.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    students = db.relationship('Student', backref='batch', lazy=True)