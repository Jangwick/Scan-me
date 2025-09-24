# QR Code Attendance System Configuration

import os
from datetime import timedelta
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.absolute()

class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'qr-attendance-secret-key-2025'
    
    # Database Configuration
    DATABASE_PATH = BASE_DIR / 'database' / 'attendance.db'
    
    # Upload Configuration
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    QR_CODES_FOLDER = BASE_DIR / 'static' / 'qr_codes'
    REPORTS_FOLDER = BASE_DIR / 'reports'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # QR Code Configuration
    QR_CODE_SIZE = 10
    QR_CODE_BORDER = 4
    QR_CODE_ERROR_CORRECT = 'M'  # Medium error correction
    QR_CODE_FORMAT = 'PNG'
    QR_CODE_SECURITY_TOKEN_LENGTH = 32
    QR_CODE_EXPIRY_HOURS = 24
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Security Configuration
    BCRYPT_LOG_ROUNDS = 12
    PASSWORD_MIN_LENGTH = 6
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_DURATION = timedelta(minutes=15)
    
    # Email Configuration (for notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@attendance.local'
    
    # Attendance Configuration
    ATTENDANCE_LATE_THRESHOLD_MINUTES = 15
    ATTENDANCE_DUPLICATE_SCAN_WINDOW_MINUTES = 5
    ATTENDANCE_AUTO_CLEANUP_DAYS = 365
    
    # Report Configuration
    REPORTS_DEFAULT_FORMAT = 'excel'
    REPORTS_MAX_RECORDS = 10000
    REPORTS_CACHE_TIMEOUT = timedelta(hours=1)
    
    # Notification Configuration
    NOTIFICATIONS_ENABLED = True
    NOTIFICATIONS_EMAIL_ENABLED = False  # Set to True to enable email notifications
    NOTIFICATIONS_MAX_QUEUE_SIZE = 1000
    NOTIFICATIONS_CLEANUP_INTERVAL = timedelta(hours=24)
    
    # API Configuration
    API_RATE_LIMIT = '100 per hour'
    API_TIMEOUT = 30  # seconds
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = BASE_DIR / 'logs' / 'attendance.log'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # Development Configuration
    DEBUG = os.environ.get('DEBUG', 'False').lower() in ['true', 'on', '1']
    TESTING = False
    
    # WebSocket Configuration (optional)
    WEBSOCKET_ENABLED = os.environ.get('WEBSOCKET_ENABLED', 'False').lower() in ['true', 'on', '1']
    WEBSOCKET_PING_TIMEOUT = 60
    WEBSOCKET_PING_INTERVAL = 25
    
    # Performance Configuration
    DATABASE_CONNECTION_POOL_SIZE = 20
    DATABASE_QUERY_TIMEOUT = 30
    CACHE_ENABLED = True
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # File Storage Configuration
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'csv', 'xlsx'}
    TEMP_CLEANUP_INTERVAL = timedelta(hours=1)
    
    @staticmethod
    def init_app(app):
        """Initialize application configuration"""
        # Create necessary directories
        directories = [
            Config.UPLOAD_FOLDER,
            Config.QR_CODES_FOLDER,
            Config.REPORTS_FOLDER,
            Config.DATABASE_PATH.parent,
            Config.LOG_FILE.parent
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Set Flask configuration
        app.config.update({
            'SECRET_KEY': Config.SECRET_KEY,
            'PERMANENT_SESSION_LIFETIME': Config.PERMANENT_SESSION_LIFETIME,
            'SESSION_COOKIE_SECURE': Config.SESSION_COOKIE_SECURE,
            'SESSION_COOKIE_HTTPONLY': Config.SESSION_COOKIE_HTTPONLY,
            'SESSION_COOKIE_SAMESITE': Config.SESSION_COOKIE_SAMESITE,
            'MAX_CONTENT_LENGTH': Config.MAX_CONTENT_LENGTH,
        })


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Use SQLite for development
    DATABASE_PATH = BASE_DIR / 'database' / 'attendance_dev.db'
    
    # Relaxed security for development
    BCRYPT_LOG_ROUNDS = 4  # Faster for development
    SESSION_COOKIE_SECURE = False
    
    # Enable WebSocket for development
    WEBSOCKET_ENABLED = True
    
    # More verbose logging
    LOG_LEVEL = 'DEBUG'
    
    # Email configuration for development (use console backend)
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 1025  # MailHog default port
    MAIL_USE_TLS = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # Use in-memory database for testing
    DATABASE_PATH = ':memory:'
    
    # Disable security features for testing
    BCRYPT_LOG_ROUNDS = 4
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = False
    
    # Disable email for testing
    MAIL_SUPPRESS_SEND = True
    NOTIFICATIONS_EMAIL_ENABLED = False
    
    # Fast cache timeout for testing
    CACHE_DEFAULT_TIMEOUT = 1


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True  # Requires HTTPS
    BCRYPT_LOG_ROUNDS = 14
    
    # Production database path
    DATABASE_PATH = BASE_DIR / 'database' / 'attendance_prod.db'
    
    # Production logging
    LOG_LEVEL = 'WARNING'
    
    # Email configuration for production
    NOTIFICATIONS_EMAIL_ENABLED = True
    
    # Performance optimizations
    DATABASE_CONNECTION_POOL_SIZE = 50
    CACHE_DEFAULT_TIMEOUT = 3600  # 1 hour
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Production-specific initialization
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Setup file logging
        if not app.debug:
            file_handler = RotatingFileHandler(
                cls.LOG_FILE,
                maxBytes=cls.LOG_MAX_BYTES,
                backupCount=cls.LOG_BACKUP_COUNT
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            app.logger.setLevel(logging.INFO)
            app.logger.info('QR Attendance System startup')


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


# Additional Configuration Classes
class QRCodeConfig:
    """QR Code specific configuration"""
    
    # QR Code generation settings
    VERSION = 1  # Controls the size of the QR Code
    ERROR_CORRECT = {
        'L': 1,  # ~7% error correction
        'M': 0,  # ~15% error correction (default)
        'Q': 3,  # ~25% error correction
        'H': 2   # ~30% error correction
    }
    
    # QR Code styling
    FILL_COLOR = "black"
    BACK_COLOR = "white"
    
    # QR Code data format
    DATA_FORMAT = {
        'student_id': str,
        'timestamp': str,
        'security_token': str,
        'room_id': str,
        'expiry': str
    }
    
    # Batch processing
    BATCH_SIZE = 100
    BATCH_TIMEOUT = 300  # 5 minutes


class DatabaseConfig:
    """Database specific configuration"""
    
    # Connection settings
    TIMEOUT = 30.0
    CHECK_SAME_THREAD = False
    
    # WAL mode settings for better concurrency
    JOURNAL_MODE = 'WAL'
    SYNCHRONOUS = 'NORMAL'
    CACHE_SIZE = 10000
    TEMP_STORE = 'MEMORY'
    
    # Backup settings
    BACKUP_INTERVAL = timedelta(hours=6)
    BACKUP_RETENTION_DAYS = 30
    
    # Performance settings
    OPTIMIZE_INTERVAL = timedelta(days=1)
    VACUUM_INTERVAL = timedelta(days=7)


class SecurityConfig:
    """Security specific configuration"""
    
    # Password policy
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBERS = True
    PASSWORD_REQUIRE_SPECIAL = False
    
    # Session security
    SESSION_REGENERATE_ON_LOGIN = True
    SESSION_TIMEOUT_WARNING = timedelta(minutes=5)
    
    # API security
    API_KEY_LENGTH = 32
    API_RATE_LIMIT_STORAGE_URL = 'memory://'
    
    # CORS settings
    CORS_ORIGINS = ['http://localhost:3000']  # Add your frontend URLs
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE']
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization']


# Environment-specific configurations
def get_config():
    """Get configuration based on environment variable"""
    return config.get(os.environ.get('FLASK_ENV', 'default'))


# Validation functions
def validate_config():
    """Validate configuration settings"""
    errors = []
    
    # Check required directories
    if not Config.DATABASE_PATH.parent.exists():
        errors.append(f"Database directory does not exist: {Config.DATABASE_PATH.parent}")
    
    # Check email configuration if enabled
    if Config.NOTIFICATIONS_EMAIL_ENABLED:
        if not Config.MAIL_SERVER:
            errors.append("MAIL_SERVER is required when email notifications are enabled")
        if not Config.MAIL_USERNAME:
            errors.append("MAIL_USERNAME is required when email notifications are enabled")
    
    # Check QR code directory
    if not Config.QR_CODES_FOLDER.exists():
        try:
            Config.QR_CODES_FOLDER.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create QR codes directory: {e}")
    
    return errors


# Initialize configuration
def init_config(app, config_name=None):
    """Initialize application with configuration"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    config_class = config.get(config_name, DevelopmentConfig)
    config_class.init_app(app)
    
    # Validate configuration
    errors = validate_config()
    if errors:
        for error in errors:
            app.logger.error(f"Configuration error: {error}")
        raise RuntimeError("Configuration validation failed")
    
    return config_class