"""
Announcement Model for broadcasts
"""
from datetime import datetime
from app import db


class Announcement(db.Model):
    """Announcement/Broadcast model for holidays, events, and messages"""
    __tablename__ = 'announcements'
    
    # Type constants
    TYPE_GENERAL = 'GENERAL'
    TYPE_HOLIDAY = 'HOLIDAY'
    TYPE_EVENT = 'EVENT'
    TYPE_HOMEWORK = 'HOMEWORK'
    TYPE_EXAM = 'EXAM'
    TYPE_NOTICE = 'NOTICE'
    
    TYPES = [TYPE_GENERAL, TYPE_HOLIDAY, TYPE_EVENT, TYPE_HOMEWORK, TYPE_EXAM, TYPE_NOTICE]
    
    # Priority constants
    PRIORITY_LOW = 'LOW'
    PRIORITY_NORMAL = 'NORMAL'
    PRIORITY_HIGH = 'HIGH'
    PRIORITY_URGENT = 'URGENT'
    
    PRIORITIES = [PRIORITY_LOW, PRIORITY_NORMAL, PRIORITY_HIGH, PRIORITY_URGENT]
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    announcement_type = db.Column(db.String(20), default=TYPE_GENERAL)
    priority = db.Column(db.String(20), default=PRIORITY_NORMAL)
    
    # Target audience
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=True)  # Null = all batches
    for_students = db.Column(db.Boolean, default=True)
    for_teachers = db.Column(db.Boolean, default=True)
    for_parents = db.Column(db.Boolean, default=False)
    
    # Scheduling
    publish_date = db.Column(db.Date, default=datetime.utcnow)
    expiry_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_pinned = db.Column(db.Boolean, default=False)
    
    # Attachments
    image_url = db.Column(db.String(500), nullable=True)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    batch = db.relationship('Batch', backref='announcements', lazy=True)
    author = db.relationship('User', backref='announcements', lazy=True)
    
    @property
    def is_expired(self):
        """Check if announcement has expired"""
        if self.expiry_date:
            return datetime.now().date() > self.expiry_date
        return False
    
    @property
    def target_audience(self):
        """Get human-readable target audience"""
        audiences = []
        if self.for_students:
            audiences.append('Students')
        if self.for_teachers:
            audiences.append('Teachers')
        if self.for_parents:
            audiences.append('Parents')
        return ', '.join(audiences) if audiences else 'None'
    
    def __repr__(self):
        return f'<Announcement {self.title}>'
