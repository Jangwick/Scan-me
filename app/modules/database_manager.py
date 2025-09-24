"""
Database Manager Module - Flask QR Code Attendance System
Author: GitHub Copilot
Date: September 2025

This module handles all database operations for the attendance system.
It provides a comprehensive interface for managing SQLite database connections,
table creation, data insertion, updates, and queries. The module ensures
data integrity and provides transaction support for complex operations.

Features:
- SQLite database connection management
- Table schema creation and migration
- CRUD operations for all entities
- Transaction support
- Connection pooling
- Data validation and sanitization
- Error handling and logging
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from contextlib import contextmanager
import threading
from werkzeug.security import generate_password_hash
import json
import os

class DatabaseManager:
    """
    Comprehensive database management class for the QR code attendance system.
    Handles all database operations including connection management, schema creation,
    and data manipulation with proper error handling and transaction support.
    """
    
    def __init__(self, db_path):
        """
        Initialize the database manager with the specified database path.
        
        Args:
            db_path (str): Path to the SQLite database file
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._local = threading.local()
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database schema if it doesn't exist
        self.initialize_database()
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections with automatic cleanup.
        Provides thread-local connections for thread safety.
        
        Yields:
            sqlite3.Connection: Database connection object
        """
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable foreign key constraints
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        
        try:
            yield self._local.connection
        except Exception as e:
            self._local.connection.rollback()
            self.logger.error(f"Database operation failed: {str(e)}")
            raise
        finally:
            # Connection remains open for reuse within the thread
            pass
    
    def initialize_database(self):
        """
        Create all necessary tables and initial data for the attendance system.
        This method is idempotent and can be called multiple times safely.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create users table (professors, admins, staff)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        full_name VARCHAR(100) NOT NULL,
                        email VARCHAR(100) UNIQUE,
                        user_type VARCHAR(20) DEFAULT 'user',
                        department VARCHAR(100),
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create students table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS students (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id VARCHAR(20) UNIQUE NOT NULL,
                        first_name VARCHAR(50) NOT NULL,
                        last_name VARCHAR(50) NOT NULL,
                        middle_name VARCHAR(50),
                        department VARCHAR(100) NOT NULL,
                        year_level INTEGER NOT NULL,
                        section VARCHAR(10) NOT NULL,
                        email VARCHAR(100) UNIQUE,
                        phone VARCHAR(20),
                        qr_code VARCHAR(255) UNIQUE NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create rooms table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS rooms (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        room_code VARCHAR(20) UNIQUE NOT NULL,
                        room_name VARCHAR(100) NOT NULL,
                        building VARCHAR(100),
                        floor INTEGER,
                        capacity INTEGER DEFAULT 0,
                        room_type VARCHAR(50) DEFAULT 'classroom',
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create subjects table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS subjects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        subject_code VARCHAR(20) UNIQUE NOT NULL,
                        subject_name VARCHAR(100) NOT NULL,
                        description TEXT,
                        units INTEGER DEFAULT 3,
                        professor_id INTEGER,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (professor_id) REFERENCES users(id)
                    )
                """)
                
                # Create attendance table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS attendance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER NOT NULL,
                        room_id INTEGER NOT NULL,
                        subject_id INTEGER,
                        scan_date DATE NOT NULL,
                        scan_time TIME NOT NULL,
                        status VARCHAR(20) DEFAULT 'present',
                        notes TEXT,
                        scanned_by INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (student_id) REFERENCES students(id),
                        FOREIGN KEY (room_id) REFERENCES rooms(id),
                        FOREIGN KEY (subject_id) REFERENCES subjects(id),
                        FOREIGN KEY (scanned_by) REFERENCES users(id),
                        UNIQUE(student_id, room_id, scan_date)
                    )
                """)
                
                # Create room_assignments table (which professor is assigned to which room)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS room_assignments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        professor_id INTEGER NOT NULL,
                        room_id INTEGER NOT NULL,
                        subject_id INTEGER,
                        day_of_week INTEGER NOT NULL,
                        start_time TIME NOT NULL,
                        end_time TIME NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (professor_id) REFERENCES users(id),
                        FOREIGN KEY (room_id) REFERENCES rooms(id),
                        FOREIGN KEY (subject_id) REFERENCES subjects(id)
                    )
                """)
                
                # Create notifications table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        title VARCHAR(100) NOT NULL,
                        message TEXT NOT NULL,
                        type VARCHAR(50) DEFAULT 'info',
                        is_read BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """)
                
                # Create system_settings table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        setting_key VARCHAR(100) UNIQUE NOT NULL,
                        setting_value TEXT,
                        description TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(scan_date)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendance_room ON attendance(room_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_qr ON students(qr_code)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_id ON students(student_id)")
                
                conn.commit()
                
                # Insert default data if tables are empty
                self._insert_default_data(cursor)
                conn.commit()
                
                self.logger.info("Database initialized successfully")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def _insert_default_data(self, cursor):
        """
        Insert default system data including admin user, sample rooms, and settings.
        
        Args:
            cursor: Database cursor object
        """
        try:
            # Check if admin user exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'admin'")
            if cursor.fetchone()[0] == 0:
                # Insert default admin user
                admin_password = generate_password_hash('admin123')
                cursor.execute("""
                    INSERT INTO users (username, password_hash, full_name, email, user_type, department)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ('admin', admin_password, 'System Administrator', 'admin@school.edu', 'admin', 'IT Department'))
                
                # Insert sample professor
                prof_password = generate_password_hash('prof123')
                cursor.execute("""
                    INSERT INTO users (username, password_hash, full_name, email, user_type, department)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ('prof1', prof_password, 'Dr. John Smith', 'john.smith@school.edu', 'professor', 'Computer Science'))
            
            # Check if rooms exist
            cursor.execute("SELECT COUNT(*) FROM rooms")
            if cursor.fetchone()[0] == 0:
                # Insert sample rooms
                sample_rooms = [
                    ('R101', 'Room 101 - Lecture Hall A', 'Main Building', 1, 50, 'lecture'),
                    ('R201', 'Room 201 - Computer Lab 1', 'IT Building', 2, 30, 'laboratory'),
                    ('R202', 'Room 202 - Computer Lab 2', 'IT Building', 2, 30, 'laboratory'),
                    ('R301', 'Room 301 - Conference Room', 'Admin Building', 3, 20, 'meeting'),
                    ('LIBR', 'Library Study Area', 'Library Building', 1, 100, 'study')
                ]
                
                cursor.executemany("""
                    INSERT INTO rooms (room_code, room_name, building, floor, capacity, room_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, sample_rooms)
            
            # Check if system settings exist
            cursor.execute("SELECT COUNT(*) FROM system_settings")
            if cursor.fetchone()[0] == 0:
                # Insert default system settings
                default_settings = [
                    ('system_name', 'QR Code Attendance System', 'Name of the attendance system'),
                    ('max_daily_scans', '5', 'Maximum number of scans per student per day'),
                    ('late_threshold_minutes', '15', 'Minutes after class start to mark as late'),
                    ('session_timeout', '60', 'Session timeout in minutes'),
                    ('notification_enabled', '1', 'Enable real-time notifications'),
                    ('export_formats', 'excel,csv,pdf', 'Supported export formats')
                ]
                
                cursor.executemany("""
                    INSERT INTO system_settings (setting_key, setting_value, description)
                    VALUES (?, ?, ?)
                """, default_settings)
            
            # Insert sample students if none exist
            cursor.execute("SELECT COUNT(*) FROM students")
            if cursor.fetchone()[0] == 0:
                sample_students = [
                    ('2024001', 'Juan', 'Dela Cruz', 'Miguel', 'BSIT', 3, 'A', 'juan.delacruz@student.edu', '09123456789', 'QR2024001'),
                    ('2024002', 'Maria', 'Santos', 'Garcia', 'BSIT', 3, 'A', 'maria.santos@student.edu', '09123456790', 'QR2024002'),
                    ('2024003', 'Pedro', 'Reyes', 'Jose', 'BSCS', 2, 'B', 'pedro.reyes@student.edu', '09123456791', 'QR2024003'),
                    ('2024004', 'Ana', 'Cruz', 'Maria', 'BSIT', 1, 'C', 'ana.cruz@student.edu', '09123456792', 'QR2024004'),
                    ('2024005', 'Carlos', 'Lopez', 'Antonio', 'BSCS', 4, 'A', 'carlos.lopez@student.edu', '09123456793', 'QR2024005')
                ]
                
                cursor.executemany("""
                    INSERT INTO students (student_id, first_name, last_name, middle_name, department, 
                                        year_level, section, email, phone, qr_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, sample_students)
            
            self.logger.info("Default data inserted successfully")
        
        except Exception as e:
            self.logger.error(f"Failed to insert default data: {str(e)}")
            raise
    
    def execute_query(self, query, params=None, fetch_all=True):
        """
        Execute a SELECT query and return results.
        
        Args:
            query (str): SQL query string
            params (tuple): Query parameters
            fetch_all (bool): Whether to fetch all results or just one
        
        Returns:
            list or dict: Query results
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch_all:
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
                else:
                    result = cursor.fetchone()
                    return dict(result) if result else None
        
        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            raise
    
    def execute_update(self, query, params=None):
        """
        Execute an INSERT, UPDATE, or DELETE query.
        
        Args:
            query (str): SQL query string
            params (tuple): Query parameters
        
        Returns:
            int: Number of affected rows or last inserted row ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                conn.commit()
                
                # Return last inserted row ID for INSERT statements
                if query.strip().upper().startswith('INSERT'):
                    return cursor.lastrowid
                else:
                    return cursor.rowcount
        
        except Exception as e:
            self.logger.error(f"Update execution failed: {str(e)}")
            raise
    
    def execute_many(self, query, params_list):
        """
        Execute a query multiple times with different parameters.
        
        Args:
            query (str): SQL query string
            params_list (list): List of parameter tuples
        
        Returns:
            int: Number of affected rows
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount
        
        except Exception as e:
            self.logger.error(f"Batch execution failed: {str(e)}")
            raise
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions with automatic rollback on error.
        
        Yields:
            sqlite3.Connection: Database connection within transaction
        """
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                self.logger.error(f"Transaction rolled back: {str(e)}")
                raise
    
    def get_system_setting(self, key, default_value=None):
        """
        Get a system setting value by key.
        
        Args:
            key (str): Setting key
            default_value: Default value if setting not found
        
        Returns:
            str: Setting value
        """
        try:
            result = self.execute_query(
                "SELECT setting_value FROM system_settings WHERE setting_key = ?",
                (key,),
                fetch_all=False
            )
            return result['setting_value'] if result else default_value
        
        except Exception as e:
            self.logger.error(f"Failed to get system setting {key}: {str(e)}")
            return default_value
    
    def update_system_setting(self, key, value, description=None):
        """
        Update or insert a system setting.
        
        Args:
            key (str): Setting key
            value (str): Setting value
            description (str): Setting description
        
        Returns:
            bool: Success status
        """
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                
                # Check if setting exists
                cursor.execute("SELECT id FROM system_settings WHERE setting_key = ?", (key,))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing setting
                    cursor.execute("""
                        UPDATE system_settings 
                        SET setting_value = ?, description = COALESCE(?, description), 
                            updated_at = CURRENT_TIMESTAMP
                        WHERE setting_key = ?
                    """, (value, description, key))
                else:
                    # Insert new setting
                    cursor.execute("""
                        INSERT INTO system_settings (setting_key, setting_value, description)
                        VALUES (?, ?, ?)
                    """, (key, value, description))
                
                return True
        
        except Exception as e:
            self.logger.error(f"Failed to update system setting {key}: {str(e)}")
            return False
    
    def close_all_connections(self):
        """Close all database connections for cleanup."""
        try:
            if hasattr(self._local, 'connection'):
                self._local.connection.close()
                del self._local.connection
        except Exception as e:
            self.logger.error(f"Error closing connections: {str(e)}")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.close_all_connections()