"""
Student Management Routes
"""
import csv
import io
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app import db
from app.models import Student, Batch, User, FeeTransaction
from app.utils.decorators import staff_required
from app.utils.helpers import paginate_query, parse_date, save_uploaded_file

student_bp = Blueprint('student', __name__, url_prefix='/students')


def get_fee_status(student):
    """Calculate fee status for a student (days left or overdue)"""
    # Get last payment date
    last_payment = FeeTransaction.query.filter_by(
        student_id=student.id
    ).order_by(FeeTransaction.payment_date.desc()).first()
    
    if last_payment:
        # Calculate days since last payment
        last_date = last_payment.payment_date
    else:
        # Use enrollment date if no payment
        last_date = student.enrollment_date or student.created_at.date()
    
    today = date.today()
    days_since = (today - last_date).days
    days_left = 30 - days_since
    
    return {
        'days_left': days_left,
        'is_overdue': days_left < 0,
        'overdue_days': abs(days_left) if days_left < 0 else 0,
        'last_payment_date': last_date
    }


@student_bp.route('/')
@login_required
@staff_required
def list_students():
    """List all students with search and filter"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    batch_id = request.args.get('batch', type=int)
    status = request.args.get('status', '').strip()  # Default to empty for 'All Status'
    
    query = Student.query
    
    # Apply filters
    if search:
        query = query.filter(
            db.or_(
                Student.first_name.ilike(f'%{search}%'),
                Student.last_name.ilike(f'%{search}%'),
                Student.student_id.ilike(f'%{search}%'),
                Student.phone.ilike(f'%{search}%')
            )
        )
    
    if batch_id:
        query = query.filter(Student.batch_id == batch_id)
    
    if status:
        query = query.filter(Student.status == status)
    
    query = query.order_by(Student.created_at.desc())
    students = paginate_query(query, page)
    
    # Calculate fee status for each student
    fee_statuses = {}
    for student in students.items:
        fee_statuses[student.id] = get_fee_status(student)
    
    batches = Batch.query.filter_by(is_active=True).all()
    
    return render_template('student/list.html',
        students=students,
        batches=batches,
        search=search,
        selected_batch=batch_id,
        selected_status=status,
        fee_statuses=fee_statuses
    )


@student_bp.route('/bulk-move', methods=['POST'])
@login_required
@staff_required
def bulk_move_batch():
    """Move multiple students to a different batch"""
    student_ids = request.form.getlist('student_ids')
    target_batch_id = request.form.get('target_batch_id', type=int)
    
    if not student_ids:
        flash('No students selected.', 'warning')
        return redirect(url_for('student.list_students'))
    
    if not target_batch_id:
        flash('Please select a target batch.', 'warning')
        return redirect(url_for('student.list_students'))
    
    target_batch = Batch.query.get_or_404(target_batch_id)
    
    # Update all selected students
    moved_count = 0
    for student_id in student_ids:
        student = Student.query.get(int(student_id))
        if student:
            student.batch_id = target_batch_id
            moved_count += 1
    
    db.session.commit()
    flash(f'Successfully moved {moved_count} student(s) to {target_batch.name}.', 'success')
    return redirect(url_for('student.list_students'))


@student_bp.route('/bulk-delete', methods=['POST'])
@login_required
@staff_required
def bulk_delete():
    """Permanently delete multiple selected students"""
    student_ids = request.form.getlist('student_ids')
    
    if not student_ids:
        flash('No students selected.', 'warning')
        return redirect(url_for('student.list_students'))
    
    deleted_count = 0
    errors = []
    
    for student_id in student_ids:
        try:
            student = Student.query.get(int(student_id))
            if student:
                # Delete associated user account if exists
                if student.user:
                    db.session.delete(student.user)
                # Delete student (cascade will handle attendances, transactions, dues)
                db.session.delete(student)
                deleted_count += 1
        except Exception as e:
            errors.append(f"Error deleting student {student_id}: {str(e)}")
    
    db.session.commit()
    
    if deleted_count > 0:
        flash(f'Successfully deleted {deleted_count} student(s).', 'success')
    if errors:
        for error in errors:
            flash(error, 'danger')
    
    return redirect(url_for('student.list_students'))

@student_bp.route('/add', methods=['GET', 'POST'])
@login_required
@staff_required
def add_student():
    """Add new student with auto-generated login credentials"""
    if request.method == 'POST':
        try:
            # Get phone and validate (mandatory)
            phone = request.form.get('phone', '').strip()
            if not phone or len(phone) < 5:
                flash('Phone number is required and must be at least 5 digits.', 'warning')
                return redirect(request.url)
            
            first_name = request.form.get('first_name', '').strip().lower()
            
            # Generate student ID
            student_id = Student.generate_student_id()
            
            # Generate login credentials
            # Username: firstname + last 2 digits of phone + @sga
            # Password: firstname + @ + last 5 digits of phone
            phone_digits = ''.join(filter(str.isdigit, phone))
            username = f"{first_name}{phone_digits[-2:]}@sga"
            password = f"{first_name}@{phone_digits[-5:]}"
            
            # Check if username already exists, make unique if needed
            existing = User.query.filter_by(email=username).first()
            if existing:
                username = f"{first_name}{phone_digits[-3:]}@sga"
            
            # Create User account for student
            user = User(
                username=request.form.get('first_name', '').strip() + ' ' + request.form.get('last_name', '').strip(),
                email=username,  # Using generated username as email for login
                role='STUDENT',
                is_active=True
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()  # Get user ID
            
            # Handle photo upload
            photo_path = None
            if 'photo' in request.files:
                photo = request.files['photo']
                if photo.filename:
                    photo_path = save_uploaded_file(photo, 'students')
            
            # Parse date of birth
            dob = parse_date(request.form.get('date_of_birth'))
            
            # Create student linked to user
            student = Student(
                student_id=student_id,
                first_name=request.form.get('first_name', '').strip(),
                last_name=request.form.get('last_name', '').strip(),
                date_of_birth=dob,
                gender=request.form.get('gender'),
                photo=photo_path,
                email=request.form.get('email', '').strip() or None,
                phone=phone,
                address=request.form.get('address', '').strip() or None,
                city=request.form.get('city', '').strip() or None,
                state=request.form.get('state', '').strip() or None,
                pincode=request.form.get('pincode', '').strip() or None,
                parent_name=request.form.get('parent_name', '').strip() or None,
                parent_phone=request.form.get('parent_phone', '').strip() or None,
                parent_email=request.form.get('parent_email', '').strip() or None,
                parent_occupation=request.form.get('parent_occupation', '').strip() or None,
                batch_id=request.form.get('batch_id', type=int) or None,
                blood_group=request.form.get('blood_group', '').strip() or None,
                medical_conditions=request.form.get('medical_conditions', '').strip() or None,
                previous_school=request.form.get('previous_school', '').strip() or None,
                remarks=request.form.get('remarks', '').strip() or None,
                status='ACTIVE',
                user_id=user.id
            )
            
            db.session.add(student)
            db.session.commit()
            
            # Show success with login credentials
            flash(f'Student {student.full_name} registered! ID: {student.student_id}', 'success')
            flash(f'Login: {username} | Password: {password}', 'info')
            return redirect(url_for('student.view_student', id=student.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error registering student: {str(e)}', 'danger')
    
    batches = Batch.query.filter_by(is_active=True).all()
    return render_template('student/add.html', batches=batches)



@student_bp.route('/<int:id>')
@login_required
def view_student(id):
    """View student profile"""
    student = Student.query.get_or_404(id)
    
    # Get attendance percentage
    attendance_percentage = student.get_attendance_percentage()
    
    # Get total fees paid
    total_fees = student.get_total_fees_paid()
    
    # Get recent attendance
    recent_attendance = student.attendances.order_by(
        db.desc('date')
    ).limit(10).all()
    
    # Get recent transactions
    recent_transactions = student.fee_transactions.order_by(
        db.desc('payment_date')
    ).limit(5).all()
    
    return render_template('student/view.html',
        student=student,
        attendance_percentage=attendance_percentage,
        total_fees=total_fees,
        recent_attendance=recent_attendance,
        recent_transactions=recent_transactions
    )


@student_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_student(id):
    """Edit student profile"""
    student = Student.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Handle photo upload
            if 'photo' in request.files:
                photo = request.files['photo']
                if photo.filename:
                    photo_path = save_uploaded_file(photo, 'students')
                    if photo_path:
                        student.photo = photo_path
            
            # Update fields
            student.first_name = request.form.get('first_name', '').strip()
            student.last_name = request.form.get('last_name', '').strip()
            student.date_of_birth = parse_date(request.form.get('date_of_birth'))
            student.gender = request.form.get('gender')
            student.email = request.form.get('email', '').strip() or None
            student.phone = request.form.get('phone', '').strip() or None
            student.address = request.form.get('address', '').strip() or None
            student.city = request.form.get('city', '').strip() or None
            student.state = request.form.get('state', '').strip() or None
            student.pincode = request.form.get('pincode', '').strip() or None
            student.parent_name = request.form.get('parent_name', '').strip() or None
            student.parent_phone = request.form.get('parent_phone', '').strip() or None
            student.parent_email = request.form.get('parent_email', '').strip() or None
            student.parent_occupation = request.form.get('parent_occupation', '').strip() or None
            student.batch_id = request.form.get('batch_id', type=int) or None
            student.blood_group = request.form.get('blood_group', '').strip() or None
            student.medical_conditions = request.form.get('medical_conditions', '').strip() or None
            student.previous_school = request.form.get('previous_school', '').strip() or None
            student.remarks = request.form.get('remarks', '').strip() or None
            student.status = request.form.get('status', 'ACTIVE')
            
            db.session.commit()
            flash('Student updated successfully!', 'success')
            return redirect(url_for('student.view_student', id=student.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating student: {str(e)}', 'danger')
    
    batches = Batch.query.filter_by(is_active=True).all()
    return render_template('student/edit.html', student=student, batches=batches)


@student_bp.route('/<int:id>/credentials', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_credentials(id):
    """Edit student login credentials"""
    student = Student.query.get_or_404(id)
    
    if not student.user:
        flash('No login account linked to this student.', 'warning')
        return redirect(url_for('student.create_credentials', id=id))
    
    if request.method == 'POST':
        try:
            new_username = request.form.get('username', '').strip()
            new_password = request.form.get('password', '').strip()
            is_active = 'is_active' in request.form
            
            # Update username if changed
            if new_username and new_username != student.user.email:
                # Check if username already exists
                existing = User.query.filter_by(email=new_username).first()
                if existing and existing.id != student.user.id:
                    flash('Username already exists.', 'danger')
                    return render_template('student/credentials.html', student=student)
                student.user.email = new_username
            
            # Update password if provided
            if new_password:
                student.user.set_password(new_password)
                flash(f'Password updated to: {new_password}', 'info')
            
            student.user.is_active = is_active
            db.session.commit()
            
            flash('Credentials updated successfully!', 'success')
            return redirect(url_for('student.view_student', id=student.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating credentials: {str(e)}', 'danger')
    
    return render_template('student/credentials.html', student=student)


@student_bp.route('/<int:id>/credentials/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create_credentials(id):
    """Create login for existing student without credentials"""
    student = Student.query.get_or_404(id)
    
    if student.user:
        flash('Student already has login credentials.', 'info')
        return redirect(url_for('student.edit_credentials', id=id))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            if not username or not password:
                flash('Username and password are required.', 'warning')
                return render_template('student/create_credentials.html', student=student)
            
            # Check if username exists
            if User.query.filter_by(email=username).first():
                flash('Username already exists.', 'danger')
                return render_template('student/create_credentials.html', student=student)
            
            # Create user account
            user = User(
                username=student.full_name,
                email=username,
                role='STUDENT',
                is_active=True
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            
            # Link to student
            student.user_id = user.id
            db.session.commit()
            
            flash(f'Login created! Username: {username} | Password: {password}', 'success')
            return redirect(url_for('student.view_student', id=student.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating credentials: {str(e)}', 'danger')
    
    # Generate suggested credentials
    phone_digits = ''.join(filter(str.isdigit, student.phone or '00000'))
    first_name = student.first_name.lower()
    suggested_username = f"{first_name}{phone_digits[-2:]}@sga"
    suggested_password = f"{first_name}@{phone_digits[-5:]}"
    
    return render_template('student/create_credentials.html', 
        student=student,
        suggested_username=suggested_username,
        suggested_password=suggested_password
    )


@student_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@staff_required
def delete_student(id):
    """Permanently delete student and associated user account"""
    student = Student.query.get_or_404(id)
    student_name = student.full_name
    
    try:
        # Delete associated user account if exists
        if student.user:
            db.session.delete(student.user)
        
        # Delete student record
        db.session.delete(student)
        db.session.commit()
        
        flash(f'Student {student_name} has been permanently deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting student: {str(e)}', 'danger')
    
    return redirect(url_for('student.list_students'))


@student_bp.route('/<int:id>/deactivate', methods=['POST'])
@login_required
@staff_required
def deactivate_student(id):
    """Deactivate a student (soft delete)"""
    student = Student.query.get_or_404(id)
    student.status = 'INACTIVE'
    db.session.commit()
    flash(f'Student {student.full_name} has been deactivated.', 'info')
    return redirect(url_for('student.list_students'))


@student_bp.route('/<int:id>/activate', methods=['POST'])
@login_required
@staff_required
def activate_student(id):
    """Activate a student"""
    student = Student.query.get_or_404(id)
    student.status = 'ACTIVE'
    db.session.commit()
    flash(f'Student {student.full_name} has been activated.', 'success')
    return redirect(url_for('student.list_students'))


@student_bp.route('/import', methods=['GET', 'POST'])
@login_required
@staff_required
def import_students():
    """Import students from CSV"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'warning')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'warning')
            return redirect(request.url)
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file.', 'warning')
            return redirect(request.url)
        
        try:
            # Read CSV
            stream = io.StringIO(file.stream.read().decode('utf-8'))
            reader = csv.DictReader(stream)
            
            batch_id = request.form.get('batch_id', type=int)
            imported = 0
            errors = []
            
            for row in reader:
                try:
                    student = Student(
                        student_id=Student.generate_student_id(),
                        first_name=row.get('first_name', '').strip(),
                        last_name=row.get('last_name', '').strip(),
                        email=row.get('email', '').strip() or None,
                        phone=row.get('phone', '').strip() or None,
                        parent_name=row.get('parent_name', '').strip() or None,
                        parent_phone=row.get('parent_phone', '').strip() or None,
                        batch_id=batch_id,
                        status='ACTIVE'
                    )
                    db.session.add(student)
                    imported += 1
                except Exception as e:
                    errors.append(f"Row error: {str(e)}")
            
            db.session.commit()
            flash(f'Successfully imported {imported} students.', 'success')
            
            if errors:
                flash(f'{len(errors)} rows had errors.', 'warning')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error importing file: {str(e)}', 'danger')
        
        return redirect(url_for('student.list_students'))
    
    batches = Batch.query.filter_by(is_active=True).all()
    return render_template('student/import.html', batches=batches)


# Batch Management Routes
@student_bp.route('/batches')
@login_required
@staff_required
def list_batches():
    """List all batches"""
    batches = Batch.query.order_by(Batch.class_name, Batch.name).all()
    return render_template('student/batches.html', batches=batches)


@student_bp.route('/batches/add', methods=['GET', 'POST'])
@login_required
@staff_required
def add_batch():
    """Add new batch"""
    if request.method == 'POST':
        try:
            batch = Batch(
                name=request.form.get('name', '').strip(),
                class_name=request.form.get('class_name', '').strip(),
                capacity=request.form.get('capacity', 30, type=int),
                teacher_id=request.form.get('teacher_id', type=int) or None,
                description=request.form.get('description', '').strip() or None,
                is_active=True
            )
            db.session.add(batch)
            db.session.commit()
            
            flash(f'Batch {batch.name} created successfully!', 'success')
            return redirect(url_for('student.list_batches'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating batch: {str(e)}', 'danger')
    
    teachers = User.query.filter_by(role='TEACHER', is_active=True).all()
    return render_template('student/add_batch.html', teachers=teachers)


@student_bp.route('/batches/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_batch(id):
    """Edit batch"""
    batch = Batch.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            batch.name = request.form.get('name', '').strip()
            batch.class_name = request.form.get('class_name', '').strip()
            batch.capacity = request.form.get('capacity', 30, type=int)
            batch.teacher_id = request.form.get('teacher_id', type=int) or None
            batch.description = request.form.get('description', '').strip() or None
            batch.is_active = 'is_active' in request.form
            
            db.session.commit()
            flash('Batch updated successfully!', 'success')
            return redirect(url_for('student.list_batches'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating batch: {str(e)}', 'danger')
    
    teachers = User.query.filter_by(role='TEACHER', is_active=True).all()
    return render_template('student/edit_batch.html', batch=batch, teachers=teachers)


@student_bp.route('/batches/<int:id>/delete', methods=['POST'])
@login_required
@staff_required
def delete_batch(id):
    """Delete batch"""
    batch = Batch.query.get_or_404(id)
    batch_name = batch.name
    
    try:
        # Check if there are students in this batch
        student_count = batch.student_count
        
        if student_count > 0:
            flash(f'Cannot delete "{batch_name}" - it has {student_count} student(s). Move students to another batch first.', 'warning')
            return redirect(url_for('student.list_batches'))
        
        # Check for fee structures linked to this batch
        from app.models import FeeStructure
        fee_structures = FeeStructure.query.filter_by(batch_id=id).count()
        if fee_structures > 0:
            flash(f'Cannot delete "{batch_name}" - it has {fee_structures} fee structure(s) linked. Delete those first.', 'warning')
            return redirect(url_for('student.list_batches'))
        
        db.session.delete(batch)
        db.session.commit()
        flash(f'Batch "{batch_name}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting batch: {str(e)}', 'danger')
    
    return redirect(url_for('student.list_batches'))


# API endpoints for AJAX
@student_bp.route('/api/search')
@login_required
def api_search_students():
    """API endpoint for student search (autocomplete)"""
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify([])
    
    students = Student.query.filter(
        db.or_(
            Student.first_name.ilike(f'%{query}%'),
            Student.last_name.ilike(f'%{query}%'),
            Student.student_id.ilike(f'%{query}%')
        ),
        Student.status == 'ACTIVE'
    ).limit(10).all()
    
    return jsonify([{
        'id': s.id,
        'student_id': s.student_id,
        'name': s.full_name,
        'batch': s.batch.name if s.batch else 'No Batch'
    } for s in students])
