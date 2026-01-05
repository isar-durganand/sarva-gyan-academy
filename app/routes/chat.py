"""
Chat Routes - Internal Messaging System
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_

from app import db
from app.models import User, Conversation, Message, get_total_unread_count

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


@chat_bp.route('/')
@login_required
def inbox():
    """Display inbox with all conversations"""
    conversations = Conversation.get_user_conversations(current_user.id)
    
    # Build conversation data with unread counts
    conversation_data = []
    for conv in conversations:
        other_user = conv.get_other_user(current_user.id)
        last_msg = conv.last_message
        unread_count = conv.get_unread_count(current_user.id)
        
        conversation_data.append({
            'conversation': conv,
            'other_user': other_user,
            'last_message': last_msg,
            'unread_count': unread_count
        })
    
    # Determine which template to use based on user role
    if current_user.is_student():
        return render_template('portal/messages.html',
            conversations=conversation_data,
            total_unread=get_total_unread_count(current_user.id)
        )
    else:
        return render_template('chat/inbox.html',
            conversations=conversation_data,
            total_unread=get_total_unread_count(current_user.id)
        )


@chat_bp.route('/conversation/<int:conversation_id>')
@login_required
def view_conversation(conversation_id):
    """View a specific conversation"""
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # Verify user is part of this conversation
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        flash('You do not have access to this conversation.', 'danger')
        return redirect(url_for('chat.inbox'))
    
    # Mark messages as read
    conversation.mark_as_read(current_user.id)
    
    # Get all messages
    messages = conversation.messages.order_by(Message.created_at.asc()).all()
    other_user = conversation.get_other_user(current_user.id)
    
    if current_user.is_student():
        return render_template('portal/conversation.html',
            conversation=conversation,
            messages=messages,
            other_user=other_user
        )
    else:
        return render_template('chat/conversation.html',
            conversation=conversation,
            messages=messages,
            other_user=other_user
        )


@chat_bp.route('/conversation/<int:conversation_id>/send', methods=['POST'])
@login_required
def send_message(conversation_id):
    """Send a message in a conversation"""
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # Verify user is part of this conversation
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        flash('You do not have access to this conversation.', 'danger')
        return redirect(url_for('chat.inbox'))
    
    content = request.form.get('content', '').strip()
    
    if not content:
        flash('Message cannot be empty.', 'warning')
        return redirect(url_for('chat.view_conversation', conversation_id=conversation_id))
    
    # Create new message
    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=content
    )
    db.session.add(message)
    
    # Update conversation timestamp
    conversation.updated_at = message.created_at
    db.session.commit()
    
    return redirect(url_for('chat.view_conversation', conversation_id=conversation_id))


@chat_bp.route('/compose')
@login_required
def compose():
    """Show compose new message form"""
    # Get recipient from query string if provided
    recipient_id = request.args.get('to', type=int)
    recipient = None
    if recipient_id:
        recipient = User.query.get(recipient_id)
    
    if current_user.is_student():
        return render_template('portal/compose.html', recipient=recipient)
    else:
        return render_template('chat/compose.html', recipient=recipient)


@chat_bp.route('/compose', methods=['POST'])
@login_required
def send_new_message():
    """Create a new conversation and send first message"""
    recipient_id = request.form.get('recipient_id', type=int)
    content = request.form.get('content', '').strip()
    
    if not recipient_id:
        flash('Please select a recipient.', 'warning')
        return redirect(url_for('chat.compose'))
    
    if not content:
        flash('Message cannot be empty.', 'warning')
        return redirect(url_for('chat.compose'))
    
    # Verify recipient exists and is not current user
    recipient = User.query.get(recipient_id)
    if not recipient:
        flash('Recipient not found.', 'danger')
        return redirect(url_for('chat.compose'))
    
    if recipient_id == current_user.id:
        flash('You cannot send a message to yourself.', 'warning')
        return redirect(url_for('chat.compose'))
    
    # Get or create conversation
    conversation = Conversation.get_or_create(current_user.id, recipient_id)
    
    # Create message
    message = Message(
        conversation_id=conversation.id,
        sender_id=current_user.id,
        content=content
    )
    db.session.add(message)
    conversation.updated_at = message.created_at
    db.session.commit()
    
    flash('Message sent successfully!', 'success')
    return redirect(url_for('chat.view_conversation', conversation_id=conversation.id))


@chat_bp.route('/api/users')
@login_required
def search_users():
    """API endpoint for user search (for recipient selection)"""
    query = request.args.get('q', '').strip()
    
    # Special case: return all active users (for initial display)
    if query == '*' or query == '':
        users = User.query.filter(
            User.id != current_user.id,
            User.is_active == True
        ).order_by(User.username).limit(20).all()
    elif len(query) < 1:
        return jsonify([])
    else:
        # Search for users by username or email, excluding current user
        users = User.query.filter(
            User.id != current_user.id,
            User.is_active == True,
            or_(
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        ).order_by(User.username).limit(15).all()
    
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'role': u.role
    } for u in users])


@chat_bp.route('/api/unread-count')
@login_required
def unread_count():
    """API endpoint to get total unread message count"""
    count = get_total_unread_count(current_user.id)
    return jsonify({'count': count})


@chat_bp.route('/api/conversation/<int:conversation_id>/messages')
@login_required
def get_messages(conversation_id):
    """API endpoint to get messages for real-time polling"""
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # Verify user is part of this conversation
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        return jsonify({'error': 'Not authorized'}), 403
    
    # Get last message ID from query param (only return newer messages)
    last_id = request.args.get('after', 0, type=int)
    
    # Get new messages
    messages = conversation.messages.filter(
        Message.id > last_id
    ).order_by(Message.created_at.asc()).all()
    
    # Mark as read
    if messages:
        conversation.mark_as_read(current_user.id)
    
    return jsonify({
        'messages': [{
            'id': m.id,
            'sender_id': m.sender_id,
            'content': m.content,
            'is_read': m.is_read,
            'is_mine': m.sender_id == current_user.id,
            'time': m.created_at.strftime('%I:%M %p')
        } for m in messages]
    })


@chat_bp.route('/conversation/<int:conversation_id>/delete', methods=['POST'])
@login_required
def delete_conversation(conversation_id):
    """Delete an entire conversation"""
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # Verify user is part of this conversation
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        flash('You do not have access to this conversation.', 'danger')
        return redirect(url_for('chat.inbox'))
    
    try:
        # Delete all messages first (due to foreign key)
        Message.query.filter_by(conversation_id=conversation_id).delete()
        # Delete the conversation
        db.session.delete(conversation)
        db.session.commit()
        flash('Conversation deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting conversation.', 'danger')
    
    return redirect(url_for('chat.inbox'))


@chat_bp.route('/conversation/<int:conversation_id>/clear', methods=['POST'])
@login_required
def clear_conversation(conversation_id):
    """Clear all messages in a conversation (keep conversation)"""
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # Verify user is part of this conversation
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        flash('You do not have access to this conversation.', 'danger')
        return redirect(url_for('chat.inbox'))
    
    try:
        Message.query.filter_by(conversation_id=conversation_id).delete()
        db.session.commit()
        flash('Chat cleared successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error clearing chat.', 'danger')
    
    return redirect(url_for('chat.view_conversation', conversation_id=conversation_id))


@chat_bp.route('/message/<int:message_id>/delete', methods=['POST'])
@login_required  
def delete_message(message_id):
    """Delete a single message (only sender can delete)"""
    message = Message.query.get_or_404(message_id)
    conversation_id = message.conversation_id
    
    # Only the sender can delete their own message
    if message.sender_id != current_user.id:
        flash('You can only delete your own messages.', 'warning')
        return redirect(url_for('chat.view_conversation', conversation_id=conversation_id))
    
    try:
        db.session.delete(message)
        db.session.commit()
        flash('Message deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting message.', 'danger')
    
    return redirect(url_for('chat.view_conversation', conversation_id=conversation_id))


@chat_bp.route('/api/message/<int:message_id>/delete', methods=['POST'])
@login_required
def api_delete_message(message_id):
    """API endpoint to delete a message (for AJAX calls)"""
    message = Message.query.get_or_404(message_id)
    
    if message.sender_id != current_user.id:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403
    
    try:
        db.session.delete(message)
        db.session.commit()
        return jsonify({'success': True})
    except:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Delete failed'}), 500


# Context processor to make unread count available in all templates
@chat_bp.app_context_processor
def inject_unread_count():
    """Inject unread message count into all templates"""
    if current_user.is_authenticated:
        return {'unread_message_count': get_total_unread_count(current_user.id)}
    return {'unread_message_count': 0}

