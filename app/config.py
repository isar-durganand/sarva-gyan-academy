"""
Application Configuration
"""
import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Ensure instance directory exists
instance_path = os.path.join(basedir, 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)


def get_database_url():
    """Get database URL with Supabase compatibility fix"""
    url = os.environ.get('DATABASE_URL')
    if url:
        # Supabase uses 'postgres://' but SQLAlchemy requires 'postgresql://'
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        return url
    # Fallback to SQLite for local development
    return 'sqlite:///' + os.path.join(basedir, 'instance', 'sarva_gyaan.db')


class Config:
    """Base configuration"""
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'sarva-gyaan-academy-secret-key-2024'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = get_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Upload configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(basedir), 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'csv', 'xlsx'}
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    # Application settings
    APP_NAME = 'Sarva Gyaan Academy'
    TIMEZONE = 'Asia/Kolkata'
    CURRENCY = '₹'
    DATE_FORMAT = '%d-%m-%Y'
    DATETIME_FORMAT = '%d-%m-%Y %H:%M'
    
    # Admin credentials from environment
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@sarvagyaan.com')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'changeme123')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
