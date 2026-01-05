"""
Student Portal Routes - Dashboard for Students
"""
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func, or_

from app import db
from app.models import Student, Announcement, Attendance, FeeTransaction
from app.utils.decorators import student_required
from app.utils.helpers import save_uploaded_file

portal_bp = Blueprint('portal', __name__, url_prefix='/portal')


@portal_bp.route('/')
@login_required
@student_required
def dashboard():
    """Student portal dashboard"""
    # Get student linked to current user
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    if not student:
        return render_template('portal/no_student.html')
    
    today = date.today()
    
    # Get attendance stats for this month
    first_day = date(today.year, today.month, 1)
    month_attendance = Attendance.query.filter(
        Attendance.student_id == student.id,
        Attendance.date >= first_day,
        Attendance.date <= today
    ).all()
    
    present_count = sum(1 for a in month_attendance if a.status in ['PRESENT', 'LATE'])
    total_days = len(month_attendance)
    attendance_percentage = round((present_count / total_days * 100), 1) if total_days > 0 else 0
    
    # Get recent attendance
    recent_attendance = Attendance.query.filter_by(
        student_id=student.id
    ).order_by(Attendance.date.desc()).limit(7).all()
    
    # Get announcements for this student
    announcements = Announcement.query.filter(
        Announcement.is_active == True,
        Announcement.for_students == True,
        or_(
            Announcement.batch_id == None,  # All batches
            Announcement.batch_id == student.batch_id
        ),
        or_(
            Announcement.expiry_date == None,
            Announcement.expiry_date >= today
        )
    ).order_by(
        Announcement.is_pinned.desc(),
        Announcement.priority.desc(),
        Announcement.created_at.desc()
    ).limit(10).all()
    
    # Separate by type
    holidays = [a for a in announcements if a.announcement_type == 'HOLIDAY']
    homework = [a for a in announcements if a.announcement_type == 'HOMEWORK']
    events = [a for a in announcements if a.announcement_type == 'EVENT']
    notices = [a for a in announcements if a.announcement_type not in ['HOLIDAY', 'HOMEWORK', 'EVENT']]
    
    return render_template('portal/dashboard.html',
        student=student,
        attendance_percentage=attendance_percentage,
        present_count=present_count,
        total_days=total_days,
        recent_attendance=recent_attendance,
        announcements=announcements,
        holidays=holidays,
        homework=homework,
        events=events,
        notices=notices
    )


@portal_bp.route('/attendance')
@login_required
@student_required
def my_attendance():
    """View full attendance history"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    if not student:
        return render_template('portal/no_student.html')
    
    # Get all attendance records
    attendance_records = Attendance.query.filter_by(
        student_id=student.id
    ).order_by(Attendance.date.desc()).all()
    
    # Calculate overall percentage
    total = len(attendance_records)
    present = sum(1 for a in attendance_records if a.status in ['PRESENT', 'LATE'])
    percentage = round((present / total * 100), 1) if total > 0 else 0
    
    return render_template('portal/attendance.html',
        student=student,
        attendance_records=attendance_records,
        total=total,
        present=present,
        percentage=percentage
    )


@portal_bp.route('/announcements')
@login_required
@student_required
def my_announcements():
    """View all announcements"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    today = date.today()
    
    if not student:
        return render_template('portal/no_student.html')
    
    announcements = Announcement.query.filter(
        Announcement.is_active == True,
        Announcement.for_students == True,
        or_(
            Announcement.batch_id == None,
            Announcement.batch_id == student.batch_id
        ),
        or_(
            Announcement.expiry_date == None,
            Announcement.expiry_date >= today
        )
    ).order_by(
        Announcement.is_pinned.desc(),
        Announcement.created_at.desc()
    ).all()
    
    return render_template('portal/announcements.html',
        student=student,
        announcements=announcements
    )


@portal_bp.route('/fees')
@login_required
@student_required
def my_fees():
    """View fee status and payment history"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    if not student:
        return render_template('portal/no_student.html')
    
    # Get all fee transactions
    transactions = FeeTransaction.query.filter_by(
        student_id=student.id
    ).order_by(FeeTransaction.payment_date.desc()).all()
    
    total_paid = sum(float(t.amount) for t in transactions)
    
    return render_template('portal/fees.html',
        student=student,
        transactions=transactions,
        total_paid=total_paid
    )


@portal_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@student_required
def my_profile():
    """View and update profile"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    if not student:
        return render_template('portal/no_student.html')
    
    if request.method == 'POST':
        try:
            action = request.form.get('action', 'update_photo')
            
            if action == 'update_photo':
                # Handle photo upload
                if 'photo' in request.files:
                    photo = request.files['photo']
                    if photo.filename:
                        photo_path = save_uploaded_file(photo, 'students')
                        if photo_path:
                            student.photo = photo_path
                            db.session.commit()
                            flash('Profile picture updated!', 'success')
            
            elif action == 'update_details':
                # Update personal details
                from app.utils.helpers import parse_date
                
                student.date_of_birth = parse_date(request.form.get('date_of_birth'))
                student.gender = request.form.get('gender', '').strip() or None
                student.blood_group = request.form.get('blood_group', '').strip() or None
                
                # Address
                student.address = request.form.get('address', '').strip() or None
                student.city = request.form.get('city', '').strip() or None
                student.state = request.form.get('state', '').strip() or None
                student.pincode = request.form.get('pincode', '').strip() or None
                
                # Parent details
                student.parent_name = request.form.get('parent_name', '').strip() or None
                student.parent_phone = request.form.get('parent_phone', '').strip() or None
                student.parent_email = request.form.get('parent_email', '').strip() or None
                student.parent_occupation = request.form.get('parent_occupation', '').strip() or None
                
                # School details
                student.previous_school = request.form.get('previous_school', '').strip() or None
                student.medical_conditions = request.form.get('medical_conditions', '').strip() or None
                
                db.session.commit()
                flash('Profile updated successfully!', 'success')
            
            return redirect(url_for('portal.my_profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
    
    return render_template('portal/profile.html', student=student)


