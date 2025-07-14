import os
from datetime import datetime, timedelta, date
from flask import render_template, redirect, url_for, flash, request, send_file, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, or_
from app import db
from models import Centre, Student, Enquiry, Course, Scheme, FeePayment, SubscriptionPayment
from forms import (LoginForm, RegisterForm, StudentForm, EnquiryForm, CourseForm, 
                  SchemeForm, FeePaymentForm, LogoUploadForm)
from utils import (generate_enrollment_number, save_logo, export_students_excel, 
                  export_students_pdf, calculate_net_fees)
from middleware import subscription_required

def register_routes(app):
    
    # Auth Routes
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('auth_login'))
    
    @app.route('/login', methods=['GET', 'POST'])
    def auth_login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = LoginForm()
        if form.validate_on_submit():
            centre = Centre.query.filter_by(email=form.email.data).first()
            if centre and check_password_hash(centre.password_hash, form.password.data):
                login_user(centre, remember=form.remember_me.data)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            flash('Invalid email or password', 'error')
        
        return render_template('auth/login.html', form=form)
    
    @app.route('/register', methods=['GET', 'POST'])
    def auth_register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = RegisterForm()
        if form.validate_on_submit():
            # Check if email already exists
            existing_centre = Centre.query.filter_by(email=form.email.data).first()
            if existing_centre:
                flash('Email already registered', 'error')
                return render_template('auth/register.html', form=form)
            
            centre = Centre(
                name=form.name.data,
                email=form.email.data,
                password_hash=generate_password_hash(form.password.data),
                phone=form.phone.data,
                address=form.address.data,
                city=form.city.data,
                pincode=form.pincode.data,
                subscription_type='trial'
            )
            
            db.session.add(centre)
            db.session.commit()
            
            login_user(centre)
            flash('Registration successful! You have 14 days free trial.', 'success')
            return redirect(url_for('dashboard'))
        
        return render_template('auth/register.html', form=form)
    
    @app.route('/logout')
    def auth_logout():
        logout_user()
        return redirect(url_for('auth_login'))
    
    # Dashboard
    @app.route('/dashboard')
    @login_required
    @subscription_required
    def dashboard():
        # Get statistics
        total_students = Student.query.filter_by(centre_id=current_user.id).count()
        total_enquiries = Enquiry.query.filter_by(centre_id=current_user.id, status='active').count()
        
        # Fee statistics
        paid_students = Student.query.filter_by(centre_id=current_user.id).all()
        total_fees_collected = sum(student.get_total_paid() for student in paid_students)
        pending_fees = sum(student.get_balance_fees() for student in paid_students)
        
        # Fee status counts
        fully_paid = sum(1 for student in paid_students if student.get_fee_status() == 'Paid')
        partially_paid = sum(1 for student in paid_students if student.get_fee_status() == 'Partial')
        unpaid = sum(1 for student in paid_students if student.get_fee_status() == 'Unpaid')
        
        # Recent students
        recent_students = Student.query.filter_by(centre_id=current_user.id)\
                                     .order_by(Student.created_at.desc()).limit(5).all()
        
        # Recent enquiries
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
    
    # Students Routes
    @app.route('/students')
    @login_required
    @subscription_required
    def students_list():
        page = request.args.get('page', 1, type=int)
        fee_status = request.args.get('fee_status', 'all')
        search = request.args.get('search', '')
        
        query = Student.query.filter_by(centre_id=current_user.id)
        
        # Apply search filter
        if search:
            query = query.filter(or_(
                Student.name.ilike(f'%{search}%'),
                Student.enrollment_number.ilike(f'%{search}%'),
                Student.mobile1.ilike(f'%{search}%')
            ))
        
        # Apply fee status filter
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
            
            # Manual pagination for filtered results
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
        
        return render_template('students/list.html', students=students, 
                             fee_status=fee_status, search=search)
    
    @app.route('/students/add', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def students_add():
        form = StudentForm()
        
        # Populate course choices
        courses = Course.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.course_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in courses]
        
        # Populate scheme choices
        schemes = Scheme.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.scheme_id.choices = [(0, 'Select Scheme')] + [(s.id, s.name) for s in schemes]
        
        if form.validate_on_submit():
            # Generate enrollment number if not provided
            enrollment_number = form.enrollment_number.data or generate_enrollment_number()
            
            # Check if enrollment number already exists
            existing_student = Student.query.filter_by(
                centre_id=current_user.id, 
                enrollment_number=enrollment_number
            ).first()
            
            if existing_student:
                flash('Enrollment number already exists', 'error')
                return render_template('students/add.html', form=form)
            
            # Calculate net fees
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
                scheme_id=form.scheme_id.data if form.scheme_id.data != 0 else None
            )
            
            db.session.add(student)
            db.session.commit()
            
            flash('Student added successfully', 'success')
            return redirect(url_for('students_list'))
        
        return render_template('students/add.html', form=form)
    
    @app.route('/students/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def students_edit(id):
        student = Student.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        form = StudentForm(obj=student)
        
        # Populate course choices
        courses = Course.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.course_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in courses]
        
        # Populate scheme choices
        schemes = Scheme.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.scheme_id.choices = [(0, 'Select Scheme')] + [(s.id, s.name) for s in schemes]
        
        if form.validate_on_submit():
            # Check if enrollment number already exists (excluding current student)
            existing_student = Student.query.filter(
                Student.centre_id == current_user.id,
                Student.enrollment_number == form.enrollment_number.data,
                Student.id != student.id
            ).first()
            
            if existing_student:
                flash('Enrollment number already exists', 'error')
                return render_template('students/edit.html', form=form, student=student)
            
            # Calculate net fees
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
    
    # Fee Payment Routes
    @app.route('/students/<int:id>/pay-fees', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def pay_fees(id):
        student = Student.query.filter_by(id=id, centre_id=current_user.id).first_or_404()
        form = FeePaymentForm()
        
        if form.validate_on_submit():
            # Check if payment amount doesn't exceed balance
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
    
    # Enquiry Routes
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
        
        # Populate course choices
        courses = Course.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.course_interested_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in courses]
        
        # Populate scheme choices
        schemes = Scheme.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.scheme_id.choices = [(0, 'Select Scheme')] + [(s.id, s.name) for s in schemes]
        
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
        
        # Populate course choices
        courses = Course.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.course_interested_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in courses]
        
        # Populate scheme choices
        schemes = Scheme.query.filter_by(centre_id=current_user.id, is_active=True).all()
        form.scheme_id.choices = [(0, 'Select Scheme')] + [(s.id, s.name) for s in schemes]
        
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
        
        # Create new student from enquiry
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
            total_fees=0,  # Will need to be updated manually
            net_fees=0,
            centre_id=current_user.id,
            course_id=enquiry.course_interested_id,
            scheme_id=enquiry.scheme_id
        )
        
        # Mark enquiry as converted
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
    
    # Course Routes
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
        
        # Check if course has students
        if course.students:
            flash('Cannot delete course as it has enrolled students', 'error')
            return redirect(url_for('courses_list'))
            
        db.session.delete(course)
        db.session.commit()
        flash('Course deleted successfully', 'success')
        return redirect(url_for('courses_list'))
    
    # Scheme Routes
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
        
        # Check if scheme has students
        if scheme.students:
            flash('Cannot delete scheme as it has enrolled students', 'error')
            return redirect(url_for('schemes_list'))
            
        db.session.delete(scheme)
        db.session.commit()
        flash('Scheme deleted successfully', 'success')
        return redirect(url_for('schemes_list'))
    
    # Export Routes
    @app.route('/export/options')
    @login_required
    @subscription_required
    def export_options():
        return render_template('exports/options.html')
    
    @app.route('/export/excel', methods=['POST'])
    @login_required
    @subscription_required
    def export_excel():
        fields = request.form.getlist('fields')
        fee_status = request.form.get('fee_status', 'all')
        
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
        
        return send_file(
            output,
            as_attachment=True,
            download_name=f'students_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    @app.route('/export/pdf', methods=['POST'])
    @login_required
    @subscription_required
    def export_pdf():
        fields = request.form.getlist('fields')
        fee_status = request.form.get('fee_status', 'all')
        
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
        
        return send_file(
            output,
            as_attachment=True,
            download_name=f'students_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
    
    # Subscription Routes
    @app.route('/subscription/plans')
    @login_required
    def subscription_plans():
        return render_template('subscription/plans.html')
    
    @app.route('/subscription/payment')
    @login_required
    def subscription_payment():
        import razorpay
        
        plan = request.args.get('plan', 'monthly')
        
        # Razorpay plan IDs and amounts
        if plan == 'monthly':
            plan_id = 'plan_QiyHYDfCNwOii0'
            amount = 69900  # ₹699 in paise
        else:
            plan_id = 'plan_QiyHxYGHqd3KLz'
            amount = 699900  # ₹6999 in paise
        
        # Initialize Razorpay client
        client = razorpay.Client(auth=(os.environ.get('RAZORPAY_KEY_ID'), os.environ.get('RAZORPAY_KEY_SECRET')))
        
        # Create subscription
        try:
            subscription = client.subscription.create({
                'plan_id': plan_id,
                'customer_notify': 1,
                'quantity': 1,
                'total_count': 120 if plan == 'monthly' else 10,  # 10 years for yearly, 10 years for monthly
                'notes': {
                    'centre_id': current_user.id,
                    'centre_name': current_user.name,
                    'plan_type': plan
                }
            })
            
            return render_template('subscription/payment.html', 
                                 plan=plan, 
                                 amount=amount//100,  # Convert back to rupees for display
                                 subscription_id=subscription['id'],
                                 razorpay_key=os.environ.get('RAZORPAY_KEY_ID'))
        except Exception as e:
            flash(f'Error creating subscription: {str(e)}', 'error')
            return redirect(url_for('subscription_plans'))
    
    @app.route('/subscription/webhook', methods=['POST'])
    def subscription_webhook():
        import razorpay
        
        # Verify webhook signature
        client = razorpay.Client(auth=(os.environ.get('RAZORPAY_KEY_ID'), os.environ.get('RAZORPAY_KEY_SECRET')))
        
        try:
            # Get webhook data
            webhook_body = request.get_data(as_text=True)
            webhook_signature = request.headers.get('X-Razorpay-Signature')
            
            # Verify webhook signature (optional but recommended)
            # client.utility.verify_webhook_signature(webhook_body, webhook_signature, webhook_secret)
            
            # Parse webhook data
            webhook_data = request.get_json()
            event = webhook_data.get('event')
            
            if event == 'subscription.charged':
                payment_data = webhook_data.get('payload', {}).get('payment', {}).get('entity', {})
                subscription_data = webhook_data.get('payload', {}).get('subscription', {}).get('entity', {})
                
                # Extract centre_id from notes
                centre_id = subscription_data.get('notes', {}).get('centre_id')
                plan_type = subscription_data.get('notes', {}).get('plan_type')
                
                if centre_id:
                    centre = Centre.query.get(int(centre_id))
                    if centre:
                        # Update subscription
                        centre.subscription_type = plan_type
                        centre.subscription_start_date = datetime.utcnow()
                        centre.razorpay_subscription_id = subscription_data.get('id')
                        
                        if plan_type == 'monthly':
                            centre.subscription_end_date = datetime.utcnow() + timedelta(days=30)
                        else:
                            centre.subscription_end_date = datetime.utcnow() + timedelta(days=365)
                        
                        # Record payment
                        payment_record = SubscriptionPayment(
                            centre_id=centre.id,
                            amount=payment_data.get('amount', 0) / 100,  # Convert from paise
                            plan_type=plan_type,
                            razorpay_payment_id=payment_data.get('id'),
                            status='completed'
                        )
                        
                        db.session.add(payment_record)
                        db.session.commit()
            
            return {'status': 'success'}, 200
            
        except Exception as e:
            print(f"Webhook error: {str(e)}")
            return {'status': 'error', 'message': str(e)}, 400
    
    @app.route('/subscription/success')
    @login_required
    def subscription_success():
        subscription_id = request.args.get('subscription_id')
        plan = request.args.get('plan', 'monthly')
        
        # Note: Actual subscription activation happens via webhook
        # This is just for user feedback
        flash('Payment initiated successfully! Your subscription will be activated shortly.', 'success')
        return render_template('subscription/success.html', plan=plan)
    
    # Settings Routes
    @app.route('/settings/logo', methods=['GET', 'POST'])
    @login_required
    @subscription_required
    def settings_logo():
        form = LogoUploadForm()
        
        if form.validate_on_submit():
            if form.logo.data:
                logo_filename = save_logo(form.logo.data, current_user.id)
                current_user.logo_filename = logo_filename
                db.session.commit()
                flash('Logo uploaded successfully', 'success')
                return redirect(url_for('settings_logo'))
        
        return render_template('settings/logo.html', form=form)
    
    @app.route('/settings/invoices')
    @login_required
    def settings_invoices():
        """View subscription invoices"""
        invoices = SubscriptionPayment.query.filter_by(
            centre_id=current_user.id,
            status='completed'
        ).order_by(SubscriptionPayment.payment_date.desc()).all()
        
        return render_template('settings/invoices.html', invoices=invoices)
    
    @app.route('/settings/invoices/<int:invoice_id>/download')
    @login_required
    def download_invoice(invoice_id):
        """Download invoice PDF"""
        invoice = SubscriptionPayment.query.filter_by(
            id=invoice_id,
            centre_id=current_user.id,
            status='completed'
        ).first_or_404()
        
        try:
            from utils import generate_invoice_pdf
            pdf_file, invoice_number = generate_invoice_pdf(invoice)
            
            return send_file(
                pdf_file,
                as_attachment=True,
                download_name=f'{invoice_number}.pdf',
                mimetype='application/pdf'
            )
        except Exception as e:
            flash(f'Error generating invoice: {str(e)}', 'error')
            return redirect(url_for('settings_invoices'))
