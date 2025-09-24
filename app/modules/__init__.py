# QR Attendance System - Modules Package
"""
Core business logic modules for QR Code Attendance System.
Contains all the main functionality modules for the attendance tracking system.
"""

__version__ = "1.0.0"
__description__ = "Core modules for QR attendance system functionality"

# Module descriptions
MODULES = {
    'database_manager': 'Database operations and schema management',
    'qr_generator': 'QR code generation and validation',
    'attendance_manager': 'Attendance processing and analytics',
    'report_generator': 'Report generation and data export',
    'notification_system': 'Real-time notifications and alerts',
    'auth_manager': 'Authentication and authorization',
    'room_manager': 'Room management and scheduling',
    'student_manager': 'Student operations and management'
}

def get_module_info():
    """Get information about available modules"""
    return MODULES