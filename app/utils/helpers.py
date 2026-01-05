"""
Helper Functions
"""
import os
from datetime import datetime
from flask import current_app


def format_currency(amount):
    """Format amount as Indian Rupee"""
    if amount is None:
        return "₹0.00"
    return f"₹{float(amount):,.2f}"


def format_date(date_obj, format_str=None):
    """Format date object to string"""
    if date_obj is None:
        return ""
    if format_str is None:
        format_str = current_app.config.get('DATE_FORMAT', '%d-%m-%Y')
    if isinstance(date_obj, str):
        return date_obj
    return date_obj.strftime(format_str)


def format_datetime(dt_obj, format_str=None):
    """Format datetime object to string"""
    if dt_obj is None:
        return ""
    if format_str is None:
        format_str = current_app.config.get('DATETIME_FORMAT', '%d-%m-%Y %H:%M')
    return dt_obj.strftime(format_str)


def allowed_file(filename):
    """Check if file extension is allowed"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif'})


def save_uploaded_file(file, folder='uploads'):
    """Save uploaded file and return path"""
    if file and allowed_file(file.filename):
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        
        # Add timestamp to filename to make it unique
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
        
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        return os.path.join(folder, filename)
    return None


def parse_date(date_str, format_str='%Y-%m-%d'):
    """Parse date string to date object"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, format_str).date()
    except ValueError:
        return None


def get_current_academic_year():
    """Get current academic year string (e.g., '2024-25')"""
    today = datetime.now()
    if today.month >= 4:  # April onwards is new academic year
        return f"{today.year}-{str(today.year + 1)[2:]}"
    return f"{today.year - 1}-{str(today.year)[2:]}"


def get_months_list():
    """Get list of months with their names"""
    return [
        (1, 'January'), (2, 'February'), (3, 'March'),
        (4, 'April'), (5, 'May'), (6, 'June'),
        (7, 'July'), (8, 'August'), (9, 'September'),
        (10, 'October'), (11, 'November'), (12, 'December')
    ]


def paginate_query(query, page, per_page=None):
    """Paginate SQLAlchemy query"""
    if per_page is None:
        per_page = current_app.config.get('ITEMS_PER_PAGE', 20)
    return query.paginate(page=page, per_page=per_page, error_out=False)
