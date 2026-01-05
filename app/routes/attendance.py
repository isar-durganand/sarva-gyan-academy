"""
Attendance Management Routes
"""
from datetime import datetime, date, timedelta
from calendar import monthrange
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from sqlalchemy import func
import io
import csv

from app import db
from app.models import Student, Batch, Attendance
from app.utils.decorators import staff_required
from app.utils.helpers import parse_date, get_months_list

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')


@attendance_bp.route('/')
@login_required
@staff_required
def index():
    """Attendance dashboard"""
    today = date.today()
    
    # Today's attendance stats
    total_students = Student.query.filter_by(status='ACTIVE').count()
    today_marked = Attendance.query.filter_by(date=today).count()
    today_present = Attendance.query.filter_by(date=today, status='PRESENT').count()
    today_absent = Attendance.query.filter_by(date=today, status='ABSENT').count()
    today_late = Attendance.query.filter_by(date=today, status='LATE').count()
    
    # Batch-wise today's status
    batches = Batch.query.filter_by(is_active=True).all()
    batch_stats = []
    for batch in batches:
        total = batch.students.filter_by(status='ACTIVE').count()
        marked = Attendance.query.join(Student).filter(
            Student.batch_id == batch.id,
            Attendance.date == today
        ).count()
        present = Attendance.query.join(Student).filter(
            Student.batch_id == batch.id,
            Attendance.date == today,
            Attendance.status == 'PRESENT'
        ).count()
        
        batch_stats.append({
            'batch': batch,
            'total': total,
            'marked': marked,
            'present': present,
            'percentage': round((present / total * 100), 1) if total > 0 else 0
        })
    
    return render_template('attendance/index.html',
        today=today,
        total_students=total_students,
        today_marked=today_marked,
        today_present=today_present,
        today_absent=today_absent,
        today_late=today_late,
        batch_stats=batch_stats
    )


@attendance_bp.route('/mark', methods=['GET', 'POST'])
@login_required
@staff_required
def mark_attendance():
    """Mark attendance for a batch"""
    batches = Batch.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        batch_id = request.form.get('batch_id', type=int)
        attendance_date = parse_date(request.form.get('date')) or date.today()
        
        if not batch_id:
            flash('Please select a batch.', 'warning')
            return redirect(request.url)
        
        # Get all students in batch
        students = Student.query.filter_by(batch_id=batch_id, status='ACTIVE').all()
        
        marked_count = 0
        for student in students:
            status = request.form.get(f'status_{student.id}', 'ABSENT')
            remarks = request.form.get(f'remarks_{student.id}', '').strip()
            
            # Check if attendance already exists
            existing = Attendance.query.filter_by(
                student_id=student.id,
                date=attendance_date
            ).first()
            
            if existing:
                existing.status = status
                existing.remarks = remarks
                existing.marked_by = current_user.id
            else:
                attendance = Attendance(
                    student_id=student.id,
                    date=attendance_date,
                    status=status,
                    remarks=remarks,
                    marked_by=current_user.id
                )
                db.session.add(attendance)
            
            marked_count += 1
        
        db.session.commit()
        flash(f'Attendance marked for {marked_count} students.', 'success')
        return redirect(url_for('attendance.index'))
    
    # GET request - show form
    batch_id = request.args.get('batch_id', type=int)
    attendance_date = parse_date(request.args.get('date')) or date.today()
    
    students = []
    attendance_records = {}
    selected_batch = None
    
    if batch_id:
        selected_batch = Batch.query.get(batch_id)
        students = Student.query.filter_by(batch_id=batch_id, status='ACTIVE').order_by(Student.first_name).all()
        
        # Get existing attendance for the date
        for student in students:
            record = Attendance.query.filter_by(
                student_id=student.id,
                date=attendance_date
            ).first()
            attendance_records[student.id] = record
    
    return render_template('attendance/mark.html',
        batches=batches,
        selected_batch=selected_batch,
        students=students,
        attendance_records=attendance_records,
        attendance_date=attendance_date
    )


@attendance_bp.route('/view')
@login_required  
def view_attendance():
    """View attendance records"""
    batch_id = request.args.get('batch_id', type=int)
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    
    batches = Batch.query.filter_by(is_active=True).all()
    
    students = []
    attendance_data = {}
    days_in_month = 0
    
    if batch_id:
        students = Student.query.filter_by(batch_id=batch_id, status='ACTIVE').order_by(Student.first_name).all()
        _, days_in_month = monthrange(year, month)
        
        # Get attendance for each student for each day
        for student in students:
            attendance_data[student.id] = {}
            for day in range(1, days_in_month + 1):
                att_date = date(year, month, day)
                record = Attendance.query.filter_by(
                    student_id=student.id,
                    date=att_date
                ).first()
                attendance_data[student.id][day] = record
    
    return render_template('attendance/view.html',
        batches=batches,
        selected_batch=batch_id,
        students=students,
        attendance_data=attendance_data,
        days_in_month=days_in_month,
        month=month,
        year=year,
        months=get_months_list()
    )


@attendance_bp.route('/report')
@login_required
@staff_required
def attendance_report():
    """Monthly attendance report"""
    batch_id = request.args.get('batch_id', type=int)
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    
    batches = Batch.query.filter_by(is_active=True).all()
    report_data = []
    
    if batch_id:
        report_data = Attendance.get_monthly_summary(batch_id, year, month)
    
    return render_template('attendance/report.html',
        batches=batches,
        selected_batch=batch_id,
        report_data=report_data,
        month=month,
        year=year,
        months=get_months_list()
    )


@attendance_bp.route('/student/<int:student_id>')
@login_required
def student_attendance(student_id):
    """View individual student attendance history"""
    student = Student.query.get_or_404(student_id)
    
    # Get attendance records ordered by date descending
    page = request.args.get('page', 1, type=int)
    attendance_records = student.attendances.order_by(
        Attendance.date.desc()
    ).paginate(page=page, per_page=30, error_out=False)
    
    # Calculate overall stats
    total = student.attendances.count()
    present = student.attendances.filter(Attendance.status.in_(['PRESENT', 'LATE'])).count()
    percentage = round((present / total * 100), 2) if total > 0 else 0
    
    return render_template('attendance/student.html',
        student=student,
        attendance_records=attendance_records,
        total=total,
        present=present,
        percentage=percentage
    )


@attendance_bp.route('/export')
@login_required
@staff_required
def export_attendance():
    """Export attendance to CSV"""
    batch_id = request.args.get('batch_id', type=int)
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    
    if not batch_id:
        flash('Please select a batch to export.', 'warning')
        return redirect(url_for('attendance.view_attendance'))
    
    batch = Batch.query.get_or_404(batch_id)
    students = Student.query.filter_by(batch_id=batch_id, status='ACTIVE').order_by(Student.first_name).all()
    _, days_in_month = monthrange(year, month)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row
    header = ['Student ID', 'Name']
    for day in range(1, days_in_month + 1):
        header.append(str(day))
    header.extend(['Present', 'Absent', 'Percentage'])
    writer.writerow(header)
    
    # Data rows
    for student in students:
        row = [student.student_id, student.full_name]
        present_count = 0
        absent_count = 0
        
        for day in range(1, days_in_month + 1):
            att_date = date(year, month, day)
            record = Attendance.query.filter_by(
                student_id=student.id,
                date=att_date
            ).first()
            
            if record:
                if record.status in ['PRESENT', 'LATE']:
                    row.append('P')
                    present_count += 1
                else:
                    row.append('A')
                    absent_count += 1
            else:
                row.append('-')
        
        total = present_count + absent_count
        percentage = round((present_count / total * 100), 1) if total > 0 else 0
        row.extend([present_count, absent_count, f'{percentage}%'])
        writer.writerow(row)
    
    # Create response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=attendance_{batch.name}_{year}_{month:02d}.csv'
        }
    )
