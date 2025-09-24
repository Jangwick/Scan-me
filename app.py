"""
Flask QR Code Attendance System - Main Application
Author: GitHub Copilot
Date: September 2025

This module serves as the main entry point for the Flask QR code attendance system.
It handles application initialization, configuration, and routes coordination.
The system provides comprehensive attendance management with QR code scanning,
real-time notifications, and data export capabilities.

Features:
- QR code scanning for room entry
- Real-time attendance display
- Room-based attendance management
- Data export to Excel/CSV/PDF
- Professor dashboard
- Automated reporting
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3
import qrcode
import io
import base64
import json
import os
from functools import wraps
import logging
from app.modules.database_manager import DatabaseManager
from app.modules.qr_generator import QRGenerator
from app.modules.attendance_manager import AttendanceManager
from app.modules.report_generator import ReportGenerator
from app.modules.notification_system import NotificationSystem
from app.modules.auth_manager import AuthManager
from app.modules.room_manager import RoomManager
from app.modules.student_manager import StudentManager

# Initialize Flask application with correct template and static folders
app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['DATABASE_URL'] = 'database/attendance.db'
app.config['UPLOAD_FOLDER'] = 'exports'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)
logger = logging.getLogger(__name__)

# Initialize system components
db_manager = DatabaseManager(app.config['DATABASE_URL'])
qr_generator = QRGenerator()
attendance_manager = AttendanceManager(db_manager)
report_generator = ReportGenerator(db_manager)
notification_system = NotificationSystem()
auth_manager = AuthManager(db_manager)
room_manager = RoomManager(db_manager)
student_manager = StudentManager(db_manager)

def login_required(f):
    """Decorator to require login for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'admin':
            flash('Admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Main landing page"""
    try:
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        
        # Get recent activity for display (limited to last 10 entries)
        recent_scans = attendance_manager.get_recent_attendance(limit=10)
        total_students = student_manager.get_student_count()
        total_rooms = room_manager.get_room_count()
        
        stats = {
            'total_students': total_students,
            'total_rooms': total_rooms,
            'today_scans': len([scan for scan in recent_scans 
                              if scan['date'] == datetime.now().strftime('%Y-%m-%d')])
        }
        
        return render_template('index.html', 
                             recent_scans=recent_scans, 
                             stats=stats)
    
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        flash('An error occurred while loading the page.', 'error')
        return render_template('index.html', recent_scans=[], stats={})

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page and authentication"""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                flash('Please provide both username and password.', 'error')
                return render_template('login.html')
            
            user = auth_manager.authenticate_user(username, password)
            
            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['user_type'] = user['user_type']
                session['full_name'] = user['full_name']
                
                flash(f'Welcome back, {user["full_name"]}!', 'success')
                logger.info(f"User {username} logged in successfully")
                
                # Redirect based on user type
                if user['user_type'] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'error')
                logger.warning(f"Failed login attempt for username: {username}")
        
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    username = session.get('username', 'Unknown')
    session.clear()
    flash('You have been logged out successfully.', 'success')
    logger.info(f"User {username} logged out")
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main user dashboard"""
    try:
        user_type = session.get('user_type', 'user')
        
        # Get dashboard data based on user type
        if user_type == 'professor':
            # Professor-specific dashboard data
            rooms = room_manager.get_rooms_by_professor(session['user_id'])
            today_summary = attendance_manager.get_today_attendance_summary()
            
            dashboard_data = {
                'user_type': user_type,
                'rooms': rooms,
                'today_attendance': [],  # Use empty list for now
                'total_rooms': len(rooms),
                'today_present': today_summary.get('unique_students', 0)
            }
        
        elif user_type == 'admin':
            return redirect(url_for('admin_dashboard'))
        
        else:
            # Regular user dashboard
            recent_scans = attendance_manager.get_recent_attendance(limit=10)
            
            dashboard_data = {
                'user_type': user_type,
                'recent_scans': recent_scans
            }
        
        return render_template('dashboard.html', data=dashboard_data)
    
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        flash('Error loading dashboard data.', 'error')
        return render_template('dashboard.html', data={})

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard with system overview"""
    try:
        # Get comprehensive admin statistics
        today_summary = attendance_manager.get_today_attendance_summary()
        stats = {
            'total_students': student_manager.get_student_count(),
            'total_professors': auth_manager.get_professor_count(),
            'total_rooms': room_manager.get_room_count(),
            'today_scans': today_summary.get('total_scans', 0),
            'active_sessions': today_summary.get('unique_students', 0),
            'recent_activity': attendance_manager.get_recent_attendance(limit=20)
        }
        
        # Get room occupancy data
        room_occupancy = room_manager.get_room_occupancy_stats()
        
        # Get attendance trends for the last 7 days
        attendance_trends = attendance_manager.get_attendance_trends(days=7)
        
        admin_data = {
            'stats': stats,
            'room_occupancy': room_occupancy,
            'attendance_trends': attendance_trends
        }
        
        return render_template('dashboard.html', data=admin_data)
    
    except Exception as e:
        logger.error(f"Admin dashboard error: {str(e)}")
        flash('Error loading admin dashboard.', 'error')
        return render_template('dashboard.html', data={})

@app.route('/scan')
@login_required
def scan_page():
    """QR code scanning interface"""
    try:
        rooms = room_manager.get_all_rooms()
        return render_template('scan.html', rooms=rooms)
    
    except Exception as e:
        logger.error(f"Scan page error: {str(e)}")
        flash('Error loading scan page.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/scan', methods=['POST'])
@login_required
def process_scan():
    """Process QR code scan and record attendance"""
    try:
        data = request.get_json()
        qr_code = data.get('qr_code', '').strip()
        room_id = data.get('room_id')
        
        if not qr_code:
            return jsonify({
                'success': False, 
                'message': 'No QR code data provided'
            }), 400
        
        if not room_id:
            return jsonify({
                'success': False, 
                'message': 'No room specified'
            }), 400
        
        # Process the attendance scan
        result = attendance_manager.process_attendance_scan(qr_code, room_id)
        
        if result['success']:
            # Send real-time notification
            notification_data = {
                'student_name': result['student']['name'],
                'student_id': result['student']['student_id'],
                'department': result['student']['department'],
                'year_section': f"{result['student']['year']}{result['student']['section']}",
                'room_name': result['room']['name'],
                'timestamp': result['timestamp'],
                'status': result['status']
            }
            
            notification_system.send_attendance_notification(notification_data)
            
            return jsonify({
                'success': True,
                'message': f"Attendance recorded for {result['student']['name']}",
                'data': notification_data
            })
        
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
    
    except Exception as e:
        logger.error(f"Scan processing error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing the scan'
        }), 500

@app.route('/reports')
@login_required
def reports():
    """Reports and analytics page"""
    try:
        # For now, redirect to dashboard since we don't have a separate reports template
        # In a full implementation, this would show detailed reports
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Reports error: {str(e)}")
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    # Initialize database on startup
    try:
        db_manager.initialize_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)