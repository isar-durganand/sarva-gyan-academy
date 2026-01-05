"""
Fee Management Models
"""
from datetime import datetime, date
from app import db


class FeeStructure(db.Model):
    """Fee structure definition"""
    __tablename__ = 'fee_structures'
    
    # Frequency constants
    FREQ_MONTHLY = 'MONTHLY'
    FREQ_QUARTERLY = 'QUARTERLY'
    FREQ_YEARLY = 'YEARLY'
    FREQ_ONE_TIME = 'ONE_TIME'
    
    FREQUENCIES = [FREQ_MONTHLY, FREQ_QUARTERLY, FREQ_YEARLY, FREQ_ONE_TIME]
    
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    frequency = db.Column(db.String(20), default=FREQ_MONTHLY)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('FeeTransaction', backref='fee_structure', lazy=True)
    
    def __repr__(self):
        return f'<FeeStructure {self.name}: ₹{self.amount}>'


class FeeTransaction(db.Model):
    """Fee payment transactions"""
    __tablename__ = 'fee_transactions'
    
    # Payment mode constants
    MODE_CASH = 'CASH'
    MODE_CHEQUE = 'CHEQUE'
    MODE_UPI = 'UPI'
    MODE_CARD = 'CARD'
    MODE_BANK_TRANSFER = 'BANK_TRANSFER'
    
    PAYMENT_MODES = [MODE_CASH, MODE_CHEQUE, MODE_UPI, MODE_CARD, MODE_BANK_TRANSFER]
    
    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    fee_structure_id = db.Column(db.Integer, db.ForeignKey('fee_structures.id'), nullable=True)
    
    # Payment details
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=date.today)
    payment_mode = db.Column(db.String(20), default=MODE_CASH)
    
    # For specific payment modes
    cheque_number = db.Column(db.String(20))
    cheque_date = db.Column(db.Date)
    bank_name = db.Column(db.String(100))
    transaction_id = db.Column(db.String(100))  # For UPI/Online payments
    
    # Additional info
    description = db.Column(db.String(255))
    month_for = db.Column(db.String(20))  # e.g., "January 2024"
    discount = db.Column(db.Numeric(10, 2), default=0)
    fine = db.Column(db.Numeric(10, 2), default=0)
    
    # Collected by
    collected_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    collector = db.relationship('User', foreign_keys=[collected_by], backref='fees_collected')
    
    @staticmethod
    def generate_receipt_number():
        """Generate unique receipt number"""
        today = datetime.now()
        prefix = f"REC{today.strftime('%Y%m%d')}"
        
        # Get last receipt of today
        last_receipt = FeeTransaction.query.filter(
            FeeTransaction.receipt_number.like(f'{prefix}%')
        ).order_by(FeeTransaction.id.desc()).first()
        
        if last_receipt:
            last_num = int(last_receipt.receipt_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"{prefix}{new_num:04d}"
    
    @property
    def net_amount(self):
        """Calculate net amount after discount and fine"""
        return float(self.amount) - float(self.discount or 0) + float(self.fine or 0)
    
    def __repr__(self):
        return f'<FeeTransaction {self.receipt_number}: ₹{self.amount}>'


class FeeDue(db.Model):
    """Track pending fee dues"""
    __tablename__ = 'fee_dues'
    
    STATUS_PENDING = 'PENDING'
    STATUS_PAID = 'PAID'
    STATUS_PARTIAL = 'PARTIAL'
    STATUS_OVERDUE = 'OVERDUE'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    fee_structure_id = db.Column(db.Integer, db.ForeignKey('fee_structures.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    month_for = db.Column(db.String(20))
    status = db.Column(db.String(20), default=STATUS_PENDING)
    paid_amount = db.Column(db.Numeric(10, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - cascade delete ensures fee dues are removed when student is deleted
    student = db.relationship('Student', backref=db.backref('fee_dues', lazy='dynamic', cascade='all, delete-orphan'))
    fee_structure = db.relationship('FeeStructure', backref='dues')
    
    @property
    def pending_amount(self):
        """Get remaining pending amount"""
        return float(self.amount) - float(self.paid_amount or 0)
    
    @property
    def is_overdue(self):
        """Check if fee is overdue"""
        return self.due_date < date.today() and self.status != self.STATUS_PAID
    
    def __repr__(self):
        return f'<FeeDue {self.student_id} - ₹{self.amount} due {self.due_date}>'
