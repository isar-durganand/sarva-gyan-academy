"""
User Model - Authentication and Authorization
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager


class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    # Role constants
    ROLE_ADMIN = 'ADMIN'
    ROLE_TEACHER = 'TEACHER'
    ROLE_STUDENT = 'STUDENT'
    ROLE_PARENT = 'PARENT'
    
    ROLES = [ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT, ROLE_PARENT]
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_STUDENT)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student = db.relationship('Student', backref='user', uselist=False, lazy=True)
    batches_taught = db.relationship('Batch', backref='teacher', lazy=True)
    
    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == self.ROLE_ADMIN
    
    def is_teacher(self):
        """Check if user is teacher"""
        return self.role == self.ROLE_TEACHER
    
    def is_student(self):
        """Check if user is student"""
        return self.role == self.ROLE_STUDENT
    
    def is_parent(self):
        """Check if user is parent"""
        return self.role == self.ROLE_PARENT
    
    def __repr__(self):
        return f'<User {self.email}>'


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))
