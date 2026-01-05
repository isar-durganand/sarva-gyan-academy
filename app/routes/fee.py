"""
Fee Management Routes
"""
from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, make_response
from flask_login import login_required, current_user
from sqlalchemy import func
import io
import json

from app import db
from app.models import Student, Batch, FeeStructure, FeeTransaction, FeeDue
from app.utils.decorators import staff_required
from app.utils.helpers import parse_date, format_currency, get_months_list, paginate_query

fee_bp = Blueprint('fee', __name__, url_prefix='/fees')


@fee_bp.route('/')
@login_required
@staff_required
def index():
    """Fee management dashboard"""
    today = date.today()
    
    # Today's collection
    today_collection = db.session.query(func.sum(FeeTransaction.amount)).filter(
        FeeTransaction.payment_date == today
    ).scalar() or 0
    
    # This month's collection
    first_day = date(today.year, today.month, 1)
    monthly_collection = db.session.query(func.sum(FeeTransaction.amount)).filter(
        FeeTransaction.payment_date >= first_day,
        FeeTransaction.payment_date <= today
    ).scalar() or 0
    
    # Total pending dues
    total_pending = db.session.query(func.sum(FeeDue.amount - FeeDue.paid_amount)).filter(
        FeeDue.status != 'PAID'
    ).scalar() or 0
    
    # Recent transactions
    recent_transactions = FeeTransaction.query.order_by(
        FeeTransaction.created_at.desc()
    ).limit(10).all()
    
    # Fee structures
    fee_structures = FeeStructure.query.filter_by(is_active=True).all()
    
    return render_template('fee/index.html',
        today_collection=today_collection,
        monthly_collection=monthly_collection,
        total_pending=total_pending,
        recent_transactions=recent_transactions,
        fee_structures=fee_structures
    )


@fee_bp.route('/collect', methods=['GET', 'POST'])
@login_required
@staff_required
def collect_fee():
    """Collect fee from student"""
    if request.method == 'POST':
        try:
            student_id = request.form.get('student_id', type=int)
            amount = Decimal(request.form.get('amount', '0'))
            payment_mode = request.form.get('payment_mode', 'CASH')
            fee_structure_id = request.form.get('fee_structure_id', type=int) or None
            month_for = request.form.get('month_for', '').strip()
            discount = Decimal(request.form.get('discount', '0') or '0')
            fine = Decimal(request.form.get('fine', '0') or '0')
            description = request.form.get('description', '').strip()
            
            if not student_id or amount <= 0:
                flash('Please select a student and enter valid amount.', 'warning')
                return redirect(request.url)
            
            student = Student.query.get_or_404(student_id)
            
            # Generate receipt number
            receipt_number = FeeTransaction.generate_receipt_number()
            
            # Create transaction
            transaction = FeeTransaction(
                receipt_number=receipt_number,
                student_id=student_id,
                fee_structure_id=fee_structure_id,
                amount=amount,
                payment_date=parse_date(request.form.get('payment_date')) or date.today(),
                payment_mode=payment_mode,
                month_for=month_for,
                discount=discount,
                fine=fine,
                description=description,
                collected_by=current_user.id
            )
            
            # For cheque payments
            if payment_mode == 'CHEQUE':
                transaction.cheque_number = request.form.get('cheque_number', '').strip()
                transaction.cheque_date = parse_date(request.form.get('cheque_date'))
                transaction.bank_name = request.form.get('bank_name', '').strip()
            
            # For UPI/Online payments
            if payment_mode in ['UPI', 'BANK_TRANSFER', 'CARD']:
                transaction.transaction_id = request.form.get('transaction_id', '').strip()
            
            db.session.add(transaction)
            db.session.commit()
            
            flash(f'Payment of ₹{amount} received from {student.full_name}. Receipt: {receipt_number}', 'success')
            return redirect(url_for('fee.view_receipt', id=transaction.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing payment: {str(e)}', 'danger')
    
    # GET request
    fee_structures = FeeStructure.query.filter_by(is_active=True).all()
    batches = Batch.query.filter_by(is_active=True).all()
    
    # Pre-select student if provided
    student_id = request.args.get('student_id', type=int)
    selected_student = Student.query.get(student_id) if student_id else None
    
    return render_template('fee/collect.html',
        fee_structures=fee_structures,
        batches=batches,
        selected_student=selected_student,
        payment_modes=FeeTransaction.PAYMENT_MODES
    )


@fee_bp.route('/receipt/<int:id>')
@login_required
def view_receipt(id):
    """View fee receipt"""
    transaction = FeeTransaction.query.get_or_404(id)
    return render_template('fee/receipt.html', transaction=transaction)


@fee_bp.route('/receipt/<int:id>/print')
@login_required
def print_receipt(id):
    """Printable receipt view"""
    transaction = FeeTransaction.query.get_or_404(id)
    return render_template('fee/receipt_print.html', transaction=transaction)


@fee_bp.route('/transactions')
@login_required
@staff_required
def list_transactions():
    """List all fee transactions"""
    page = request.args.get('page', 1, type=int)
    student_id = request.args.get('student_id', type=int)
    start_date = parse_date(request.args.get('start_date'))
    end_date = parse_date(request.args.get('end_date'))
    payment_mode = request.args.get('payment_mode', '')
    
    query = FeeTransaction.query
    
    if student_id:
        query = query.filter(FeeTransaction.student_id == student_id)
    if start_date:
        query = query.filter(FeeTransaction.payment_date >= start_date)
    if end_date:
        query = query.filter(FeeTransaction.payment_date <= end_date)
    if payment_mode:
        query = query.filter(FeeTransaction.payment_mode == payment_mode)
    
    query = query.order_by(FeeTransaction.created_at.desc())
    transactions = paginate_query(query, page)
    
    # Calculate totals
    total_amount = db.session.query(func.sum(FeeTransaction.amount)).filter(
        FeeTransaction.id.in_([t.id for t in transactions.items])
    ).scalar() or 0
    
    return render_template('fee/transactions.html',
        transactions=transactions,
        total_amount=total_amount,
        payment_modes=FeeTransaction.PAYMENT_MODES
    )


@fee_bp.route('/pending')
@login_required
@staff_required
def pending_fees():
    """View pending fee dues - shows students whose fee payment is overdue"""
    batch_id = request.args.get('batch_id', type=int)
    
    batches = Batch.query.filter_by(is_active=True).all()
    
    # Get students with pending fees
    query = Student.query.filter_by(status='ACTIVE')
    if batch_id:
        query = query.filter(Student.batch_id == batch_id)
    
    students = query.all()
    today = date.today()
    
    # Calculate pending for each student
    # Logic: Fee is due after each COMPLETE month from enrollment date
    # E.g., Enrolled Jan 2 -> First fee due Feb 2 -> If not paid by Feb 2, shows as pending
    pending_list = []
    for student in students:
        # Get fee structure for student's batch
        if student.batch:
            fee_structure = FeeStructure.query.filter_by(
                batch_id=student.batch_id, 
                is_active=True
            ).first()
            
            if fee_structure:
                monthly_fee = float(fee_structure.amount)
                
                # Get enrollment date
                enrollment_date = student.enrollment_date or (student.created_at.date() if student.created_at else today)
                
                if not enrollment_date:
                    continue
                
                # Calculate number of COMPLETE months since enrollment
                # A month is complete when the same day of next month has passed
                # E.g., enrolled Jan 2 -> one complete month = Feb 2
                complete_months = 0
                
                # Calculate months difference
                year_diff = today.year - enrollment_date.year
                month_diff = today.month - enrollment_date.month
                total_months = year_diff * 12 + month_diff
                
                # Check if the current month's due date has passed
                # Due date is the same day of month as enrollment (or last day if month is shorter)
                if total_months > 0:
                    # At least one month has passed
                    due_day = min(enrollment_date.day, 28)  # Cap at 28 for safety with Feb
                    
                    # Check if we've passed the due day this month
                    if today.day >= due_day:
                        complete_months = total_months
                    else:
                        complete_months = total_months - 1
                else:
                    # Same month as enrollment, no fee due yet
                    complete_months = 0
                
                # Only proceed if at least 1 complete month has passed
                if complete_months > 0:
                    expected = monthly_fee * complete_months
                    paid = float(student.get_total_fees_paid())
                    pending = expected - paid
                    
                    # Only add if there's actually pending amount (more than ₹1)
                    if pending > 1:
                        pending_list.append({
                            'student': student,
                            'expected': expected,
                            'paid': paid,
                            'pending': pending,
                            'months_overdue': complete_months
                        })
    
    # Sort by pending amount (highest first)
    pending_list.sort(key=lambda x: x['pending'], reverse=True)
    
    return render_template('fee/pending.html',
        batches=batches,
        selected_batch=batch_id,
        pending_list=pending_list
    )


@fee_bp.route('/defaulters')
@login_required
@staff_required
def defaulters():
    """Fee defaulters list"""
    today = date.today()
    
    # Get overdue fee dues
    overdue = FeeDue.query.filter(
        FeeDue.due_date < today,
        FeeDue.status != 'PAID'
    ).order_by(FeeDue.due_date).all()
    
    return render_template('fee/defaulters.html', overdue=overdue)


# Fee Structure Management

@fee_bp.route('/structure')
@login_required
@staff_required
def list_structures():
    """List fee structures"""
    structures = FeeStructure.query.order_by(FeeStructure.created_at.desc()).all()
    return render_template('fee/structures.html', structures=structures)


@fee_bp.route('/structure/add', methods=['GET', 'POST'])
@login_required
@staff_required
def add_structure():
    """Add fee structure"""
    if request.method == 'POST':
        try:
            structure = FeeStructure(
                name=request.form.get('name', '').strip(),
                batch_id=request.form.get('batch_id', type=int) or None,
                amount=Decimal(request.form.get('amount', '0')),
                frequency=request.form.get('frequency', 'MONTHLY'),
                description=request.form.get('description', '').strip(),
                is_active=True
            )
            db.session.add(structure)
            db.session.commit()
            
            flash(f'Fee structure "{structure.name}" created successfully!', 'success')
            return redirect(url_for('fee.list_structures'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating fee structure: {str(e)}', 'danger')
    
    batches = Batch.query.filter_by(is_active=True).all()
    return render_template('fee/add_structure.html', 
        batches=batches,
        frequencies=FeeStructure.FREQUENCIES
    )


@fee_bp.route('/structure/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_structure(id):
    """Edit fee structure"""
    structure = FeeStructure.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            structure.name = request.form.get('name', '').strip()
            structure.batch_id = request.form.get('batch_id', type=int) or None
            structure.amount = Decimal(request.form.get('amount', '0'))
            structure.frequency = request.form.get('frequency', 'MONTHLY')
            structure.description = request.form.get('description', '').strip()
            structure.is_active = 'is_active' in request.form
            
            db.session.commit()
            flash('Fee structure updated successfully!', 'success')
            return redirect(url_for('fee.list_structures'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating fee structure: {str(e)}', 'danger')
    
    batches = Batch.query.filter_by(is_active=True).all()
    return render_template('fee/edit_structure.html',
        structure=structure,
        batches=batches,
        frequencies=FeeStructure.FREQUENCIES
    )


@fee_bp.route('/structure/<int:id>/delete', methods=['POST'])
@login_required
@staff_required
def delete_structure(id):
    """Delete fee structure"""
    structure = FeeStructure.query.get_or_404(id)
    structure_name = structure.name
    
    try:
        # Check if there are any transactions linked to this structure
        transaction_count = FeeTransaction.query.filter_by(fee_structure_id=id).count()
        
        if transaction_count > 0:
            flash(f'Cannot delete "{structure_name}" - it has {transaction_count} associated transaction(s). Deactivate it instead.', 'warning')
            return redirect(url_for('fee.list_structures'))
        
        db.session.delete(structure)
        db.session.commit()
        flash(f'Fee structure "{structure_name}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting fee structure: {str(e)}', 'danger')
    
    return redirect(url_for('fee.list_structures'))


@fee_bp.route('/report')
@login_required
@staff_required
def fee_report():
    """Fee collection report"""
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    
    # Date range
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1)
    else:
        last_day = date(year, month + 1, 1)
    
    # Total collection
    total = db.session.query(func.sum(FeeTransaction.amount)).filter(
        FeeTransaction.payment_date >= first_day,
        FeeTransaction.payment_date < last_day
    ).scalar() or 0
    
    # Payment mode-wise breakdown  
    mode_breakdown = db.session.query(
        FeeTransaction.payment_mode,
        func.sum(FeeTransaction.amount).label('total'),
        func.count(FeeTransaction.id).label('count')
    ).filter(
        FeeTransaction.payment_date >= first_day,
        FeeTransaction.payment_date < last_day
    ).group_by(FeeTransaction.payment_mode).all()
    
    # Daily collection
    daily_collection = db.session.query(
        FeeTransaction.payment_date,
        func.sum(FeeTransaction.amount).label('total')
    ).filter(
        FeeTransaction.payment_date >= first_day,
        FeeTransaction.payment_date < last_day
    ).group_by(FeeTransaction.payment_date).order_by(FeeTransaction.payment_date).all()
    
    return render_template('fee/report.html',
        month=month,
        year=year,
        months=get_months_list(),
        total=total,
        mode_breakdown=mode_breakdown,
        daily_collection=daily_collection
    )


@fee_bp.route('/student-details/<int:student_id>')
@login_required
@staff_required
def get_student_fee_details(student_id):
    """Get fee details for a specific student via AJAX"""
    student = Student.query.get_or_404(student_id)
    
    response = {
        'status': 'success',
        'student': {
            'id': student.id,
            'name': student.full_name,
            'batch_id': student.batch_id
        },
        'fee_structure': None,
        'pending_amount': 0
    }
    
    # Get fee structure for student's batch
    if student.batch_id:
        fee_structure = FeeStructure.query.filter_by(
            batch_id=student.batch_id, 
            is_active=True
        ).first()
        
        if fee_structure:
            response['fee_structure'] = {
                'id': fee_structure.id,
                'name': fee_structure.name,
                'amount': float(fee_structure.amount)
            }
            
            # Calculate pending amount (reuse logic from pending_fees)
            today = date.today()
            monthly_fee = float(fee_structure.amount)
            enrollment_date = student.enrollment_date or (student.created_at.date() if student.created_at else today)
            
            if enrollment_date:
                year_diff = today.year - enrollment_date.year
                month_diff = today.month - enrollment_date.month
                total_months = year_diff * 12 + month_diff
                
                complete_months = 0
                if total_months > 0:
                    due_day = min(enrollment_date.day, 28)
                    if today.day >= due_day:
                        complete_months = total_months
                    else:
                        complete_months = total_months - 1
                
                if complete_months > 0:
                    expected = monthly_fee * complete_months
                    paid = float(student.get_total_fees_paid())
                    pending = max(0, expected - paid)
                    response['pending_amount'] = pending

    return Response(
        response=json.dumps(response),
        status=200,
        mimetype='application/json'
    )
