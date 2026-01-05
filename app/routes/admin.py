"""
Admin Dashboard Routes
"""
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.models import User, Student, Batch, Attendance, FeeTransaction
from app.utils.decorators import admin_required, staff_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Admin dashboard with statistics"""
    # Get statistics
    total_students = Student.query.filter_by(status='ACTIVE').count()
    total_batches = Batch.query.filter_by(is_active=True).count()
    total_teachers = User.query.filter_by(role='TEACHER', is_active=True).count()
    
    # Today's attendance
    today = date.today()
    today_attendance = Attendance.query.filter_by(date=today).count()
    today_present = Attendance.query.filter_by(date=today, status='PRESENT').count()
    
    # This month's fee collection
    first_day = date(today.year, today.month, 1)
    monthly_collection = db.session.query(func.sum(FeeTransaction.amount)).filter(
        FeeTransaction.payment_date >= first_day,
        FeeTransaction.payment_date <= today
    ).scalar() or 0
    
    # Recent enrollments (last 7 days)
    week_ago = today - timedelta(days=7)
    recent_enrollments = Student.query.filter(
        Student.enrollment_date >= week_ago
    ).order_by(Student.created_at.desc()).limit(5).all()
    
    # Recent fee transactions
    recent_transactions = FeeTransaction.query.order_by(
        FeeTransaction.created_at.desc()
    ).limit(5).all()
    
    # Batch-wise student count
    batch_stats = db.session.query(
        Batch.name,
        func.count(Student.id).label('count')
    ).outerjoin(Student, (Student.batch_id == Batch.id) & (Student.status == 'ACTIVE')
    ).filter(Batch.is_active == True
    ).group_by(Batch.id).all()
    
    # Attendance trend (last 7 days)
    attendance_trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        present = Attendance.query.filter_by(date=day, status='PRESENT').count()
        total = Attendance.query.filter_by(date=day).count()
        attendance_trend.append({
            'date': day.strftime('%d %b'),
            'present': present,
            'total': total
        })
    
    return render_template('admin/dashboard.html',
        total_students=total_students,
        total_batches=total_batches,
        total_teachers=total_teachers,
        today_attendance=today_attendance,
        today_present=today_present,
        monthly_collection=monthly_collection,
        recent_enrollments=recent_enrollments,
        recent_transactions=recent_transactions,
        batch_stats=batch_stats,
        attendance_trend=attendance_trend,
        now=datetime.now()
    )


@admin_bp.route('/settings')
@login_required
@staff_required
def settings():
    """Application settings page"""
    return render_template('admin/settings.html')


# Teacher Management Routes
@admin_bp.route('/teachers')
@login_required
@admin_required
def list_teachers():
    """List all teachers"""
    teachers = User.query.filter_by(role='TEACHER').order_by(User.created_at.desc()).all()
    return render_template('admin/teachers.html', teachers=teachers)


@admin_bp.route('/teachers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_teacher():
    """Add new teacher"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        
        # Validation
        if not username or not email or not password:
            flash('Please fill all required fields.', 'warning')
            return render_template('admin/add_teacher.html')
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('admin/add_teacher.html')
        
        try:
            teacher = User(
                username=username,
                email=email,
                role='TEACHER',
                is_active=True
            )
            teacher.set_password(password)
            
            db.session.add(teacher)
            db.session.commit()
            
            flash(f'Teacher "{username}" added successfully!', 'success')
            return redirect(url_for('admin.list_teachers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding teacher: {str(e)}', 'danger')
    
    return render_template('admin/add_teacher.html')


@admin_bp.route('/teachers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_teacher(id):
    """Edit teacher details"""
    teacher = User.query.get_or_404(id)
    
    if teacher.role != 'TEACHER':
        flash('Invalid teacher.', 'danger')
        return redirect(url_for('admin.list_teachers'))
    
    if request.method == 'POST':
        try:
            teacher.username = request.form.get('username', '').strip()
            teacher.email = request.form.get('email', '').strip()
            teacher.is_active = 'is_active' in request.form
            
            # Update password if provided
            new_password = request.form.get('password', '').strip()
            if new_password:
                teacher.set_password(new_password)
            
            db.session.commit()
            flash('Teacher updated successfully!', 'success')
            return redirect(url_for('admin.list_teachers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating teacher: {str(e)}', 'danger')
    
    return render_template('admin/edit_teacher.html', teacher=teacher)


@admin_bp.route('/teachers/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_teacher(id):
    """Toggle teacher active status"""
    teacher = User.query.get_or_404(id)
    
    if teacher.role != 'TEACHER':
        flash('Invalid teacher.', 'danger')
        return redirect(url_for('admin.list_teachers'))
    
    teacher.is_active = not teacher.is_active
    db.session.commit()
    
    status = 'activated' if teacher.is_active else 'deactivated'
    flash(f'Teacher {teacher.username} {status}.', 'success')
    return redirect(url_for('admin.list_teachers'))


@admin_bp.route('/teachers/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_teacher(id):
    """Permanently delete teacher account"""
    teacher = User.query.get_or_404(id)
    
    if teacher.role != 'TEACHER':
        flash('Invalid teacher.', 'danger')
        return redirect(url_for('admin.list_teachers'))
    
    teacher_name = teacher.username
    
    try:
        # Unassign teacher from batches
        from app.models import Batch
        Batch.query.filter_by(teacher_id=id).update({'teacher_id': None})
        
        # Delete teacher
        db.session.delete(teacher)
        db.session.commit()
        
        flash(f'Teacher {teacher_name} has been permanently deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting teacher: {str(e)}', 'danger')
    
    return redirect(url_for('admin.list_teachers'))
