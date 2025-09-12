from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, IntegerField, FloatField, DateField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange, Regexp

from datetime import date

class LoginForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for this form
    
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class RegisterForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for this form
    
    name = StringField('Centre Name', validators=[DataRequired(), Length(min=2, max=200)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Address', validators=[Optional()])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    pincode = StringField('Pincode', validators=[Optional(), Length(max=10)])

class CourseForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for this form
    
    name = StringField('Course Name', validators=[DataRequired(), Length(min=2, max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    duration_months = IntegerField('Duration (Months)', validators=[Optional(), NumberRange(min=1)])
    fees = FloatField('Fees', validators=[Optional(), NumberRange(min=0)])

class SchemeForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for this form
    
    name = StringField('Scheme Name', validators=[DataRequired(), Length(min=2, max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    discount_percentage = FloatField('Discount Percentage', validators=[Optional(), NumberRange(min=0, max=100)])

class StudentForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for this form
    
    enrollment_number = StringField('Enrollment Number', validators=[Optional(), Length(max=50)])
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=200)])
    father_name = StringField('Father\'s Name', validators=[Optional(), Length(max=200)])
    sex = SelectField('Sex', choices=[('', 'Select'), ('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')], validators=[Optional()])
    age = IntegerField('Age', validators=[Optional(), NumberRange(min=1, max=120)])
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    date_of_joining = DateField('Date of Joining', validators=[DataRequired()], default=date.today)
    batch_id = SelectField('Batch', coerce=int, validators=[Optional()])
    # Contact Information
    mobile1 = StringField('Mobile 1', validators=[DataRequired(), Length(min=10, max=15)])
    mobile2 = StringField('Mobile 2', validators=[Optional(), Length(max=15)])
    address_line1 = StringField('Address Line 1', validators=[Optional(), Length(max=255)])
    address_line2 = StringField('Address Line 2', validators=[Optional(), Length(max=255)])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    pincode = StringField('Pincode', validators=[Optional(), Length(max=10)])
    
    # Academic Information
    qualification = StringField('Qualification', validators=[Optional(), Length(max=200)])
    
    # Fee Information
    total_fees = FloatField('Total Fees', validators=[DataRequired(), NumberRange(min=0)])
    concession = FloatField('Concession', validators=[Optional(), NumberRange(min=0)])
    bill_number = StringField('Bill Number', validators=[Optional(), Length(max=50)])
    
    # Initial Payment Information
    initial_payment_amount = FloatField('Initial Payment Amount', validators=[Optional(), NumberRange(min=0)])
    initial_payment_date = DateField('Initial Payment Date', validators=[Optional()], default=date.today)
    initial_payment_method = SelectField('Initial Payment Method', 
                                       choices=[('', 'Select Method'), ('CASH', 'Cash'), ('CARD', 'Card'), ('ONLINE', 'Online'), ('CHEQUE', 'Cheque')],
                                       validators=[Optional()])
    
    # Foreign Keys
    course_id = SelectField('Course', coerce=int, validators=[DataRequired()])
    scheme_id = SelectField('Scheme', coerce=int, validators=[Optional()])

class EnquiryForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for this form
    
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=200)])
    father_name = StringField('Father\'s Name', validators=[Optional(), Length(max=200)])
    sex = SelectField('Sex', choices=[('', 'Select'), ('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')], validators=[Optional()])
    
    # Contact Information
    mobile1 = StringField('Mobile 1', validators=[DataRequired(), Length(min=10, max=15)])
    mobile2 = StringField('Mobile 2', validators=[Optional(), Length(max=15)])
    address = TextAreaField('Address', validators=[Optional()])
    pincode = StringField('Pincode', validators=[Optional(), Length(max=10)])
    
    # Additional Information
    employment_status = StringField('Employment Status', validators=[Optional(), Length(max=100)])
    qualification = StringField('Qualification', validators=[Optional(), Length(max=200)])
    reason_for_interest = TextAreaField('Reason for Interest', validators=[Optional()])
    joining_plan = StringField('Joining Plan', validators=[Optional(), Length(max=200)])
    source_of_information = StringField('Source of Information', validators=[Optional(), Length(max=200)])
    
    # Foreign Keys
    course_interested_id = SelectField('Course Interested', coerce=int, validators=[Optional()])
    scheme_id = SelectField('Scheme', coerce=int, validators=[Optional()])

class FeePaymentForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for this form
    
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    payment_date = DateField('Payment Date', validators=[DataRequired()], default=date.today)
    payment_method = SelectField('Payment Method', 
                                choices=[('CASH', 'Cash'), ('CARD', 'Card'), ('ONLINE', 'Online'), ('CHEQUE', 'Cheque')],
                                validators=[DataRequired()])
    receipt_number = StringField('Receipt Number', validators=[Optional(), Length(max=50)])
    notes = TextAreaField('Notes', validators=[Optional()])

class LogoUploadForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for this form
    
    logo = FileField('Logo', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])

class BatchForm(FlaskForm):
    class Meta:
        csrf = False  # Disable CSRF for this form
    
    name = StringField('Batch Name', validators=[DataRequired(), Length(min=2, max=100)])
    is_active = BooleanField('Active', default=True)
    start_time = StringField('Start Time', validators=[DataRequired(), Regexp(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', 
                            message="Invalid time format. Use HH:MM (24-hour format)")])
    end_time = StringField('End Time', validators=[DataRequired(), Regexp(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', 
                          message="Invalid time format. Use HH:MM (24-hour format)")])