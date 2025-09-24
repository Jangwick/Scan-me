# QR Attendance System - App Package
"""
Main application package for QR Code Attendance System.
This package contains the core Flask application and all its modules.
"""

__version__ = "1.0.0"
__author__ = "QR Attendance Team"
__description__ = "A comprehensive Flask-based attendance tracking system using QR code scanning technology"

# Import core components for easy access
from .modules.database_manager import DatabaseManager
from .modules.qr_generator import QRGenerator
from .modules.attendance_manager import AttendanceManager
from .modules.report_generator import ReportGenerator
from .modules.notification_system import NotificationSystem
from .modules.auth_manager import AuthManager
from .modules.room_manager import RoomManager
from .modules.student_manager import StudentManager

__all__ = [
    'DatabaseManager',
    'QRGenerator', 
    'AttendanceManager',
    'ReportGenerator',
    'NotificationSystem',
    'AuthManager',
    'RoomManager',
    'StudentManager'
]