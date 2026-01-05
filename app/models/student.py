"""
Student and Batch Models
"""
from datetime import datetime, date
from app import db


class Batch(db.Model):
    """Batch/Class model"""
    __tablename__ = 'batches'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, default=30)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    students = db.relationship('Student', backref='batch', lazy='dynamic')
    fee_structures = db.relationship('FeeStructure', backref='batch', lazy=True)
    
    @property
    def student_count(self):
        """Get number of students in batch"""
        return self.students.count()
    
    @property
    def available_seats(self):
        """Get available seats in batch"""
        return max(0, self.capacity - self.student_count)
    
    def __repr__(self):
        return f'<Batch {self.name}>'


class Student(db.Model):
    """Student model with complete profile"""
    __tablename__ = 'students'
    
    # Status constants
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_INACTIVE = 'INACTIVE'
    STATUS_GRADUATED = 'GRADUATED'
    STATUS_DROPPED = 'DROPPED'
    
    GENDER_MALE = 'MALE'
    GENDER_FEMALE = 'FEMALE'
    GENDER_OTHER = 'OTHER'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Personal Information
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    photo = db.Column(db.String(255))  # Photo file path
    
    # Contact Information
    email = db.Column(db.String(120))
    phone = db.Column(db.String(15))
    address = db.Column(db.Text)
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    pincode = db.Column(db.String(10))
    
    # Parent/Guardian Information
    parent_name = db.Column(db.String(100))
    parent_phone = db.Column(db.String(15))
    parent_email = db.Column(db.String(120))
    parent_occupation = db.Column(db.String(100))
    
    # Academic Information
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    enrollment_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default=STATUS_ACTIVE)
    
    # Additional Information
    blood_group = db.Column(db.String(5))
    medical_conditions = db.Column(db.Text)
    previous_school = db.Column(db.String(200))
    remarks = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - cascade delete ensures related records are removed when student is deleted
    attendances = db.relationship('Attendance', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    fee_transactions = db.relationship('FeeTransaction', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def full_name(self):
        """Get full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    @staticmethod
    def generate_student_id():
        """Generate unique student ID"""
        from datetime import datetime
        year = datetime.now().strftime('%Y')
        
        # Get the last student of this year
        last_student = Student.query.filter(
            Student.student_id.like(f'SGA{year}%')
        ).order_by(Student.id.desc()).first()
        
        if last_student:
            # Extract number and increment
            last_num = int(last_student.student_id[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"SGA{year}{new_num:04d}"
    
    def get_attendance_percentage(self, start_date=None, end_date=None):
        """Calculate attendance percentage for date range"""
        from app.models.attendance import Attendance
        
        query = self.attendances
        if start_date:
            query = query.filter(Attendance.date >= start_date)
        if end_date:
            query = query.filter(Attendance.date <= end_date)
        
        total = query.count()
        if total == 0:
            return 0
        
        present = query.filter(Attendance.status.in_(['PRESENT', 'LATE'])).count()
        return round((present / total) * 100, 2)
    
    def get_total_fees_paid(self):
        """Get total fees paid by student"""
        total = db.session.query(db.func.sum(FeeTransaction.amount)).filter(
            FeeTransaction.student_id == self.id
        ).scalar()
        return total or 0
    
    def __repr__(self):
        return f'<Student {self.student_id}: {self.full_name}>'


# Import at end to avoid circular imports
from app.models.fee import FeeTransaction
