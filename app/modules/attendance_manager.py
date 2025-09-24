"""
Attendance Manager Module - Flask QR Code Attendance System
Author: GitHub Copilot
Date: September 2025

This module handles all attendance-related operations for the QR code attendance system.
It manages attendance recording, validation, duplicate prevention, room-based tracking,
and provides comprehensive attendance analytics and reporting capabilities.

Features:
- QR code scan processing and validation
- Duplicate scan prevention
- Room-based attendance tracking
- Real-time attendance status updates
- Attendance analytics and statistics
- Late arrival detection and handling
- Bulk attendance operations
- Attendance history management
"""

from datetime import datetime, timedelta, time
import logging
from typing import Dict, List, Optional, Any, Tuple
import json
from dataclasses import dataclass
from app.modules.qr_generator import QRGenerator

@dataclass
class AttendanceRecord:
    """Data class for attendance record structure."""
    id: Optional[int]
    student_id: int
    room_id: int
    subject_id: Optional[int]
    scan_date: str
    scan_time: str
    status: str
    notes: Optional[str]
    scanned_by: Optional[int]
    created_at: str

class AttendanceManager:
    """
    Comprehensive attendance management system for QR code-based attendance tracking.
    Handles all aspects of attendance processing, validation, and analytics.
    """
    
    def __init__(self, database_manager):
        """
        Initialize the attendance manager with database connection.
        
        Args:
            database_manager: Database manager instance
        """
        self.db = database_manager
        self.qr_generator = QRGenerator()
        self.logger = logging.getLogger(__name__)
        
        # Attendance status constants
        self.STATUS_PRESENT = 'present'
        self.STATUS_LATE = 'late'
        self.STATUS_ABSENT = 'absent'
        self.STATUS_EXCUSED = 'excused'
        
        # Time thresholds
        self.late_threshold_minutes = 15  # Minutes after class start to mark as late
        self.max_daily_scans = 5  # Maximum scans per student per day
        
        # Load system settings
        self._load_system_settings()
    
    def _load_system_settings(self):
        """Load attendance-related system settings from database."""
        try:
            late_threshold = self.db.get_system_setting('late_threshold_minutes', '15')
            self.late_threshold_minutes = int(late_threshold)
            
            max_scans = self.db.get_system_setting('max_daily_scans', '5')
            self.max_daily_scans = int(max_scans)
            
            self.logger.info("Attendance system settings loaded successfully")
        
        except Exception as e:
            self.logger.error(f"Failed to load system settings: {str(e)}")
    
    def process_attendance_scan(self, qr_data: str, room_id: int, 
                               scanned_by: Optional[int] = None) -> Dict[str, Any]:
        """
        Process a QR code scan for attendance recording.
        
        Args:
            qr_data (str): QR code data string
            room_id (int): Room ID where scan occurred
            scanned_by (int): ID of user who performed the scan
        
        Returns:
            Dict[str, Any]: Scan processing result
        """
        try:
            # Validate QR code
            qr_validation = self.qr_generator.validate_qr_code(qr_data)
            if not qr_validation['valid']:
                return {
                    'success': False,
                    'message': f"Invalid QR code: {qr_validation['error']}",
                    'error_type': qr_validation.get('error_type', 'validation_error')
                }
            
            student_id_from_qr = qr_validation['data']['student_id']
            
            # Get student information
            student = self._get_student_by_id(student_id_from_qr)
            if not student:
                return {
                    'success': False,
                    'message': 'Student not found in database',
                    'error_type': 'student_not_found'
                }
            
            if not student['is_active']:
                return {
                    'success': False,
                    'message': 'Student account is inactive',
                    'error_type': 'inactive_student'
                }
            
            # Get room information
            room = self._get_room_by_id(room_id)
            if not room:
                return {
                    'success': False,
                    'message': 'Room not found',
                    'error_type': 'room_not_found'
                }
            
            if not room['is_active']:
                return {
                    'success': False,
                    'message': 'Room is inactive',
                    'error_type': 'inactive_room'
                }
            
            # Check for duplicate scans
            current_date = datetime.now().strftime('%Y-%m-%d')
            existing_attendance = self._check_existing_attendance(
                student['id'], room_id, current_date
            )
            
            if existing_attendance:
                return {
                    'success': False,
                    'message': f"Attendance already recorded for {student['first_name']} {student['last_name']} in this room today",
                    'error_type': 'duplicate_scan',
                    'existing_record': existing_attendance
                }
            
            # Check daily scan limit
            daily_scans = self._get_daily_scan_count(student['id'], current_date)
            if daily_scans >= self.max_daily_scans:
                return {
                    'success': False,
                    'message': f"Maximum daily scans ({self.max_daily_scans}) exceeded for this student",
                    'error_type': 'scan_limit_exceeded'
                }
            
            # Determine attendance status based on time
            current_time = datetime.now().time()
            attendance_status = self._determine_attendance_status(room_id, current_time)
            
            # Record attendance
            attendance_record = self._record_attendance(
                student['id'],
                room_id,
                current_date,
                current_time.strftime('%H:%M:%S'),
                attendance_status,
                scanned_by
            )
            
            if attendance_record:
                # Prepare success response
                result = {
                    'success': True,
                    'message': f"Attendance recorded successfully for {student['first_name']} {student['last_name']}",
                    'student': {
                        'id': student['id'],
                        'student_id': student['student_id'],
                        'name': f"{student['first_name']} {student['last_name']}",
                        'department': student['department'],
                        'year': student['year_level'],
                        'section': student['section']
                    },
                    'room': {
                        'id': room['id'],
                        'name': room['room_name'],
                        'code': room['room_code']
                    },
                    'attendance': {
                        'id': attendance_record,
                        'date': current_date,
                        'time': current_time.strftime('%H:%M:%S'),
                        'status': attendance_status
                    },
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                self.logger.info(f"Attendance recorded: Student {student['student_id']}, Room {room['room_code']}, Status: {attendance_status}")
                return result
            
            else:
                return {
                    'success': False,
                    'message': 'Failed to record attendance in database',
                    'error_type': 'database_error'
                }
        
        except Exception as e:
            self.logger.error(f"Attendance scan processing failed: {str(e)}")
            return {
                'success': False,
                'message': 'An error occurred while processing the scan',
                'error_type': 'system_error'
            }
    
    def _get_student_by_id(self, student_id: str) -> Optional[Dict[str, Any]]:
        """
        Get student information by student ID.
        
        Args:
            student_id (str): Student ID
        
        Returns:
            Dict[str, Any]: Student information or None
        """
        try:
            return self.db.execute_query(
                """SELECT * FROM students WHERE student_id = ? AND is_active = 1""",
                (student_id,),
                fetch_all=False
            )
        except Exception as e:
            self.logger.error(f"Failed to get student {student_id}: {str(e)}")
            return None
    
    def _get_room_by_id(self, room_id: int) -> Optional[Dict[str, Any]]:
        """
        Get room information by room ID.
        
        Args:
            room_id (int): Room ID
        
        Returns:
            Dict[str, Any]: Room information or None
        """
        try:
            return self.db.execute_query(
                """SELECT * FROM rooms WHERE id = ? AND is_active = 1""",
                (room_id,),
                fetch_all=False
            )
        except Exception as e:
            self.logger.error(f"Failed to get room {room_id}: {str(e)}")
            return None
    
    def _check_existing_attendance(self, student_id: int, room_id: int, date: str) -> Optional[Dict[str, Any]]:
        """
        Check if attendance already exists for student in room on specific date.
        
        Args:
            student_id (int): Student database ID
            room_id (int): Room ID
            date (str): Date string (YYYY-MM-DD)
        
        Returns:
            Dict[str, Any]: Existing attendance record or None
        """
        try:
            return self.db.execute_query(
                """SELECT a.*, s.student_id, s.first_name, s.last_name, r.room_name, r.room_code
                   FROM attendance a
                   JOIN students s ON a.student_id = s.id
                   JOIN rooms r ON a.room_id = r.id
                   WHERE a.student_id = ? AND a.room_id = ? AND a.scan_date = ?""",
                (student_id, room_id, date),
                fetch_all=False
            )
        except Exception as e:
            self.logger.error(f"Failed to check existing attendance: {str(e)}")
            return None
    
    def _get_daily_scan_count(self, student_id: int, date: str) -> int:
        """
        Get the number of scans for a student on a specific date.
        
        Args:
            student_id (int): Student database ID
            date (str): Date string (YYYY-MM-DD)
        
        Returns:
            int: Number of scans
        """
        try:
            result = self.db.execute_query(
                """SELECT COUNT(*) as scan_count FROM attendance 
                   WHERE student_id = ? AND scan_date = ?""",
                (student_id, date),
                fetch_all=False
            )
            return result['scan_count'] if result else 0
        except Exception as e:
            self.logger.error(f"Failed to get daily scan count: {str(e)}")
            return 0
    
    def _determine_attendance_status(self, room_id: int, scan_time: time) -> str:
        """
        Determine attendance status based on scan time and room schedule.
        
        Args:
            room_id (int): Room ID
            scan_time (time): Time of scan
        
        Returns:
            str: Attendance status
        """
        try:
            # Get current day of week (0 = Monday, 6 = Sunday)
            current_weekday = datetime.now().weekday()
            
            # Check room assignments for current time and day
            room_assignment = self.db.execute_query(
                """SELECT ra.*, s.subject_name 
                   FROM room_assignments ra
                   LEFT JOIN subjects s ON ra.subject_id = s.id
                   WHERE ra.room_id = ? AND ra.day_of_week = ? 
                   AND ra.start_time <= ? AND ra.end_time >= ?
                   AND ra.is_active = 1""",
                (room_id, current_weekday, scan_time.strftime('%H:%M:%S'), scan_time.strftime('%H:%M:%S')),
                fetch_all=False
            )
            
            if room_assignment:
                # Calculate if student is late
                start_time = datetime.strptime(room_assignment['start_time'], '%H:%M:%S').time()
                scan_datetime = datetime.combine(datetime.now().date(), scan_time)
                start_datetime = datetime.combine(datetime.now().date(), start_time)
                
                time_diff = scan_datetime - start_datetime
                late_threshold = timedelta(minutes=self.late_threshold_minutes)
                
                if time_diff > late_threshold:
                    return self.STATUS_LATE
                else:
                    return self.STATUS_PRESENT
            else:
                # No specific schedule, mark as present
                return self.STATUS_PRESENT
        
        except Exception as e:
            self.logger.error(f"Failed to determine attendance status: {str(e)}")
            return self.STATUS_PRESENT
    
    def _record_attendance(self, student_id: int, room_id: int, date: str, 
                          time_str: str, status: str, scanned_by: Optional[int] = None) -> Optional[int]:
        """
        Record attendance in the database.
        
        Args:
            student_id (int): Student database ID
            room_id (int): Room ID
            date (str): Date string
            time_str (str): Time string
            status (str): Attendance status
            scanned_by (int): ID of user who performed the scan
        
        Returns:
            int: Attendance record ID or None
        """
        try:
            # Get subject ID if there's an active class
            current_weekday = datetime.now().weekday()
            subject_assignment = self.db.execute_query(
                """SELECT subject_id FROM room_assignments 
                   WHERE room_id = ? AND day_of_week = ? 
                   AND start_time <= ? AND end_time >= ?
                   AND is_active = 1""",
                (room_id, current_weekday, time_str, time_str),
                fetch_all=False
            )
            
            subject_id = subject_assignment['subject_id'] if subject_assignment else None
            
            # Insert attendance record
            attendance_id = self.db.execute_update(
                """INSERT INTO attendance 
                   (student_id, room_id, subject_id, scan_date, scan_time, status, scanned_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (student_id, room_id, subject_id, date, time_str, status, scanned_by)
            )
            
            return attendance_id
        
        except Exception as e:
            self.logger.error(f"Failed to record attendance: {str(e)}")
            return None
    
    def get_recent_attendance(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent attendance records across all rooms and students.
        
        Args:
            limit (int): Number of records to retrieve
        
        Returns:
            List[Dict[str, Any]]: Recent attendance records
        """
        try:
            return self.db.execute_query(
                """SELECT a.*, 
                          s.student_id, s.first_name, s.last_name, s.department, 
                          s.year_level, s.section,
                          r.room_name, r.room_code, r.building,
                          sub.subject_name, sub.subject_code,
                          u.full_name as scanned_by_name
                   FROM attendance a
                   JOIN students s ON a.student_id = s.id
                   JOIN rooms r ON a.room_id = r.id
                   LEFT JOIN subjects sub ON a.subject_id = sub.id
                   LEFT JOIN users u ON a.scanned_by = u.id
                   ORDER BY a.created_at DESC
                   LIMIT ?""",
                (limit,)
            )
        except Exception as e:
            self.logger.error(f"Failed to get recent attendance: {str(e)}")
            return []
    
    def get_today_attendance_summary(self) -> Dict[str, Any]:
        """
        Get attendance summary for today.
        
        Returns:
            Dict[str, Any]: Today's attendance summary
        """
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Get total scans today
            total_scans = self.db.execute_query(
                "SELECT COUNT(*) as count FROM attendance WHERE scan_date = ?",
                (today,),
                fetch_all=False
            )['count']
            
            # Get status breakdown
            status_breakdown = self.db.execute_query(
                """SELECT status, COUNT(*) as count 
                   FROM attendance 
                   WHERE scan_date = ? 
                   GROUP BY status""",
                (today,)
            )
            
            # Get room-wise attendance
            room_breakdown = self.db.execute_query(
                """SELECT r.room_name, r.room_code, COUNT(a.id) as attendance_count
                   FROM rooms r
                   LEFT JOIN attendance a ON r.id = a.room_id AND a.scan_date = ?
                   WHERE r.is_active = 1
                   GROUP BY r.id, r.room_name, r.room_code
                   ORDER BY attendance_count DESC""",
                (today,)
            )
            
            # Get department-wise attendance
            dept_breakdown = self.db.execute_query(
                """SELECT s.department, COUNT(a.id) as attendance_count
                   FROM students s
                   JOIN attendance a ON s.id = a.student_id
                   WHERE a.scan_date = ?
                   GROUP BY s.department
                   ORDER BY attendance_count DESC""",
                (today,)
            )
            
            return {
                'date': today,
                'total_scans': total_scans,
                'status_breakdown': status_breakdown,
                'room_breakdown': room_breakdown,
                'department_breakdown': dept_breakdown
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get today's attendance summary: {str(e)}")
            return {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_scans': 0,
                'status_breakdown': [],
                'room_breakdown': [],
                'department_breakdown': []
            }
    
    def get_student_attendance_history(self, student_id: str, 
                                     days: int = 30) -> List[Dict[str, Any]]:
        """
        Get attendance history for a specific student.
        
        Args:
            student_id (str): Student ID
            days (int): Number of days to look back
        
        Returns:
            List[Dict[str, Any]]: Student's attendance history
        """
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            return self.db.execute_query(
                """SELECT a.*, r.room_name, r.room_code, r.building,
                          sub.subject_name, sub.subject_code
                   FROM attendance a
                   JOIN students s ON a.student_id = s.id
                   JOIN rooms r ON a.room_id = r.id
                   LEFT JOIN subjects sub ON a.subject_id = sub.id
                   WHERE s.student_id = ? AND a.scan_date >= ?
                   ORDER BY a.scan_date DESC, a.scan_time DESC""",
                (student_id, start_date)
            )
        
        except Exception as e:
            self.logger.error(f"Failed to get student attendance history: {str(e)}")
            return []
    
    def get_room_attendance_report(self, room_id: int, 
                                  start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Generate attendance report for a specific room and date range.
        
        Args:
            room_id (int): Room ID
            start_date (str): Start date (YYYY-MM-DD)
            end_date (str): End date (YYYY-MM-DD)
        
        Returns:
            Dict[str, Any]: Room attendance report
        """
        try:
            # Get room information
            room_info = self._get_room_by_id(room_id)
            if not room_info:
                return {'error': 'Room not found'}
            
            # Get attendance records for the date range
            attendance_records = self.db.execute_query(
                """SELECT a.*, s.student_id, s.first_name, s.last_name, 
                          s.department, s.year_level, s.section,
                          sub.subject_name, sub.subject_code
                   FROM attendance a
                   JOIN students s ON a.student_id = s.id
                   LEFT JOIN subjects sub ON a.subject_id = sub.id
                   WHERE a.room_id = ? AND a.scan_date BETWEEN ? AND ?
                   ORDER BY a.scan_date DESC, a.scan_time DESC""",
                (room_id, start_date, end_date)
            )
            
            # Calculate statistics
            total_attendance = len(attendance_records)
            unique_students = len(set(record['student_id'] for record in attendance_records))
            
            status_counts = {}
            for record in attendance_records:
                status = record['status']
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Daily breakdown
            daily_breakdown = {}
            for record in attendance_records:
                date = record['scan_date']
                if date not in daily_breakdown:
                    daily_breakdown[date] = {'total': 0, 'present': 0, 'late': 0}
                
                daily_breakdown[date]['total'] += 1
                if record['status'] in ['present', 'late']:
                    daily_breakdown[date][record['status']] += 1
            
            return {
                'room_info': room_info,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'statistics': {
                    'total_attendance': total_attendance,
                    'unique_students': unique_students,
                    'status_counts': status_counts
                },
                'daily_breakdown': daily_breakdown,
                'attendance_records': attendance_records
            }
        
        except Exception as e:
            self.logger.error(f"Failed to generate room attendance report: {str(e)}")
            return {'error': str(e)}
    
    def update_attendance_status(self, attendance_id: int, new_status: str, 
                                notes: str = None, updated_by: int = None) -> bool:
        """
        Update attendance record status and add notes.
        
        Args:
            attendance_id (int): Attendance record ID
            new_status (str): New attendance status
            notes (str): Optional notes
            updated_by (int): ID of user making the update
        
        Returns:
            bool: Success status
        """
        try:
            # Validate status
            valid_statuses = [self.STATUS_PRESENT, self.STATUS_LATE, self.STATUS_ABSENT, self.STATUS_EXCUSED]
            if new_status not in valid_statuses:
                self.logger.error(f"Invalid attendance status: {new_status}")
                return False
            
            # Update attendance record
            affected_rows = self.db.execute_update(
                """UPDATE attendance 
                   SET status = ?, notes = COALESCE(?, notes), 
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (new_status, notes, attendance_id)
            )
            
            if affected_rows > 0:
                self.logger.info(f"Attendance record {attendance_id} updated to status: {new_status}")
                return True
            else:
                self.logger.warning(f"No attendance record found with ID: {attendance_id}")
                return False
        
        except Exception as e:
            self.logger.error(f"Failed to update attendance status: {str(e)}")
            return False
    
    def get_attendance_trends(self, days: int = 30) -> Dict[str, Any]:
        """
        Get attendance trends and analytics for the specified number of days.
        
        Args:
            days (int): Number of days to analyze
        
        Returns:
            Dict[str, Any]: Attendance trends and analytics
        """
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            # Daily attendance counts
            daily_counts = self.db.execute_query(
                """SELECT scan_date, COUNT(*) as daily_count,
                          SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) as present_count,
                          SUM(CASE WHEN status = 'late' THEN 1 ELSE 0 END) as late_count
                   FROM attendance 
                   WHERE scan_date BETWEEN ? AND ?
                   GROUP BY scan_date
                   ORDER BY scan_date""",
                (start_date, end_date)
            )
            
            # Peak hours analysis
            hourly_distribution = self.db.execute_query(
                """SELECT CAST(SUBSTR(scan_time, 1, 2) AS INTEGER) as hour,
                          COUNT(*) as scan_count
                   FROM attendance 
                   WHERE scan_date BETWEEN ? AND ?
                   GROUP BY hour
                   ORDER BY hour""",
                (start_date, end_date)
            )
            
            # Department trends
            department_trends = self.db.execute_query(
                """SELECT s.department, COUNT(a.id) as attendance_count,
                          AVG(CASE WHEN a.status = 'late' THEN 1.0 ELSE 0.0 END) as late_rate
                   FROM students s
                   JOIN attendance a ON s.id = a.student_id
                   WHERE a.scan_date BETWEEN ? AND ?
                   GROUP BY s.department
                   ORDER BY attendance_count DESC""",
                (start_date, end_date)
            )
            
            return {
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'days_analyzed': days
                },
                'daily_counts': daily_counts,
                'hourly_distribution': hourly_distribution,
                'department_trends': department_trends
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get attendance trends: {str(e)}")
            return {
                'error': str(e),
                'date_range': {
                    'start_date': start_date if 'start_date' in locals() else None,
                    'end_date': end_date if 'end_date' in locals() else None,
                    'days_analyzed': days
                }
            }