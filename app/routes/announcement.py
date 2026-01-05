"""
Announcement/Broadcast Routes
"""
import os
from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models import Announcement, Batch
from app.utils.decorators import staff_required

announcement_bp = Blueprint('announcement', __name__, url_prefix='/announcements')

# Allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@announcement_bp.route('/')
@login_required
@staff_required
def list_announcements():
    """List all announcements"""
    announcements = Announcement.query.order_by(
        Announcement.is_pinned.desc(),
        Announcement.created_at.desc()
    ).all()
    return render_template('announcement/list.html', announcements=announcements)


@announcement_bp.route('/upload-image', methods=['POST'])
@login_required
@staff_required
def upload_image():
    """Handle image upload for announcements"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400
    
    # Check file size (max 5MB)
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > 5 * 1024 * 1024:
        return jsonify({'error': 'File too large. Maximum size is 5MB'}), 400
    
    try:
        # Create uploads directory if it doesn't exist
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'announcements')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Generate secure filename with timestamp
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        # Save file
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Return URL for the uploaded image
        image_url = url_for('static', filename=f'uploads/announcements/{filename}')
        return jsonify({'success': True, 'url': image_url})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@announcement_bp.route('/add', methods=['GET', 'POST'])
@login_required
@staff_required
def add_announcement():
    """Create new announcement"""
    if request.method == 'POST':
        try:
            announcement = Announcement(
                title=request.form.get('title', '').strip(),
                content=request.form.get('content', '').strip(),
                announcement_type=request.form.get('announcement_type', 'GENERAL'),
                priority=request.form.get('priority', 'NORMAL'),
                batch_id=request.form.get('batch_id', type=int) or None,
                for_students='for_students' in request.form,
                for_teachers='for_teachers' in request.form,
                for_parents='for_parents' in request.form,
                publish_date=datetime.strptime(request.form.get('publish_date'), '%Y-%m-%d').date() if request.form.get('publish_date') else date.today(),
                expiry_date=datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d').date() if request.form.get('expiry_date') else None,
                is_pinned='is_pinned' in request.form,
                is_active=True,
                image_url=request.form.get('image_url', '').strip() or None,
                created_by=current_user.id
            )
            
            db.session.add(announcement)
            db.session.commit()
            
            flash(f'Announcement "{announcement.title}" published!', 'success')
            return redirect(url_for('announcement.list_announcements'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating announcement: {str(e)}', 'danger')
    
    batches = Batch.query.filter_by(is_active=True).all()
    return render_template('announcement/add.html', 
        batches=batches,
        types=Announcement.TYPES,
        priorities=Announcement.PRIORITIES,
        today=date.today().strftime('%Y-%m-%d')
    )


@announcement_bp.route('/<int:id>')
@login_required
def view_announcement(id):
    """View announcement details"""
    announcement = Announcement.query.get_or_404(id)
    return render_template('announcement/view.html', announcement=announcement)


@announcement_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_announcement(id):
    """Edit announcement"""
    announcement = Announcement.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            announcement.title = request.form.get('title', '').strip()
            announcement.content = request.form.get('content', '').strip()
            announcement.announcement_type = request.form.get('announcement_type', 'GENERAL')
            announcement.priority = request.form.get('priority', 'NORMAL')
            announcement.batch_id = request.form.get('batch_id', type=int) or None
            announcement.for_students = 'for_students' in request.form
            announcement.for_teachers = 'for_teachers' in request.form
            announcement.for_parents = 'for_parents' in request.form
            announcement.is_pinned = 'is_pinned' in request.form
            announcement.is_active = 'is_active' in request.form
            announcement.image_url = request.form.get('image_url', '').strip() or None
            
            if request.form.get('publish_date'):
                announcement.publish_date = datetime.strptime(request.form.get('publish_date'), '%Y-%m-%d').date()
            if request.form.get('expiry_date'):
                announcement.expiry_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d').date()
            else:
                announcement.expiry_date = None
            
            db.session.commit()
            flash('Announcement updated!', 'success')
            return redirect(url_for('announcement.list_announcements'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating: {str(e)}', 'danger')
    
    batches = Batch.query.filter_by(is_active=True).all()
    return render_template('announcement/edit.html',
        announcement=announcement,
        batches=batches,
        types=Announcement.TYPES,
        priorities=Announcement.PRIORITIES
    )


@announcement_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@staff_required
def delete_announcement(id):
    """Delete announcement"""
    announcement = Announcement.query.get_or_404(id)
    db.session.delete(announcement)
    db.session.commit()
    flash('Announcement deleted.', 'success')
    return redirect(url_for('announcement.list_announcements'))
