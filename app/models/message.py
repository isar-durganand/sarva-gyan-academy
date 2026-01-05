"""
Message and Conversation Models for Internal Chat System
"""
from datetime import datetime
from app import db


class Conversation(db.Model):
    """Conversation model representing a chat thread between two users"""
    __tablename__ = 'conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user1 = db.relationship('User', foreign_keys=[user1_id], backref='conversations_as_user1')
    user2 = db.relationship('User', foreign_keys=[user2_id], backref='conversations_as_user2')
    messages = db.relationship('Message', backref='conversation', lazy='dynamic', 
                               cascade='all, delete-orphan', order_by='Message.created_at')
    
    @property
    def last_message(self):
        """Get the most recent message in this conversation"""
        return self.messages.order_by(Message.created_at.desc()).first()
    
    def get_other_user(self, current_user_id):
        """Get the other participant in the conversation"""
        if self.user1_id == current_user_id:
            return self.user2
        return self.user1
    
    def get_unread_count(self, user_id):
        """Get count of unread messages for a specific user"""
        return self.messages.filter(
            Message.sender_id != user_id,
            Message.is_read == False
        ).count()
    
    def mark_as_read(self, user_id):
        """Mark all messages as read for a specific user"""
        unread_messages = self.messages.filter(
            Message.sender_id != user_id,
            Message.is_read == False
        ).all()
        for msg in unread_messages:
            msg.is_read = True
        db.session.commit()
    
    @staticmethod
    def get_or_create(user1_id, user2_id):
        """Get existing conversation or create new one between two users"""
        # Normalize order to avoid duplicates
        if user1_id > user2_id:
            user1_id, user2_id = user2_id, user1_id
        
        conversation = Conversation.query.filter(
            ((Conversation.user1_id == user1_id) & (Conversation.user2_id == user2_id)) |
            ((Conversation.user1_id == user2_id) & (Conversation.user2_id == user1_id))
        ).first()
        
        if not conversation:
            conversation = Conversation(user1_id=user1_id, user2_id=user2_id)
            db.session.add(conversation)
            db.session.commit()
        
        return conversation
    
    @staticmethod
    def get_user_conversations(user_id):
        """Get all conversations for a user, ordered by most recent activity"""
        return Conversation.query.filter(
            (Conversation.user1_id == user_id) | (Conversation.user2_id == user_id)
        ).order_by(Conversation.updated_at.desc()).all()
    
    def __repr__(self):
        return f'<Conversation {self.id}: User {self.user1_id} <-> User {self.user2_id}>'


class Message(db.Model):
    """Individual message within a conversation"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', backref='sent_messages')
    
    def __repr__(self):
        return f'<Message {self.id} from User {self.sender_id}>'


def get_total_unread_count(user_id):
    """Get total count of unread messages for a user across all conversations"""
    return Message.query.join(Conversation).filter(
        ((Conversation.user1_id == user_id) | (Conversation.user2_id == user_id)),
        Message.sender_id != user_id,
        Message.is_read == False
    ).count()
