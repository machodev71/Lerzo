import os
from datetime import datetime, timedelta, date
from flask import render_template, redirect, url_for, flash, request, send_file, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, or_
from app import db
from models import Centre, Student, Enquiry, Course, Scheme, FeePayment, SubscriptionPayment, Batch
from forms import (LoginForm, RegisterForm, StudentForm, EnquiryForm, CourseForm, 
                  SchemeForm, FeePaymentForm, LogoUploadForm, BatchForm)
from utils import (
    export_students_excel,
    export_students_pdf,
    export_enquiries_excel,
    export_enquiries_pdf,
    generate_invoice_pdf,
    generate_enrollment_number,
    calculate_net_fees
)
from middleware import subscription_required

def register_routes(app):
    @app.route('/terms-of-service')
    def terms_of_service():
        return render_template('legal/terms_of_service.html')

    @app.route('/privacy-policy')
    def privacy_policy():
        return render_template('legal/privacy_policy.html')
    
    # Auth Routes
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('auth_login'))
    
    @app.route('/login', methods=['GET', 'POST'])
    def auth_login():
        """Login page without CSRF protection"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = LoginForm()
        
        if request.method == 'POST':
            current_app.logger.info(f"Login attempt from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if form.validate_on_submit():
            try:
                centre = Centre.query.filter_by(email=form.email.data).first()
                
                if centre and check_password_hash(centre.password_hash, form.password.data):
                    login_user(centre, remember=form.remember_me.data)
                    
                    next_page = request.args.get('next')
                    if next_page:
                        return redirect(next_page)
                    
                    flash('Login successful!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Invalid email or password', 'error')
            except Exception as e:
                current_app.logger.error(f"Login error: {e}")
                flash('Login failed. Please try again.', 'error')
        
        return render_template('auth/login.html', form=form)
    
    @app.route('/register', methods=['GET', 'POST'])
    def auth_register():
        """Registration page without CSRF protection"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = RegisterForm()
        
        if form.validate_on_submit():
            try:
                existing_centre = Centre.query.filter_by(email=form.email.data).first()
                if existing_centre:
                    flash('Email already registered. Please use a different email.', 'error')
                    return render_template('auth/register.html', form=form)
                
                centre = Centre(
                    name=form.name.data,
                    email=form.email.data,
                    password_hash=generate_password_hash(form.password.data),
                    phone=form.phone.data,
                    address=form.address.data,
                    city=form.city.data,
                    pincode=form.pincode.data,
                    subscription_type='trial',
                    trial_start_date=datetime.utcnow(),
                    trial_end_date=datetime.utcnow() + timedelta(days=14)
                )
                
                db.session.add(centre)
                db.session.commit()
                
                create_default_batches(centre.id)
                
                login_user(centre)
                flash('Registration successful! You have 14 days free trial.', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Registration error: {e}")
                flash('Registration failed. Please try again.', 'error')
        
        return render_template('auth/register.html', form=form)

    def create_default_batches(centre_id):
        """Create default batch timings for a new centre"""
        default_batches = [
            {"name": "Morning (6-8 AM)", "start_time": "06:00", "end_time": "08:00"},
            {"name": "Morning (8-10 AM)", "start_time": "08:00", "end_time": "10:00"},
            {"name": "Morning (10-12 PM)", "start_time": "10:00", "end_time": "12:00"},
            {"name": "Afternoon (12-2 PM)", "start_time": "12:00", "end_time": "14:00"},
            {"name": "Afternoon (2-4 PM)", "start_time": "14:00", "end_time": "16:00"},
            {"name": "Evening (4-6 PM)", "start_time": "16:00", "end_time": "18:00"},
            {"name": "Evening (6-8 PM)", "start_time": "18:00", "end_time": "20:00"},
            {"name": "Night (8-9 PM)", "start_time": "20:00", "end_time": "21:00"},
        ]
        
        try:
            for batch in default_batches:
                new_batch = Batch(
                    name=batch["name"],
                    start_time=datetime.strptime(batch["start_time"], "%H:%M").time(),
                    end_time=datetime.strptime(batch["end_time"], "%H:%M").time(),
                    centre_id=centre_id
                )
                db.session.add(new_batch)
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating default batches: {str(e)}")
            raise
    
    @app.route('/logout')
    @login_required
    def auth_logout():
        """Logout"""
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('auth_login'))
    
    @app.route('/dashboard')
    @login_required
    @subscription_required
    def dashboard():
        try:
            total_students = Student.query.filter_by(centre_id=current_user.id).count()
            total_enquiries = Enquiry.query.filter_by(centre_id=current_user.id, status='active').count()
            
            paid_students = Student.query.filter_by(centre_id=current_user.id).all()
            total_fees_collected = sum(student.get_total_paid() for student in paid_students)
            pending_fees = sum(student.get_balance_fees() for student in paid_students)
            
            fully_paid = sum(1 for student in paid_students if student.get_fee_status() == 'Paid')
            partially_paid = sum(1 for student in paid_students if student.get_fee_status() == 'Partial')
            unpaid = sum(1 for student in paid_students if student.get_fee_status() == 'Unpaid')
            
            recent_students = Student.query.filter_by(centre_id=current_user.id)\
                                        .order_by(Student.created_at.desc()).limit(5).all()
            
            recent_enquiries = Enquiry.query.filter_by(centre_id=current_user.id, status='active')\
                                          .order_by(Enquiry.created_at.desc()).limit(5).all()
            
            return render_template('dashboard/index.html',
                                 total_students=total_students,
                                 total_enquiries=total_enquiries,
                                 total_fees_collected=total_fees_collected,
                                 pending_fees=pending_fees,
                                 fully_paid=fully_paid,
                                 partially_paid=partially_paid,
                                 unpaid=unpaid,
                                 recent_students=recent_students,
                                 recent_enquiries=recent_enquiries)
        except Exception as e:
            current_app.logger.error(f"Dashboard error: {e}")
            flash('Error loading dashboard data', 'error')
            return render_template('dashboard/index.html', stats={})
    
    @app.route('/batches')
    @login_required
    @subscription_required
    def batches_list():
        batches = Batch.query.filter_by(centre_id=current_user.id).order_by(Batch.start_time).all()
        return render_template('batches/list.html', batches=batches)

    @app.route('/batches/add', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def batches_add():
        form = BatchForm()
        
        if request.method == 'POST':
            current_app.logger.info(f"Batch add attempt from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if form.validate_on_submit():
            try:
                start_time = datetime.strptime(form.start_time.data, '%H:%M').time()
                end_time = datetime.strptime(form.end_time.data, '%H:%M').time()
            except ValueError:
                flash('Invalid time format. Please use HH:MM format (24-hour)', 'error')
                return render_template('batches/add.html', form=form)
            
            if start_time >= end_time:
                flash('End time must be after start time', 'error')
                return render_template('batches/add.html', form=form)
            
            batch = Batch(
                name=form.name.data,
                start_time=start_time,
                end_time=end_time,
                is_active=form.is_active.data,
                centre_id=current_user.id
            )
            
            db.session.add(batch)
            db.session.commit()
            
            flash('Batch added successfully', 'success')
            return redirect(url_for('batches_list'))
        
        return render_template('batches/add.html', form=form)

    @app.route('/batches/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def batches_edit(id):
        batch = Batch.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        form = BatchForm(obj=batch)
        
        if batch.start_time:
            form.start_time.data = batch.start_time.strftime('%H:%M')
        if batch.end_time:
            form.end_time.data = batch.end_time.strftime('%H:%M')
        
        if request.method == 'POST':
            current_app.logger.info(f"Batch edit attempt for batch {id} from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if form.validate_on_submit():
            try:
                start_time = datetime.strptime(form.start_time.data, '%H:%M').time()
                end_time = datetime.strptime(form.end_time.data, '%H:%M').time()
            except ValueError:
                flash('Invalid time format. Please use HH:MM format (24-hour)', 'error')
                return render_template('batches/edit.html', form=form, batch=batch)
            
            if start_time >= end_time:
                flash('End time must be after start time', 'error')
                return render_template('batches/edit.html', form=form, batch=batch)
            
            batch.name = form.name.data
            batch.start_time = start_time
            batch.end_time = end_time
            batch.is_active = form.is_active.data
            
            db.session.commit()
            flash('Batch updated successfully', 'success')
            return redirect(url_for('batches_list'))
        
        return render_template('batches/edit.html', form=form, batch=batch)

    @app.route('/batches/<int:id>/delete', methods=['POST'])
    @login_required
    @subscription_required
    def batches_delete(id):
        batch = Batch.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        
        student_count = Student.query.filter_by(batch_id=batch.id).count()
        if student_count > 0:
            flash(f'Cannot delete batch as it has {student_count} enrolled students', 'error')
            return redirect(url_for('batches_list'))
        
        db.session.delete(batch)
        db.session.commit()
        flash('Batch deleted successfully', 'success')
        return redirect(url_for('batches_list'))
    
    @app.route('/students/add', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def students_add():
        form = StudentForm()
        
        courses = Course.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.course_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in courses]
        
        schemes = Scheme.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.scheme_id.choices = [(0, 'Select Scheme')] + [(s.id, s.name) for s in schemes]
        
        batches = Batch.query.filter_by(centre_id=current_user.id, is_active=True).order_by(Batch.start_time).all()
        form.batch_id.choices = [(0, 'Select Batch')] + [(b.id, f"{b.name} ({b.start_time.strftime('%I:%M %p')} - {b.end_time.strftime('%I:%M %p')})") for b in batches]
        
        if request.method == 'POST':
            current_app.logger.info(f"Student add attempt from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if form.validate_on_submit():
            enrollment_number = form.enrollment_number.data or generate_enrollment_number()
            
            existing_student = Student.query.filter_by(
                centre_id=current_user.id, 
                enrollment_number=enrollment_number
            ).first()
            
            if existing_student:
                flash('Enrollment number already exists', 'error')
                return render_template('students/add.html', form=form, batches=batches)
            
            net_fees = calculate_net_fees(form.total_fees.data, form.concession.data)
            
            student = Student(
                enrollment_number=enrollment_number,
                name=form.name.data.upper(),
                father_name=form.father_name.data.upper() if form.father_name.data else None,
                sex=form.sex.data,
                age=form.age.data,
                date_of_birth=form.date_of_birth.data,
                date_of_joining=form.date_of_joining.data,
                mobile1=form.mobile1.data,
                mobile2=form.mobile2.data,
                address_line1=form.address_line1.data.upper() if form.address_line1.data else None,
                address_line2=form.address_line2.data.upper() if form.address_line2.data else None,
                city=form.city.data.upper() if form.city.data else None,
                pincode=form.pincode.data,
                qualification=form.qualification.data.upper() if form.qualification.data else None,
                total_fees=form.total_fees.data,
                net_fees=net_fees,
                concession=form.concession.data or 0,
                bill_number=form.bill_number.data,
                centre_id=current_user.id,
                course_id=form.course_id.data if form.course_id.data != 0 else None,
                scheme_id=form.scheme_id.data if form.scheme_id.data != 0 else None,
                batch_id=form.batch_id.data if form.batch_id.data != 0 else None
            )
            
            db.session.add(student)
            db.session.flush()
            
            if form.initial_payment_amount.data and float(form.initial_payment_amount.data) > 0:
                payment = FeePayment(
                    amount=form.initial_payment_amount.data,
                    payment_date=form.initial_payment_date.data or date.today(),
                    payment_method=form.initial_payment_method.data,
                    receipt_number=form.bill_number.data,
                    notes="Initial payment",
                    student_id=student.id,
                    centre_id=current_user.id
                )
                db.session.add(payment)
            
            db.session.commit()
            
            flash('Student added successfully', 'success')
            return redirect(url_for('students_list'))
        
        return render_template('students/add.html', form=form, batches=batches)
        
    @app.route('/students')
    @login_required
    @subscription_required
    def students_list():
        page = request.args.get('page', 1, type=int)
        fee_status = request.args.get('fee_status', 'all')
        search = request.args.get('search', '')
        batch_id = request.args.get('batch_id', None, type=int)
        
        query = Student.query.filter_by(centre_id=current_user.id)
        
        if batch_id:
            query = query.filter_by(batch_id=batch_id)
        
        if search:
            query = query.filter(or_(
                Student.name.ilike(f'%{search}%'),
                Student.enrollment_number.ilike(f'%{search}%'),
                Student.mobile1.ilike(f'%{search}%')
            ))
        
        if fee_status != 'all':
            students_temp = query.all()
            filtered_students = []
            for student in students_temp:
                if fee_status == 'paid' and student.get_fee_status() == 'Paid':
                    filtered_students.append(student)
                elif fee_status == 'partial' and student.get_fee_status() == 'Partial':
                    filtered_students.append(student)
                elif fee_status == 'unpaid' and student.get_fee_status() == 'Unpaid':
                    filtered_students.append(student)
            
            per_page = 10
            start = (page - 1) * per_page
            end = start + per_page
            paginated_students = filtered_students[start:end]
            total = len(filtered_students)
            has_prev = page > 1
            has_next = end < total
            prev_num = page - 1 if has_prev else None
            next_num = page + 1 if has_next else None
            
            class MockPagination:
                def __init__(self, items, total, has_prev, has_next, prev_num, next_num):
                    self.items = items
                    self.total = total
                    self.has_prev = has_prev
                    self.has_next = has_next
                    self.prev_num = prev_num
                    self.next_num = next_num
            
            students = MockPagination(paginated_students, total, has_prev, has_next, prev_num, next_num)
        else:
            students = query.paginate(page=page, per_page=10, error_out=False)
        
        batches = Batch.query.filter_by(centre_id=current_user.id).order_by(Batch.start_time).all()
        
        return render_template('students/list.html', students=students, 
                            fee_status=fee_status, search=search, batches=batches,
                            selected_batch=batch_id)

    @app.route('/students/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def students_edit(id):
        student = Student.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        form = StudentForm(obj=student)
        
        courses = Course.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.course_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in courses]
        
        schemes = Scheme.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.scheme_id.choices = [(0, 'Select Scheme')] + [(s.id, s.name) for s in schemes]
        
        batches = Batch.query.filter_by(centre_id=current_user.id, is_active=True).order_by(Batch.start_time).all()
        form.batch_id.choices = [(0, 'Select Batch')] + [(b.id, f"{b.name} ({b.start_time.strftime('%I:%M %p')} - {b.end_time.strftime('%I:%M %p')})") for b in batches]
        
        initial_payment = FeePayment.query.filter_by(
            student_id=student.id,
            receipt_number=student.bill_number
        ).first()
        
        if initial_payment:
            form.initial_payment_amount.data = initial_payment.amount
            form.initial_payment_date.data = initial_payment.payment_date
            form.initial_payment_method.data = initial_payment.payment_method
        
        if request.method == 'POST':
            current_app.logger.info(f"Student edit attempt for student {id} from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if form.validate_on_submit():
            existing_student = Student.query.filter(
                Student.centre_id == current_user.id,
                Student.enrollment_number == form.enrollment_number.data,
                Student.id != student.id
            ).first()
            
            if existing_student:
                flash('Enrollment number already exists', 'error')
                return render_template('students/edit.html', form=form, student=student)
            
            net_fees = calculate_net_fees(form.total_fees.data, form.concession.data)
            
            student.enrollment_number = form.enrollment_number.data
            student.name = form.name.data.upper()
            student.father_name = form.father_name.data.upper() if form.father_name.data else None
            student.sex = form.sex.data
            student.age = form.age.data
            student.date_of_birth = form.date_of_birth.data
            student.date_of_joining = form.date_of_joining.data
            student.mobile1 = form.mobile1.data
            student.mobile2 = form.mobile2.data
            student.address_line1 = form.address_line1.data.upper() if form.address_line1.data else None
            student.address_line2 = form.address_line2.data.upper() if form.address_line2.data else None
            student.city = form.city.data.upper() if form.city.data else None
            student.pincode = form.pincode.data
            student.qualification = form.qualification.data.upper() if form.qualification.data else None
            student.total_fees = form.total_fees.data
            student.net_fees = net_fees
            student.concession = form.concession.data or 0
            student.bill_number = form.bill_number.data
            student.course_id = form.course_id.data if form.course_id.data != 0 else None
            student.scheme_id = form.scheme_id.data if form.scheme_id.data != 0 else None
            student.batch_id = form.batch_id.data if form.batch_id.data != 0 else None
            
            if form.initial_payment_amount.data and float(form.initial_payment_amount.data) > 0:
                initial_payment = FeePayment.query.filter_by(
                    student_id=student.id,
                    receipt_number=student.bill_number
                ).first()
                
                if initial_payment:
                    initial_payment.amount = form.initial_payment_amount.data
                    initial_payment.payment_date = form.initial_payment_date.data or date.today()
                    initial_payment.payment_method = form.initial_payment_method.data
                else:
                    payment = FeePayment(
                        amount=form.initial_payment_amount.data,
                        payment_date=form.initial_payment_date.data or date.today(),
                        payment_method=form.initial_payment_method.data,
                        receipt_number=student.bill_number,
                        notes="Initial payment",
                        student_id=student.id,
                        centre_id=current_user.id
                    )
                    db.session.add(payment)
            
            db.session.commit()
            flash('Student updated successfully', 'success')
            return redirect(url_for('students_list'))
        
        return render_template('students/edit.html', form=form, student=student)
    
    @app.route('/students/<int:id>')
    @login_required
    @subscription_required
    def students_view(id):
        student = Student.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        fee_payments = FeePayment.query.filter_by(student_id=student.id)\
                                     .order_by(FeePayment.payment_date.desc()).all()
        return render_template('students/view.html', student=student, fee_payments=fee_payments)
    
    @app.route('/students/<int:id>/delete', methods=['POST'])
    @login_required
    @subscription_required
    def students_delete(id):
        student = Student.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        db.session.delete(student)
        db.session.commit()
        flash('Student deleted successfully', 'success')
        return redirect(url_for('students_list'))
    
    @app.route('/students/<int:id>/pay-fees', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def pay_fees(id):
        student = Student.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        form = FeePaymentForm()
        
        if request.method == 'POST':
            current_app.logger.info(f"Fee payment attempt for student {id} from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if form.validate_on_submit():
            balance = student.get_balance_fees()
            if form.amount.data > balance:
                flash(f'Payment amount cannot exceed balance fees of ₹{balance:.2f}', 'error')
                return render_template('fees/payment.html', form=form, student=student)
            
            payment = FeePayment(
                amount=form.amount.data,
                payment_date=form.payment_date.data,
                payment_method=form.payment_method.data,
                receipt_number=form.receipt_number.data,
                notes=form.notes.data,
                student_id=student.id,
                centre_id=current_user.id
            )
            
            db.session.add(payment)
            db.session.commit()
            
            flash('Fee payment recorded successfully', 'success')
            return redirect(url_for('students_view', id=student.id))
        
        return render_template('fees/payment.html', form=form, student=student)
    
    @app.route('/enquiries')
    @login_required
    @subscription_required
    def enquiries_list():
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', 'active')
        search = request.args.get('search', '')
        
        query = Enquiry.query.filter_by(centre_id=current_user.id, status=status)
        
        if search:
            query = query.filter(or_(
                Enquiry.name.ilike(f'%{search}%'),
                Enquiry.mobile1.ilike(f'%{search}%')
            ))
        
        enquiries = query.paginate(page=page, per_page=10, error_out=False)
        return render_template('enquiries/list.html', enquiries=enquiries, 
                             status=status, search=search)
    
    @app.route('/enquiries/add', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def enquiries_add():
        form = EnquiryForm()
        
        courses = Course.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.course_interested_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in courses]
        
        schemes = Scheme.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.scheme_id.choices = [(0, 'Select Scheme')] + [(s.id, s.name) for s in schemes]
        
        if request.method == 'POST':
            current_app.logger.info(f"Enquiry add attempt from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if form.validate_on_submit():
            enquiry = Enquiry(
                name=form.name.data.upper(),
                father_name=form.father_name.data.upper() if form.father_name.data else None,
                sex=form.sex.data,
                mobile1=form.mobile1.data,
                mobile2=form.mobile2.data,
                address=form.address.data.upper() if form.address.data else None,
                pincode=form.pincode.data,
                employment_status=form.employment_status.data.upper() if form.employment_status.data else None,
                qualification=form.qualification.data.upper() if form.qualification.data else None,
                reason_for_interest=form.reason_for_interest.data,
                joining_plan=form.joining_plan.data.upper() if form.joining_plan.data else None,
                source_of_information=form.source_of_information.data.upper() if form.source_of_information.data else None,
                centre_id=current_user.id,
                course_interested_id=form.course_interested_id.data if form.course_interested_id.data != 0 else None,
                scheme_id=form.scheme_id.data if form.scheme_id.data != 0 else None
            )
            
            db.session.add(enquiry)
            db.session.commit()
            
            flash('Enquiry added successfully', 'success')
            return redirect(url_for('enquiries_list'))
        
        return render_template('enquiries/add.html', form=form)
    
    @app.route('/enquiries/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def enquiries_edit(id):
        enquiry = Enquiry.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        form = EnquiryForm(obj=enquiry)
        
        courses = Course.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.course_interested_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in courses]
        
        schemes = Scheme.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.scheme_id.choices = [(0, 'Select Scheme')] + [(s.id, s.name) for s in schemes]
        
        if request.method == 'POST':
            current_app.logger.info(f"Enquiry edit attempt for enquiry {id} from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if form.validate_on_submit():
            enquiry.name = form.name.data.upper()
            enquiry.father_name = form.father_name.data.upper() if form.father_name.data else None
            enquiry.sex = form.sex.data
            enquiry.mobile1 = form.mobile1.data
            enquiry.mobile2 = form.mobile2.data
            enquiry.address = form.address.data.upper() if form.address.data else None
            enquiry.pincode = form.pincode.data
            enquiry.employment_status = form.employment_status.data.upper() if form.employment_status.data else None
            enquiry.qualification = form.qualification.data.upper() if form.qualification.data else None
            enquiry.reason_for_interest = form.reason_for_interest.data
            enquiry.joining_plan = form.joining_plan.data.upper() if form.joining_plan.data else None
            enquiry.source_of_information = form.source_of_information.data.upper() if form.source_of_information.data else None
            enquiry.course_interested_id = form.course_interested_id.data if form.course_interested_id.data != 0 else None
            enquiry.scheme_id = form.scheme_id.data if form.scheme_id.data != 0 else None
            
            db.session.commit()
            flash('Enquiry updated successfully', 'success')
            return redirect(url_for('enquiries_list'))
        
        return render_template('enquiries/edit.html', form=form, enquiry=enquiry)
    
    @app.route('/enquiries/<int:id>/convert', methods=['POST'])
    @login_required
    @subscription_required
    def enquiries_convert(id):
        enquiry = Enquiry.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        
        student = Student(
            enrollment_number=generate_enrollment_number(),
            name=enquiry.name,
            father_name=enquiry.father_name,
            sex=enquiry.sex,
            mobile1=enquiry.mobile1,
            mobile2=enquiry.mobile2,
            address_line1=enquiry.address,
            pincode=enquiry.pincode,
            qualification=enquiry.qualification,
            date_of_joining=date.today(),
            total_fees=0,
            net_fees=0,
            centre_id=current_user.id,
            course_id=enquiry.course_interested_id,
            scheme_id=enquiry.scheme_id
        )
        
        enquiry.status = 'converted'
        
        db.session.add(student)
        db.session.commit()
        
        flash('Enquiry converted to student successfully', 'success')
        return redirect(url_for('students_edit', id=student.id))
    
    @app.route('/enquiries/<int:id>/delete', methods=['POST'])
    @login_required
    @subscription_required
    def enquiries_delete(id):
        enquiry = Enquiry.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        db.session.delete(enquiry)
        db.session.commit()
        flash('Enquiry deleted successfully', 'success')
        return redirect(url_for('enquiries_list'))
    
    @app.route('/courses')
    @login_required
    @subscription_required
    def courses_list():
        courses = Course.query.filter_by(centre_id=current_user.id).all()
        return render_template('courses/list.html', courses=courses)
    
    @app.route('/courses/add', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def courses_add():
        form = CourseForm()
        
        if request.method == 'POST':
            current_app.logger.info(f"Course add attempt from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if form.validate_on_submit():
            course = Course(
                name=form.name.data.upper(),
                description=form.description.data,
                duration_months=form.duration_months.data,
                fees=form.fees.data or 0,
                centre_id=current_user.id
            )
            
            db.session.add(course)
            db.session.commit()
            
            flash('Course added successfully', 'success')
            return redirect(url_for('courses_list'))
        
        return render_template('courses/add.html', form=form)
    
    @app.route('/courses/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def courses_edit(id):
        course = Course.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        form = CourseForm(obj=course)
        
        if request.method == 'POST':
            current_app.logger.info(f"Course edit attempt for course {id} from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if form.validate_on_submit():
            course.name = form.name.data.upper()
            course.description = form.description.data
            course.duration_months = form.duration_months.data
            course.fees = form.fees.data or 0
            
            db.session.commit()
            flash('Course updated successfully', 'success')
            return redirect(url_for('courses_list'))
        
        return render_template('courses/edit.html', form=form, course=course)
    
    @app.route('/courses/<int:id>/delete', methods=['POST'])
    @login_required
    @subscription_required
    def courses_delete(id):
        course = Course.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        
        if course.students:
            flash('Cannot delete course as it has enrolled students', 'error')
            return redirect(url_for('courses_list'))
            
        db.session.delete(course)
        db.session.commit()
        flash('Course deleted successfully', 'success')
        return redirect(url_for('courses_list'))
    
    @app.route('/schemes')
    @login_required
    @subscription_required
    def schemes_list():
        schemes = Scheme.query.filter_by(centre_id=current_user.id).all()
        return render_template('schemes/list.html', schemes=schemes)
    
    @app.route('/schemes/add', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def schemes_add():
        form = SchemeForm()
        
        if request.method == 'POST':
            current_app.logger.info(f"Scheme add attempt from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if form.validate_on_submit():
            scheme = Scheme(
                name=form.name.data.upper(),
                description=form.description.data,
                discount_percentage=form.discount_percentage.data or 0,
                centre_id=current_user.id
            )
            
            db.session.add(scheme)
            db.session.commit()
            
            flash('Scheme added successfully', 'success')
            return redirect(url_for('schemes_list'))
        
        return render_template('schemes/add.html', form=form)
    
    @app.route('/schemes/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def schemes_edit(id):
        scheme = Scheme.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        form = SchemeForm(obj=scheme)
        
        if request.method == 'POST':
            current_app.logger.info(f"Scheme edit attempt for scheme {id} from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if form.validate_on_submit():
            scheme.name = form.name.data.upper()
            scheme.description = form.description.data
            scheme.discount_percentage = form.discount_percentage.data or 0
            
            db.session.commit()
            flash('Scheme updated successfully', 'success')
            return redirect(url_for('schemes_list'))
        
        return render_template('schemes/edit.html', form=form, scheme=scheme)
    
    @app.route('/schemes/<int:id>/delete', methods=['POST'])
    @login_required
    @subscription_required
    def schemes_delete(id):
        scheme = Scheme.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        
        if scheme.students:
            flash('Cannot delete scheme as it has enrolled students', 'error')
            return redirect(url_for('schemes_list'))
            
        db.session.delete(scheme)
        db.session.commit()
        flash('Scheme deleted successfully', 'success')
        return redirect(url_for('schemes_list'))
    
    @app.route('/settings')
    @login_required
    @subscription_required
    def settings_index():
        return render_template('settings/index.html')

    @app.route('/settings/logo', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def settings_logo():
        form = LogoUploadForm()
        
        if request.method == 'POST':
            current_app.logger.info(f"Logo upload attempt from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if form.validate_on_submit():
            if form.logo.data:
                logo_file = form.logo.data
                filename = f"logo_{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{logo_file.filename.split('.')[-1]}"
                
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                
                logo_path = os.path.join(upload_dir, filename)
                logo_file.save(logo_path)
                
                current_user.logo_filename = filename
                db.session.commit()
                
                flash('Logo updated successfully', 'success')
                return redirect(url_for('settings_logo'))
        
        return render_template('settings/logo.html', form=form)

    @app.route('/settings/profile', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def settings_profile():
        form = RegisterForm(obj=current_user)
        form.password.validators = []
        
        if request.method == 'POST':
            current_app.logger.info(f"Profile update attempt from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if form.validate_on_submit():
            current_user.name = form.name.data
            current_user.email = form.email.data
            current_user.phone = form.phone.data
            current_user.address = form.address.data
            current_user.city = form.city.data
            current_user.pincode = form.pincode.data
            
            if form.password.data:
                current_user.password_hash = generate_password_hash(form.password.data)
            
            db.session.commit()
            flash('Profile updated successfully', 'success')
            return redirect(url_for('settings_profile'))
        
        return render_template('settings/profile.html', form=form)

    @app.route('/settings/invoices')
    @login_required
    @subscription_required
    def settings_invoices():
        return render_template('settings/invoices.html')

    @app.route('/settings/backup')
    @login_required
    @subscription_required
    def settings_backup():
        return render_template('settings/backup.html')

    @app.route('/settings/subscription')
    @login_required
    @subscription_required
    def settings_subscription():
        return render_template('settings/subscription.html')

    @app.route('/settings/help')
    @login_required
    @subscription_required
    def settings_help():
        return render_template('settings/help.html')

    @app.route('/reports')
    @login_required
    @subscription_required
    def reports_index():
        return render_template('reports/index.html')

    @app.route('/reports/students')
    @login_required
    @subscription_required
    def reports_students():
        total_students = Student.query.filter_by(centre_id=current_user.id).count()
        
        students = Student.query.filter_by(centre_id=current_user.id).all()
        fully_paid = sum(1 for student in students if student.get_fee_status() == 'Paid')
        partially_paid = sum(1 for student in students if student.get_fee_status() == 'Partial')
        unpaid = sum(1 for student in students if student.get_fee_status() == 'Unpaid')
        
        try:
            course_stats = db.session.query(
                Course.name,
                func.count(Student.id).label('student_count')
            ).join(Student).filter(
                Course.centre_id == current_user.id
            ).group_by(Course.name).all()
        except:
            course_stats = []
        
        return render_template('reports/students.html',
                             total_students=total_students,
                             fully_paid=fully_paid,
                             partially_paid=partially_paid,
                             unpaid=unpaid,
                             course_stats=course_stats)

    @app.route('/reports/fees')
    @login_required
    @subscription_required
    def reports_fees():
        students = Student.query.filter_by(centre_id=current_user.id).all()
        total_fees = sum(student.net_fees or 0 for student in students)
        collected_fees = sum(student.get_total_paid() for student in students)
        pending_fees = sum(student.get_balance_fees() for student in students)
        
        monthly_collections = []
        for i in range(12):
            month_start = (datetime.now().replace(day=1) - timedelta(days=30*i)).replace(day=1)
            try:
                month_end = (month_start.replace(month=month_start.month+1) if month_start.month < 12 
                            else month_start.replace(year=month_start.year+1, month=1)) - timedelta(days=1)
            except:
                month_end = month_start.replace(day=28)
            
            month_payments = FeePayment.query.filter(
                FeePayment.centre_id == current_user.id,
                FeePayment.payment_date >= month_start.date(),
                FeePayment.payment_date <= month_end.date()
            ).all()
            
            monthly_collections.append({
                'month': month_start.strftime('%b %Y'),
                'amount': sum(p.amount for p in month_payments)
            })
        
        monthly_collections.reverse()
        
        return render_template('reports/fees.html',
                             total_fees=total_fees,
                             collected_fees=collected_fees,
                             pending_fees=pending_fees,
                             monthly_collections=monthly_collections)

    @app.route('/reports/batches')
    @login_required
    @subscription_required
    def reports_batches():
        batches = Batch.query.filter_by(centre_id=current_user.id).all()
        batch_stats = []
        
        for batch in batches:
            student_count = Student.query.filter_by(batch_id=batch.id).count()
            batch_stats.append({
                'name': batch.name,
                'time': f"{batch.start_time.strftime('%I:%M %p')} - {batch.end_time.strftime('%I:%M %p')}",
                'student_count': student_count,
                'is_active': batch.is_active
            })
        
        return render_template('reports/batches.html', batch_stats=batch_stats)

    @app.route('/reports/enquiries')
    @login_required
    @subscription_required
    def reports_enquiries():
        total_enquiries = Enquiry.query.filter_by(centre_id=current_user.id).count()
        active_enquiries = Enquiry.query.filter_by(centre_id=current_user.id, status='active').count()
        converted_enquiries = Enquiry.query.filter_by(centre_id=current_user.id, status='converted').count()
        
        return render_template('reports/enquiries.html',
                             total_enquiries=total_enquiries,
                             active_enquiries=active_enquiries,
                             converted_enquiries=converted_enquiries)

    @app.route('/api/students/count')
    @login_required
    @subscription_required
    def api_students_count():
        count = Student.query.filter_by(centre_id=current_user.id).count()
        return jsonify({'count': count})

    @app.route('/api/enquiries/count')
    @login_required
    @subscription_required
    def api_enquiries_count():
        count = Enquiry.query.filter_by(centre_id=current_user.id, status='active').count()
        return jsonify({'count': count})

    @app.route('/api/batches/count')
    @login_required
    @subscription_required
    def api_batches_count():
        count = Batch.query.filter_by(centre_id=current_user.id).count()
        return jsonify({'count': count})

    @app.route('/students/<int:id>/invoice')
    @login_required
    @subscription_required
    def generate_student_invoice(id):
        student = Student.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        
        try:
            output = generate_invoice_pdf(student, current_user)
            filename = f'invoice_{student.enrollment_number}_{datetime.now().strftime("%Y%m%d")}.pdf'
            
            return send_file(
                output,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        except Exception as e:
            current_app.logger.error(f"Error generating invoice: {str(e)}")
            flash('Error generating invoice', 'error')
            return redirect(url_for('students_view', id=id))
    
    @app.route('/export/options')
    @login_required
    @subscription_required
    def export_options():
        return render_template('exports/options.html')

    @app.route('/export/excel', methods=['POST'])
    @login_required
    @subscription_required
    def export_excel():
        export_type = request.form.get('export_type', 'students')
        
        if request.method == 'POST':
            current_app.logger.info(f"Excel export attempt from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if export_type == 'students':
            fee_status = request.form.get('fee_status', 'all')
            fields = request.form.getlist('student_fields')
            
            query = Student.query.filter_by(centre_id=current_user.id)
            
            if fee_status != 'all':
                students_temp = query.all()
                students = []
                for student in students_temp:
                    if fee_status == 'paid' and student.get_fee_status() == 'Paid':
                        students.append(student)
                    elif fee_status == 'partial' and student.get_fee_status() == 'Partial':
                        students.append(student)
                    elif fee_status == 'unpaid' and student.get_fee_status() == 'Unpaid':
                        students.append(student)
            else:
                students = query.all()
            
            output = export_students_excel(students, fields)
            filename = f'students_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            
        else:
            status = request.form.get('enquiry_status', 'all')
            fields = request.form.getlist('enquiry_fields')
            
            query = Enquiry.query.filter_by(centre_id=current_user.id)
            if status != 'all':
                query = query.filter_by(status=status)
                
            enquiries = query.all()
            output = export_enquiries_excel(enquiries, fields)
            filename = f'enquiries_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    @app.route('/export/pdf', methods=['POST'])
    @login_required
    @subscription_required
    def export_pdf():
        export_type = request.form.get('export_type', 'students')
        
        if request.method == 'POST':
            current_app.logger.info(f"PDF export attempt from {request.remote_addr}")
            current_app.logger.debug(f"Form data: {request.form}")
        
        if export_type == 'students':
            fee_status = request.form.get('fee_status', 'all')
            fields = request.form.getlist('student_fields')
            
            query = Student.query.filter_by(centre_id=current_user.id)
            
            if fee_status != 'all':
                students_temp = query.all()
                students = []
                for student in students_temp:
                    if fee_status == 'paid' and student.get_fee_status() == 'Paid':
                        students.append(student)
                    elif fee_status == 'partial' and student.get_fee_status() == 'Partial':
                        students.append(student)
                    elif fee_status == 'unpaid' and student.get_fee_status() == 'Unpaid':
                        students.append(student)
            else:
                students = query.all()
            
            output = export_students_pdf(students, fields, current_user.name)
            filename = f'students_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            
        else:
            status = request.form.get('enquiry_status', 'all')
            fields = request.form.getlist('enquiry_fields')
            
            query = Enquiry.query.filter_by(centre_id=current_user.id)
            if status != 'all':
                query = query.filter_by(status=status)
                
            enquiries = query.all()
            output = export_enquiries_pdf(enquiries, fields, current_user.name)
            filename = f'enquiries_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    
    @app.route('/subscription/plans')
    @login_required
    def subscription_plans():
        return render_template('subscription/plans.html')

    @app.route('/subscription/payment')
    @login_required
    def subscription_payment():
        import razorpay
        
        plan = request.args.get('plan', 'monthly')
        
        try:
            # Always use live keys in production
            razorpay_key = os.environ.get('RAZORPAY_KEY_ID')
            razorpay_secret = os.environ.get('RAZORPAY_KEY_SECRET')
            client = razorpay.Client(auth=(razorpay_key, razorpay_secret))
            
            plans = {
                'monthly': {
                    'id': 'plan_QiyHYDfCNwOii0',
                    'amount': 69900,
                    'duration': 'Monthly',
                    'name': 'Monthly Plan',
                    'display_name': 'Monthly Plan',
                    'amount_display': '699.00'
                },
                'yearly': {
                    'id': 'plan_QiyHxYGHqd3KLz',
                    'amount': 699900,
                    'duration': 'Yearly',
                    'name': 'Yearly Plan',
                    'display_name': 'Yearly Plan',
                    'amount_display': '6,999.00'
                }
            }
            
            if plan not in plans:
                flash('Invalid subscription plan selected', 'error')
                return redirect(url_for('subscription_plans'))
            
            subscription = client.subscription.create({
                'plan_id': plans[plan]['id'],
                'customer_notify': 1,
                'quantity': 1,
                'total_count': 12 if plan == 'monthly' else 1,
                'notes': {
                    'centre_id': current_user.id,
                    'centre_name': current_user.name,
                    'plan_type': plan,
                    'plan_duration': plans[plan]['duration']
                }
            })

            current_app.logger.info(f"Created subscription {subscription['id']} for user {current_user.id}")
            return render_template('subscription/payment.html',
                                subscription=subscription,
                                plan=plans[plan],
                                plan_type=plan,
                                razorpay_key=razorpay_key,
                                current_user=current_user)
            
        except Exception as e:
            current_app.logger.error(f"Error creating subscription: {str(e)}", exc_info=True)
            flash('Error processing subscription. Please try again.', 'error')
            return redirect(url_for('subscription_plans'))


    @app.route('/subscription/webhook', methods=['POST'])
    def handle_webhook():
        import razorpay
        current_app.logger.info("Webhook received")
        
        # Verify Razorpay signature
        webhook_secret = os.getenv('RAZORPAY_WEBHOOK_SECRET')
        received_sign = request.headers.get('X-Razorpay-Signature')
        
        try:
            client = razorpay.Client(auth=(os.getenv('RAZORPAY_KEY_ID'), os.getenv('RAZORPAY_KEY_SECRET')))
            client.utility.verify_webhook_signature(
                request.data.decode('utf-8'),
                received_sign,
                webhook_secret
            )
            
            payload = request.get_json()
            event = payload['event']
            current_app.logger.info(f"Processing webhook event: {event}")
            
            # Handle different subscription events
            if event in ['subscription.activated', 'subscription.charged', 'payment.captured']:
                subscription_data = payload['payload']['subscription']['entity'] if 'subscription' in payload['payload'] else None
                payment_data = payload['payload']['payment']['entity'] if 'payment' in payload['payload'] else None
                
                if not subscription_data and payment_data:
                    # Handle direct payments (non-subscription)
                    current_app.logger.info("Processing direct payment")
                    notes = payment_data.get('notes', {})
                    centre_id = notes.get('centre_id')
                    plan_type = notes.get('plan_type', 'monthly')
                    
                    if not centre_id:
                        current_app.logger.error("No centre_id found in payment notes")
                        return jsonify({"status": "error", "message": "Missing centre_id"}), 400
                    
                    # Update centre subscription
                    centre = Centre.query.get(centre_id)
                    if not centre:
                        current_app.logger.error(f"Centre not found: {centre_id}")
                        return jsonify({"status": "error", "message": "Centre not found"}), 404
                    
                    if plan_type == 'yearly':
                        centre.subscription_type = 'yearly'
                        centre.subscription_end_date = datetime.utcnow() + timedelta(days=365)
                    else:
                        centre.subscription_type = 'monthly'
                        centre.subscription_end_date = datetime.utcnow() + timedelta(days=30)
                    
                    # Create payment record
                    payment = SubscriptionPayment(
                        amount=payment_data['amount'] / 100,
                        payment_id=payment_data['id'],
                        subscription_id=None,
                        plan_type=plan_type,
                        centre_id=centre_id,
                        status='completed',
                        notes=f"Direct payment via webhook: {event}"
                    )
                    db.session.add(payment)
                    db.session.commit()
                    current_app.logger.info(f"Processed direct payment {payment_data['id']}")
                    return jsonify({"status": "success"}), 200
                
                if not subscription_data:
                    current_app.logger.error("No subscription data in webhook payload")
                    return jsonify({"status": "error", "message": "Missing subscription data"}), 400
                
                # Extract relevant data
                subscription_id = subscription_data['id']
                plan_id = subscription_data['plan_id']
                notes = subscription_data.get('notes', {})
                centre_id = notes.get('centre_id')
                
                if not centre_id:
                    current_app.logger.error("No centre_id found in subscription notes")
                    return jsonify({"status": "error", "message": "Missing centre_id"}), 400
                
                # Find or create subscription record
                subscription = SubscriptionPayment.query.filter_by(
                    subscription_id=subscription_id
                ).first()
                
                if not subscription:
                    # New subscription
                    centre = Centre.query.get(centre_id)
                    if not centre:
                        current_app.logger.error(f"Centre not found: {centre_id}")
                        return jsonify({"status": "error", "message": "Centre not found"}), 404
                    
                    # Determine plan type
                    if plan_id == 'plan_QiyHxYGHqd3KLz':  # Yearly plan
                        plan_type = 'yearly'
                        amount = 6999.00
                        end_date = datetime.utcnow() + timedelta(days=365)
                    else:  # Default to monthly
                        plan_type = 'monthly'
                        amount = 699.00
                        end_date = datetime.utcnow() + timedelta(days=30)
                    
                    # Update centre subscription
                    centre.subscription_type = plan_type
                    centre.subscription_end_date = end_date
                    
                    # Create subscription record
                    subscription = SubscriptionPayment(
                        amount=amount,
                        payment_id=payment_data['id'] if payment_data else None,
                        subscription_id=subscription_id,
                        plan_type=plan_type,
                        centre_id=centre_id,
                        status='active' if event == 'subscription.activated' else 'completed',
                        notes=f"Webhook: {event}"
                    )
                    db.session.add(subscription)
                    
                elif payment_data and not SubscriptionPayment.query.filter_by(payment_id=payment_data['id']).first():
                    # Additional payment for existing subscription
                    payment = SubscriptionPayment(
                        amount=payment_data['amount'] / 100,
                        payment_id=payment_data['id'],
                        subscription_id=subscription_id,
                        plan_type=subscription.plan_type,
                        centre_id=centre_id,
                        status='completed',
                        notes=f"Recurring payment via webhook"
                    )
                    db.session.add(payment)
                    
                    # Update subscription end date
                    centre = Centre.query.get(centre_id)
                    if subscription.plan_type == 'yearly':
                        centre.subscription_end_date = datetime.utcnow() + timedelta(days=365)
                    else:
                        centre.subscription_end_date = datetime.utcnow() + timedelta(days=30)
                
                db.session.commit()
                current_app.logger.info(f"Processed {event} for subscription {subscription_id}")
                
            elif event == 'subscription.cancelled':
                subscription_data = payload['payload']['subscription']['entity']
                subscription_id = subscription_data['id']
                
                # Update subscription status
                subscription = SubscriptionPayment.query.filter_by(subscription_id=subscription_id).first()
                if subscription:
                    subscription.status = 'cancelled'
                    db.session.commit()
                    current_app.logger.info(f"Marked subscription {subscription_id} as cancelled")
            
            return jsonify({"status": "success"}), 200
        
        except Exception as e:
            current_app.logger.error(f"Webhook processing failed: {str(e)}", exc_info=True)
            return jsonify({"status": "error", "message": str(e)}), 400
        

    @app.route('/subscription/success')
    @login_required
    def subscription_success():
        payment_id = request.args.get('razorpay_payment_id')
        subscription_id = request.args.get('razorpay_subscription_id')
        plan = request.args.get('plan', 'monthly')
        
        try:
            if payment_id and subscription_id:
                if plan == 'yearly':
                    current_user.subscription_type = 'yearly'
                    current_user.subscription_end_date = datetime.utcnow() + timedelta(days=365)
                    amount = 6999.00
                else:
                    current_user.subscription_type = 'monthly'
                    current_user.subscription_end_date = datetime.utcnow() + timedelta(days=30)
                    amount = 699.00
                
                # Check if this payment already exists
                existing_payment = SubscriptionPayment.query.filter_by(payment_id=payment_id).first()
                if not existing_payment:
                    payment = SubscriptionPayment(
                        amount=amount,
                        payment_id=payment_id,
                        subscription_id=subscription_id,
                        plan_type=plan,
                        centre_id=current_user.id,
                        status='completed',
                        notes='Payment successful via checkout'
                    )
                    db.session.add(payment)
                    db.session.commit()
                    current_app.logger.info(f"Created payment record for {current_user.id}")
                
                flash('Subscription activated successfully!', 'success')
                return render_template('subscription/success.html')
            else:
                flash('Payment information missing', 'error')
                return redirect(url_for('subscription_plans'))
        
        except Exception as e:
            current_app.logger.error(f"Error processing success callback: {str(e)}", exc_info=True)
            db.session.rollback()
            flash('Error processing your subscription. Please contact support.', 'error')
            return redirect(url_for('subscription_plans'))

    @app.route('/subscription/failed')
    @login_required
    def subscription_failed():
        flash('Subscription payment failed. Please try again.', 'error')
        return render_template('subscription/failed.html')