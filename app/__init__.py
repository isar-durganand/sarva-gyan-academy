"""
Sarva Gyaan Academy - Flask Application Factory
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

from app.config import Config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

# Configure login manager
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.student import student_bp
    from app.routes.attendance import attendance_bp
    from app.routes.fee import fee_bp
    from app.routes.announcement import announcement_bp
    from app.routes.portal import portal_bp
    from app.routes.chat import chat_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(fee_bp)
    app.register_blueprint(announcement_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(chat_bp)
    
    # Create database tables and seed data
    with app.app_context():
        db.create_all()
        seed_database()
    
    return app


def seed_database():
    """Seed initial data if database is empty"""
    from app.models import User, Batch
    from flask import current_app
    
    # Get admin credentials from config (environment variables)
    admin_email = current_app.config.get('ADMIN_EMAIL', 'admin@sarvagyaan.com')
    admin_password = current_app.config.get('ADMIN_PASSWORD', 'changeme123')
    
    # Check if admin exists
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        # Create admin user
        admin = User(
            username='Admin',
            email=admin_email,
            role='ADMIN',
            is_active=True
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        
        # Create sample batches
        batches = [
            Batch(name='Class 10-A', class_name='Class 10', capacity=30, is_active=True),
            Batch(name='Class 10-B', class_name='Class 10', capacity=30, is_active=True),
            Batch(name='Class 11-Science', class_name='Class 11', capacity=25, is_active=True),
            Batch(name='Class 11-Commerce', class_name='Class 11', capacity=25, is_active=True),
            Batch(name='Class 12-Science', class_name='Class 12', capacity=25, is_active=True),
        ]
        for batch in batches:
            db.session.add(batch)
        
        db.session.commit()
        print("[OK] Database seeded with admin user and sample batches")

