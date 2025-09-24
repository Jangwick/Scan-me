"""
Student Manager Module - Flask QR Code Attendance System
Author: GitHub Copilot
Date: September 2025

This module handles student management operations for the attendance system.
It provides comprehensive student administration including student registration,
profile management, QR code generation, attendance tracking, and analytics.

Features:
- Student registration and profile management
- QR code generation and management
- Student information updates
- Attendance history tracking
- Academic performance analytics
- Department and section management
- Bulk student operations
- Student data validation
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
import re
import csv
import io
from dataclasses import dataclass
from app.modules.qr_generator import QRGenerator

@dataclass
class StudentProfile:
    """Data structure for student profile information."""
    id: Optional[int]
    student_id: str
    first_name: str
    last_name: str
    middle_name: Optional[str]
    department: str
    year_level: int
    section: str
    email: Optional[str]
    phone: Optional[str]
    qr_code: str
    is_active: bool

class StudentManager:
    """
    Comprehensive student management system for the QR code attendance system.
    Handles all aspects of student administration and data management.
    """
    
    def __init__(self, database_manager):
        """
        Initialize the student manager with database connection.
        
        Args:
            database_manager: Database manager instance
        """
        self.db = database_manager
        self.qr_generator = QRGenerator()
        self.logger = logging.getLogger(__name__)
        
        # Academic year levels
        self.YEAR_LEVELS = {
            1: '1st Year',
            2: '2nd Year',
            3: '3rd Year',
            4: '4th Year',
            5: '5th Year'
        }
        
        # Common departments
        self.DEPARTMENTS = [
            'BSIT', 'BSCS', 'BSBA', 'BSED', 'BEED', 'BSHM', 'BSTM',
            'AB English', 'AB Psychology', 'BSN', 'BSME', 'BSCE', 'BSEE'
        ]
        
        # Common sections
        self.SECTIONS = ['A', 'B', 'C', 'D', 'E', 'F']
        
        self.logger.info("Student manager initialized")
    
    def create_student(self, student_data: Dict[str, Any], 
                      created_by: int = None) -> Dict[str, Any]:
        """
        Create a new student record with QR code generation.
        
        Args:
            student_data (Dict[str, Any]): Student information
            created_by (int): ID of user creating the student
        
        Returns:
            Dict[str, Any]: Creation result
        """
        try:
            # Validate required fields
            required_fields = ['student_id', 'first_name', 'last_name', 'department', 'year_level', 'section']
            for field in required_fields:
                if not student_data.get(field):
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }
            
            # Validate student data
            validation_result = self._validate_student_data(student_data)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error']
                }
            
            # Check if student ID already exists
            existing_student = self.db.execute_query(
                "SELECT id FROM students WHERE student_id = ?",
                (student_data['student_id'],),
                fetch_all=False
            )
            
            if existing_student:
                return {
                    'success': False,
                    'error': 'Student ID already exists'
                }
            
            # Check if email already exists (if provided)
            if student_data.get('email'):
                existing_email = self.db.execute_query(
                    "SELECT id FROM students WHERE email = ?",
                    (student_data['email'],),
                    fetch_all=False
                )
                
                if existing_email:
                    return {
                        'success': False,
                        'error': 'Email address already exists'
                    }
            
            # Generate unique QR code
            qr_code = self._generate_unique_qr_code(student_data['student_id'])
            
            # Insert new student
            student_id = self.db.execute_update(
                """INSERT INTO students (student_id, first_name, last_name, middle_name,
                                       department, year_level, section, email, phone, qr_code,
                                       created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                (
                    student_data['student_id'],
                    student_data['first_name'],
                    student_data['last_name'],
                    student_data.get('middle_name'),
                    student_data['department'],
                    student_data['year_level'],
                    student_data['section'],
                    student_data.get('email'),
                    student_data.get('phone'),
                    qr_code
                )
            )
            
            # Generate QR code image
            qr_result = self.qr_generator.generate_student_qr_code(
                {
                    'id': student_id,
                    'student_id': student_data['student_id'],
                    'first_name': student_data['first_name'],
                    'last_name': student_data['last_name'],
                    'department': student_data['department'],
                    'year_level': student_data['year_level'],
                    'section': student_data['section']
                },
                style='with_info'
            )
            
            self.logger.info(f"Student created successfully: {student_data['student_id']} (ID: {student_id})")
            
            return {
                'success': True,
                'student_id': student_id,
                'student_number': student_data['student_id'],
                'qr_code': qr_code,
                'qr_image': qr_result.get('image_base64') if qr_result.get('success') else None,
                'message': 'Student created successfully'
            }
        
        except Exception as e:
            self.logger.error(f"Student creation failed for {student_data.get('student_id', 'unknown')}: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to create student record'
            }
    
    def update_student(self, student_id: int, update_data: Dict[str, Any],
                      updated_by: int = None) -> Dict[str, Any]:
        """
        Update student information.
        
        Args:
            student_id (int): Student database ID
            update_data (Dict[str, Any]): Updated student data
            updated_by (int): ID of user making the update
        
        Returns:
            Dict[str, Any]: Update result
        """
        try:
            # Check if student exists
            existing_student = self.db.execute_query(
                "SELECT * FROM students WHERE id = ?",
                (student_id,),
                fetch_all=False
            )
            
            if not existing_student:
                return {
                    'success': False,
                    'error': 'Student not found'
                }
            
            # Build update query
            update_fields = []
            params = []
            
            # Map of allowed fields to update
            allowed_fields = {
                'first_name': 'first_name',
                'last_name': 'last_name',
                'middle_name': 'middle_name',
                'department': 'department',
                'year_level': 'year_level',
                'section': 'section',
                'email': 'email',
                'phone': 'phone',
                'is_active': 'is_active'
            }
            
            # Validate update data
            if any(field in update_data for field in ['department', 'year_level', 'section']):
                validation_result = self._validate_student_data(update_data, partial=True)
                if not validation_result['valid']:
                    return {
                        'success': False,
                        'error': validation_result['error']
                    }
            
            # Check for email uniqueness if updating email
            if 'email' in update_data and update_data['email']:
                existing_email = self.db.execute_query(
                    "SELECT id FROM students WHERE email = ? AND id != ?",
                    (update_data['email'], student_id),
                    fetch_all=False
                )
                
                if existing_email:
                    return {
                        'success': False,
                        'error': 'Email address already exists'
                    }
            
            for field, db_field in allowed_fields.items():
                if field in update_data:
                    update_fields.append(f"{db_field} = ?")
                    params.append(update_data[field])
            
            if not update_fields:
                return {
                    'success': False,
                    'error': 'No valid fields to update'
                }
            
            # Add updated timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(student_id)
            
            # Execute update
            query = f"UPDATE students SET {', '.join(update_fields)} WHERE id = ?"
            affected_rows = self.db.execute_update(query, params)
            
            if affected_rows > 0:
                self.logger.info(f"Student {student_id} updated successfully")
                return {
                    'success': True,
                    'message': 'Student information updated successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'No changes made to student record'
                }
        
        except Exception as e:
            self.logger.error(f"Student update failed for ID {student_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to update student information'
            }
    
    def delete_student(self, student_id: int, deleted_by: int = None) -> bool:
        """
        Soft delete a student (mark as inactive).
        
        Args:
            student_id (int): Student database ID
            deleted_by (int): ID of user deleting the student
        
        Returns:
            bool: Success status
        """
        try:
            # Check if student has attendance records
            has_attendance = self.db.execute_query(
                "SELECT COUNT(*) as count FROM attendance WHERE student_id = ?",
                (student_id,),
                fetch_all=False
            )['count'] > 0
            
            if has_attendance:
                # Soft delete - mark as inactive
                affected_rows = self.db.execute_update(
                    "UPDATE students SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (student_id,)
                )
            else:
                # Hard delete if no attendance records
                affected_rows = self.db.execute_update(
                    "DELETE FROM students WHERE id = ?",
                    (student_id,)
                )
            
            if affected_rows > 0:
                self.logger.info(f"Student {student_id} deleted by user {deleted_by}")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Failed to delete student {student_id}: {str(e)}")
            return False
    
    def get_all_students(self, include_inactive: bool = False,
                        department: str = None, year_level: int = None) -> List[Dict[str, Any]]:
        """
        Get all students with optional filters.
        
        Args:
            include_inactive (bool): Include inactive students
            department (str): Filter by department
            year_level (int): Filter by year level
        
        Returns:
            List[Dict[str, Any]]: List of students
        """
        try:
            where_conditions = []
            params = []
            
            if not include_inactive:
                where_conditions.append("s.is_active = 1")
            
            if department:
                where_conditions.append("s.department = ?")
                params.append(department)
            
            if year_level:
                where_conditions.append("s.year_level = ?")
                params.append(year_level)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            return self.db.execute_query(f"""
                SELECT s.*, 
                       COUNT(a.id) as total_attendance,
                       MAX(a.created_at) as last_attendance,
                       ROUND(AVG(CASE WHEN a.status = 'present' THEN 100.0 ELSE 0.0 END), 2) as attendance_rate
                FROM students s
                LEFT JOIN attendance a ON s.id = a.student_id
                WHERE {where_clause}
                GROUP BY s.id, s.student_id, s.first_name, s.last_name, s.middle_name,
                         s.department, s.year_level, s.section, s.email, s.phone, 
                         s.qr_code, s.is_active, s.created_at, s.updated_at
                ORDER BY s.department, s.year_level, s.section, s.last_name, s.first_name
            """, params)
        
        except Exception as e:
            self.logger.error(f"Failed to get students: {str(e)}")
            return []
    
    def get_student_by_id(self, student_id: int) -> Optional[Dict[str, Any]]:
        """
        Get student by database ID.
        
        Args:
            student_id (int): Student database ID
        
        Returns:
            Dict[str, Any]: Student information or None
        """
        try:
            return self.db.execute_query(
                """SELECT s.*, 
                          COUNT(a.id) as total_attendance,
                          MAX(a.created_at) as last_attendance,
                          ROUND(AVG(CASE WHEN a.status = 'present' THEN 100.0 ELSE 0.0 END), 2) as attendance_rate
                   FROM students s
                   LEFT JOIN attendance a ON s.id = a.student_id
                   WHERE s.id = ?
                   GROUP BY s.id""",
                (student_id,),
                fetch_all=False
            )
        
        except Exception as e:
            self.logger.error(f"Failed to get student {student_id}: {str(e)}")
            return None
    
    def get_student_by_number(self, student_number: str) -> Optional[Dict[str, Any]]:
        """
        Get student by student number/ID.
        
        Args:
            student_number (str): Student number
        
        Returns:
            Dict[str, Any]: Student information or None
        """
        try:
            return self.db.execute_query(
                """SELECT s.*, 
                          COUNT(a.id) as total_attendance,
                          MAX(a.created_at) as last_attendance,
                          ROUND(AVG(CASE WHEN a.status = 'present' THEN 100.0 ELSE 0.0 END), 2) as attendance_rate
                   FROM students s
                   LEFT JOIN attendance a ON s.id = a.student_id
                   WHERE s.student_id = ? AND s.is_active = 1
                   GROUP BY s.id""",
                (student_number,),
                fetch_all=False
            )
        
        except Exception as e:
            self.logger.error(f"Failed to get student by number {student_number}: {str(e)}")
            return None
    
    def get_student_count(self, department: str = None, active_only: bool = True) -> int:
        """
        Get count of students.
        
        Args:
            department (str): Filter by department
            active_only (bool): Count only active students
        
        Returns:
            int: Number of students
        """
        try:
            where_conditions = []
            params = []
            
            if active_only:
                where_conditions.append("is_active = 1")
            
            if department:
                where_conditions.append("department = ?")
                params.append(department)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            result = self.db.execute_query(
                f"SELECT COUNT(*) as count FROM students WHERE {where_clause}",
                params,
                fetch_all=False
            )
            return result['count'] if result else 0
        
        except Exception as e:
            self.logger.error(f"Failed to get student count: {str(e)}")
            return 0
    
    def get_students_by_department(self, department: str) -> List[Dict[str, Any]]:
        """
        Get students in a specific department.
        
        Args:
            department (str): Department name
        
        Returns:
            List[Dict[str, Any]]: Students in the department
        """
        try:
            return self.db.execute_query(
                """SELECT * FROM students 
                   WHERE department = ? AND is_active = 1 
                   ORDER BY year_level, section, last_name, first_name""",
                (department,)
            )
        
        except Exception as e:
            self.logger.error(f"Failed to get students for department {department}: {str(e)}")
            return []
    
    def get_student_attendance_summary(self, student_id: int, 
                                     days: int = 30) -> Dict[str, Any]:
        """
        Get attendance summary for a specific student.
        
        Args:
            student_id (int): Student database ID
            days (int): Number of days to look back
        
        Returns:
            Dict[str, Any]: Attendance summary
        """
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Get attendance records
            attendance_records = self.db.execute_query(
                """SELECT a.*, r.room_name, r.room_code, r.building
                   FROM attendance a
                   JOIN rooms r ON a.room_id = r.id
                   WHERE a.student_id = ? AND a.scan_date >= ?
                   ORDER BY a.scan_date DESC, a.scan_time DESC""",
                (student_id, start_date)
            )
            
            # Calculate statistics
            total_scans = len(attendance_records)
            present_count = len([r for r in attendance_records if r['status'] == 'present'])
            late_count = len([r for r in attendance_records if r['status'] == 'late'])
            
            attendance_rate = (present_count / total_scans * 100) if total_scans > 0 else 0
            late_rate = (late_count / total_scans * 100) if total_scans > 0 else 0
            
            # Get unique rooms visited
            unique_rooms = len(set(r['room_id'] for r in attendance_records))
            
            # Get recent activity
            recent_activity = attendance_records[:10]
            
            return {
                'student_id': student_id,
                'date_range': {
                    'start_date': start_date,
                    'end_date': datetime.now().strftime('%Y-%m-%d'),
                    'days': days
                },
                'statistics': {
                    'total_scans': total_scans,
                    'present_count': present_count,
                    'late_count': late_count,
                    'attendance_rate': round(attendance_rate, 2),
                    'late_rate': round(late_rate, 2),
                    'unique_rooms': unique_rooms
                },
                'recent_activity': recent_activity,
                'attendance_records': attendance_records
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get attendance summary for student {student_id}: {str(e)}")
            return {
                'student_id': student_id,
                'error': str(e)
            }
    
    def regenerate_student_qr_code(self, student_id: int, 
                                  regenerated_by: int = None) -> Dict[str, Any]:
        """
        Regenerate QR code for a student.
        
        Args:
            student_id (int): Student database ID
            regenerated_by (int): ID of user regenerating the QR code
        
        Returns:
            Dict[str, Any]: Regeneration result
        """
        try:
            # Get student information
            student = self.get_student_by_id(student_id)
            if not student:
                return {
                    'success': False,
                    'error': 'Student not found'
                }
            
            # Generate new QR code
            new_qr_code = self._generate_unique_qr_code(student['student_id'])
            
            # Update database
            affected_rows = self.db.execute_update(
                "UPDATE students SET qr_code = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_qr_code, student_id)
            )
            
            if affected_rows > 0:
                # Generate QR code image
                qr_result = self.qr_generator.generate_student_qr_code(
                    {
                        'id': student['id'],
                        'student_id': student['student_id'],
                        'first_name': student['first_name'],
                        'last_name': student['last_name'],
                        'department': student['department'],
                        'year_level': student['year_level'],
                        'section': student['section']
                    },
                    style='with_info'
                )
                
                self.logger.info(f"QR code regenerated for student {student_id}")
                
                return {
                    'success': True,
                    'qr_code': new_qr_code,
                    'qr_image': qr_result.get('image_base64') if qr_result.get('success') else None,
                    'message': 'QR code regenerated successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to update QR code in database'
                }
        
        except Exception as e:
            self.logger.error(f"QR code regeneration failed for student {student_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to regenerate QR code'
            }
    
    def bulk_create_students(self, students_data: List[Dict[str, Any]], 
                            created_by: int = None) -> Dict[str, Any]:
        """
        Create multiple students in bulk operation.
        
        Args:
            students_data (List[Dict[str, Any]]): List of student data
            created_by (int): ID of user creating the students
        
        Returns:
            Dict[str, Any]: Bulk creation result
        """
        try:
            results = {
                'success': True,
                'total_students': len(students_data),
                'created': 0,
                'failed': 0,
                'errors': [],
                'created_students': []
            }
            
            for i, student_data in enumerate(students_data):
                try:
                    result = self.create_student(student_data, created_by)
                    
                    if result['success']:
                        results['created'] += 1
                        results['created_students'].append({
                            'row': i + 1,
                            'student_id': result['student_number'],
                            'name': f"{student_data['first_name']} {student_data['last_name']}"
                        })
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'row': i + 1,
                            'student_id': student_data.get('student_id', 'unknown'),
                            'error': result['error']
                        })
                
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'row': i + 1,
                        'student_id': student_data.get('student_id', 'unknown'),
                        'error': str(e)
                    })
            
            if results['failed'] > 0:
                results['success'] = False
            
            self.logger.info(f"Bulk student creation completed: {results['created']}/{results['total_students']} successful")
            return results
        
        except Exception as e:
            self.logger.error(f"Bulk student creation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'total_students': len(students_data) if students_data else 0,
                'created': 0,
                'failed': len(students_data) if students_data else 0
            }
    
    def import_students_from_csv(self, csv_content: str, 
                                created_by: int = None) -> Dict[str, Any]:
        """
        Import students from CSV content.
        
        Args:
            csv_content (str): CSV content as string
            created_by (int): ID of user importing the students
        
        Returns:
            Dict[str, Any]: Import result
        """
        try:
            # Parse CSV content
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            students_data = []
            
            # Expected CSV columns
            expected_columns = ['student_id', 'first_name', 'last_name', 'department', 'year_level', 'section']
            optional_columns = ['middle_name', 'email', 'phone']
            
            for row_num, row in enumerate(csv_reader, start=2):  # Start from row 2 (accounting for header)
                try:
                    # Check required columns
                    missing_columns = [col for col in expected_columns if col not in row or not row[col].strip()]
                    if missing_columns:
                        return {
                            'success': False,
                            'error': f"Row {row_num}: Missing required columns: {', '.join(missing_columns)}"
                        }
                    
                    # Clean and validate data
                    student_data = {
                        'student_id': row['student_id'].strip(),
                        'first_name': row['first_name'].strip(),
                        'last_name': row['last_name'].strip(),
                        'department': row['department'].strip().upper(),
                        'year_level': int(row['year_level'].strip()),
                        'section': row['section'].strip().upper()
                    }
                    
                    # Add optional fields
                    for col in optional_columns:
                        if col in row and row[col].strip():
                            student_data[col] = row[col].strip()
                    
                    students_data.append(student_data)
                
                except ValueError as e:
                    return {
                        'success': False,
                        'error': f"Row {row_num}: Invalid data format - {str(e)}"
                    }
            
            if not students_data:
                return {
                    'success': False,
                    'error': 'No valid student data found in CSV'
                }
            
            # Perform bulk creation
            result = self.bulk_create_students(students_data, created_by)
            result['import_method'] = 'csv'
            
            return result
        
        except Exception as e:
            self.logger.error(f"CSV import failed: {str(e)}")
            return {
                'success': False,
                'error': f'CSV import failed: {str(e)}'
            }
    
    def _validate_student_data(self, student_data: Dict[str, Any], 
                              partial: bool = False) -> Dict[str, Any]:
        """
        Validate student data.
        
        Args:
            student_data (Dict[str, Any]): Student data to validate
            partial (bool): Whether this is a partial update
        
        Returns:
            Dict[str, Any]: Validation result
        """
        try:
            # Validate student ID format (if provided)
            if 'student_id' in student_data:
                student_id = student_data['student_id']
                if not re.match(r'^\d{4,10}$', student_id):
                    return {'valid': False, 'error': 'Student ID must be 4-10 digits'}
            
            # Validate names
            for name_field in ['first_name', 'last_name']:
                if name_field in student_data:
                    name = student_data[name_field]
                    if not name or len(name.strip()) < 2:
                        return {'valid': False, 'error': f'{name_field.replace("_", " ").title()} must be at least 2 characters'}
                    
                    if not re.match(r'^[a-zA-Z\s\'-]+$', name):
                        return {'valid': False, 'error': f'{name_field.replace("_", " ").title()} contains invalid characters'}
            
            # Validate year level
            if 'year_level' in student_data:
                year_level = student_data['year_level']
                if not isinstance(year_level, int) or year_level < 1 or year_level > 5:
                    return {'valid': False, 'error': 'Year level must be between 1 and 5'}
            
            # Validate section
            if 'section' in student_data:
                section = student_data['section']
                if not re.match(r'^[A-Z]$', section):
                    return {'valid': False, 'error': 'Section must be a single uppercase letter'}
            
            # Validate email format (if provided)
            if 'email' in student_data and student_data['email']:
                email = student_data['email']
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                    return {'valid': False, 'error': 'Invalid email address format'}
            
            # Validate phone number format (if provided)
            if 'phone' in student_data and student_data['phone']:
                phone = student_data['phone']
                if not re.match(r'^(\+63|0)?[9]\d{9}$', phone):
                    return {'valid': False, 'error': 'Invalid phone number format'}
            
            return {'valid': True}
        
        except Exception as e:
            return {'valid': False, 'error': f'Validation error: {str(e)}'}
    
    def _generate_unique_qr_code(self, student_id: str) -> str:
        """
        Generate unique QR code for student.
        
        Args:
            student_id (str): Student ID
        
        Returns:
            str: Unique QR code string
        """
        import secrets
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_suffix = secrets.token_hex(4)
        return f"QR{student_id}_{timestamp}_{random_suffix}"
    
    def get_departments(self) -> List[str]:
        """
        Get list of departments with students.
        
        Returns:
            List[str]: List of department names
        """
        try:
            results = self.db.execute_query(
                """SELECT DISTINCT department FROM students 
                   WHERE is_active = 1 AND department IS NOT NULL 
                   ORDER BY department"""
            )
            return [r['department'] for r in results]
        
        except Exception as e:
            self.logger.error(f"Failed to get departments: {str(e)}")
            return self.DEPARTMENTS
    
    def get_year_levels(self) -> List[Dict[str, Any]]:
        """
        Get available year levels.
        
        Returns:
            List[Dict[str, Any]]: Year levels with descriptions
        """
        return [{'value': k, 'label': v} for k, v in self.YEAR_LEVELS.items()]
    
    def get_sections(self) -> List[str]:
        """
        Get available sections.
        
        Returns:
            List[str]: Section letters
        """
        return self.SECTIONS
    
    def search_students(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search students by name, student ID, or department.
        
        Args:
            query (str): Search query
            limit (int): Maximum number of results
        
        Returns:
            List[Dict[str, Any]]: Search results
        """
        try:
            search_pattern = f"%{query}%"
            
            return self.db.execute_query(
                """SELECT * FROM students 
                   WHERE is_active = 1 
                   AND (student_id LIKE ? OR first_name LIKE ? OR last_name LIKE ? 
                        OR department LIKE ? OR CONCAT(first_name, ' ', last_name) LIKE ?)
                   ORDER BY 
                       CASE WHEN student_id = ? THEN 1
                            WHEN student_id LIKE ? THEN 2
                            WHEN CONCAT(first_name, ' ', last_name) LIKE ? THEN 3
                            ELSE 4 END,
                       last_name, first_name
                   LIMIT ?""",
                (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern,
                 query, f"{query}%", search_pattern, limit)
            )
        
        except Exception as e:
            self.logger.error(f"Student search failed: {str(e)}")
            return []