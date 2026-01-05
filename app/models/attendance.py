"""
Attendance Model
"""
from datetime import datetime, date
from app import db


class Attendance(db.Model):
    """Attendance tracking model"""
    __tablename__ = 'attendances'
    
    # Status constants
    STATUS_PRESENT = 'PRESENT'
    STATUS_ABSENT = 'ABSENT'
    STATUS_LATE = 'LATE'
    STATUS_EXCUSED = 'EXCUSED'
    
    STATUSES = [STATUS_PRESENT, STATUS_ABSENT, STATUS_LATE, STATUS_EXCUSED]
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PRESENT)
    marked_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    remarks = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: one attendance record per student per day
    __table_args__ = (
        db.UniqueConstraint('student_id', 'date', name='unique_student_date'),
    )
    
    # Relationships
    marked_by_user = db.relationship('User', foreign_keys=[marked_by], backref='attendances_marked')
    
    @staticmethod
    def get_batch_attendance(batch_id, attendance_date):
        """Get attendance for a batch on a specific date"""
        from app.models.student import Student
        
        students = Student.query.filter_by(batch_id=batch_id, status='ACTIVE').all()
        attendance_records = {}
        
        for student in students:
            record = Attendance.query.filter_by(
                student_id=student.id,
                date=attendance_date
            ).first()
            attendance_records[student.id] = record
        
        return students, attendance_records
    
    @staticmethod
    def get_monthly_summary(batch_id, year, month):
        """Get monthly attendance summary for a batch"""
        from app.models.student import Student
        from calendar import monthrange
        
        students = Student.query.filter_by(batch_id=batch_id, status='ACTIVE').all()
        _, days_in_month = monthrange(year, month)
        
        summary = []
        for student in students:
            start_date = date(year, month, 1)
            end_date = date(year, month, days_in_month)
            
            total = Attendance.query.filter(
                Attendance.student_id == student.id,
                Attendance.date >= start_date,
                Attendance.date <= end_date
            ).count()
            
            present = Attendance.query.filter(
                Attendance.student_id == student.id,
                Attendance.date >= start_date,
                Attendance.date <= end_date,
                Attendance.status.in_([Attendance.STATUS_PRESENT, Attendance.STATUS_LATE])
            ).count()
            
            percentage = round((present / total * 100), 2) if total > 0 else 0
            
            summary.append({
                'student': student,
                'total_days': total,
                'present_days': present,
                'absent_days': total - present,
                'percentage': percentage
            })
        
        return summary
    
    def __repr__(self):
        return f'<Attendance {self.student_id} - {self.date}: {self.status}>'
