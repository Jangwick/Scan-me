"""
Authentication Manager Module - Flask QR Code Attendance System
Author: GitHub Copilot
Date: September 2025

This module handles user authentication, authorization, and session management
for the attendance system. It provides comprehensive security features including
password hashing, role-based access control, session management, and security logging.

Features:
- User authentication and authorization
- Password hashing and validation
- Role-based access control (RBAC)
- Session management
- Security logging and monitoring
- User account management
- Password policies and validation
- Login attempt tracking and lockout
"""

from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
import hashlib
import secrets
import re
from dataclasses import dataclass

@dataclass
class UserSession:
    """Data structure for user session information."""
    user_id: int
    username: str
    user_type: str
    full_name: str
    login_time: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str
    is_active: bool

class AuthManager:
    """
    Comprehensive authentication and authorization management system.
    Handles user login, session management, and security controls.
    """
    
    def __init__(self, database_manager):
        """
        Initialize the authentication manager with database connection.
        
        Args:
            database_manager: Database manager instance
        """
        self.db = database_manager
        self.logger = logging.getLogger(__name__)
        
        # User types and permissions
        self.USER_TYPES = {
            'ADMIN': 'admin',
            'PROFESSOR': 'professor',
            'STAFF': 'staff',
            'USER': 'user'
        }
        
        # Permission levels
        self.PERMISSIONS = {
            'admin': [
                'view_all_attendance', 'manage_users', 'manage_rooms', 
                'manage_students', 'generate_reports', 'system_settings',
                'view_analytics', 'manage_schedules', 'export_data'
            ],
            'professor': [
                'view_assigned_rooms', 'view_student_attendance', 'generate_reports',
                'mark_attendance', 'view_analytics', 'manage_schedules'
            ],
            'staff': [
                'scan_qr_codes', 'view_basic_reports', 'mark_attendance'
            ],
            'user': [
                'view_own_attendance', 'scan_qr_codes'
            ]
        }
        
        # Security settings
        self.security_config = {
            'password_min_length': 8,
            'password_require_uppercase': True,
            'password_require_lowercase': True,
            'password_require_numbers': True,
            'password_require_special': True,
            'max_login_attempts': 5,
            'lockout_duration_minutes': 30,
            'session_timeout_minutes': 60,
            'password_history_count': 5
        }
        
        # Active sessions cache
        self.active_sessions = {}
        
        # Failed login attempts tracking
        self.failed_attempts = {}
        
        self.logger.info("Authentication manager initialized")
    
    def authenticate_user(self, username: str, password: str, 
                         ip_address: str = None, user_agent: str = None) -> Optional[Dict[str, Any]]:
        """
        Authenticate user with username and password.
        
        Args:
            username (str): Username
            password (str): Password
            ip_address (str): Client IP address
            user_agent (str): Client user agent
        
        Returns:
            Dict[str, Any]: User information if authenticated, None otherwise
        """
        try:
            # Check if account is locked
            if self._is_account_locked(username):
                self.logger.warning(f"Authentication attempt for locked account: {username}")
                return None
            
            # Get user from database
            user = self.db.execute_query(
                "SELECT * FROM users WHERE username = ? AND is_active = 1",
                (username,),
                fetch_all=False
            )
            
            if not user:
                self._record_failed_attempt(username, ip_address)
                self.logger.warning(f"Authentication failed - user not found: {username}")
                return None
            
            # Verify password
            if not check_password_hash(user['password_hash'], password):
                self._record_failed_attempt(username, ip_address)
                self.logger.warning(f"Authentication failed - invalid password: {username}")
                return None
            
            # Clear failed attempts on successful login
            self._clear_failed_attempts(username)
            
            # Create user session
            session = self._create_user_session(user, ip_address, user_agent)
            
            # Log successful login
            self._log_login_event(user['id'], True, ip_address, user_agent)
            
            # Update last login time
            self.db.execute_update(
                "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (user['id'],)
            )
            
            self.logger.info(f"User authenticated successfully: {username}")
            
            return {
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'email': user['email'],
                'user_type': user['user_type'],
                'department': user['department'],
                'session_id': session.user_id,
                'permissions': self.get_user_permissions(user['user_type'])
            }
        
        except Exception as e:
            self.logger.error(f"Authentication error for user {username}: {str(e)}")
            return None
    
    def create_user(self, username: str, password: str, full_name: str,
                   email: str, user_type: str = 'user', department: str = None,
                   created_by: int = None) -> Dict[str, Any]:
        """
        Create a new user account.
        
        Args:
            username (str): Username
            password (str): Password
            full_name (str): Full name
            email (str): Email address
            user_type (str): User type/role
            department (str): Department
            created_by (int): ID of user creating this account
        
        Returns:
            Dict[str, Any]: Creation result
        """
        try:
            # Validate input parameters
            validation_result = self._validate_user_data(username, password, email)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error']
                }
            
            # Check if username already exists
            existing_user = self.db.execute_query(
                "SELECT id FROM users WHERE username = ?",
                (username,),
                fetch_all=False
            )
            
            if existing_user:
                return {
                    'success': False,
                    'error': 'Username already exists'
                }
            
            # Check if email already exists
            existing_email = self.db.execute_query(
                "SELECT id FROM users WHERE email = ?",
                (email,),
                fetch_all=False
            )
            
            if existing_email:
                return {
                    'success': False,
                    'error': 'Email address already exists'
                }
            
            # Hash password
            password_hash = generate_password_hash(password)
            
            # Insert new user
            user_id = self.db.execute_update(
                """INSERT INTO users (username, password_hash, full_name, email, 
                                    user_type, department, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                (username, password_hash, full_name, email, user_type, department)
            )
            
            # Log user creation
            self.logger.info(f"User created successfully: {username} (ID: {user_id})")
            
            return {
                'success': True,
                'user_id': user_id,
                'username': username,
                'message': 'User account created successfully'
            }
        
        except Exception as e:
            self.logger.error(f"User creation failed for {username}: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to create user account'
            }
    
    def update_password(self, user_id: int, current_password: str, 
                       new_password: str) -> Dict[str, Any]:
        """
        Update user password with validation.
        
        Args:
            user_id (int): User ID
            current_password (str): Current password
            new_password (str): New password
        
        Returns:
            Dict[str, Any]: Update result
        """
        try:
            # Get user information
            user = self.db.execute_query(
                "SELECT * FROM users WHERE id = ? AND is_active = 1",
                (user_id,),
                fetch_all=False
            )
            
            if not user:
                return {
                    'success': False,
                    'error': 'User not found or inactive'
                }
            
            # Verify current password
            if not check_password_hash(user['password_hash'], current_password):
                self.logger.warning(f"Password update failed - incorrect current password for user {user_id}")
                return {
                    'success': False,
                    'error': 'Current password is incorrect'
                }
            
            # Validate new password
            password_validation = self._validate_password(new_password)
            if not password_validation['valid']:
                return {
                    'success': False,
                    'error': password_validation['error']
                }
            
            # Check password history (if implemented)
            if self._is_password_in_history(user_id, new_password):
                return {
                    'success': False,
                    'error': 'New password cannot be the same as recent passwords'
                }
            
            # Hash new password
            new_password_hash = generate_password_hash(new_password)
            
            # Update password in database
            affected_rows = self.db.execute_update(
                "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_password_hash, user_id)
            )
            
            if affected_rows > 0:
                # Store in password history (if implemented)
                self._store_password_history(user_id, user['password_hash'])
                
                self.logger.info(f"Password updated successfully for user {user_id}")
                return {
                    'success': True,
                    'message': 'Password updated successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to update password'
                }
        
        except Exception as e:
            self.logger.error(f"Password update failed for user {user_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to update password'
            }
    
    def get_user_permissions(self, user_type: str) -> List[str]:
        """
        Get permissions for user type.
        
        Args:
            user_type (str): User type
        
        Returns:
            List[str]: List of permissions
        """
        return self.PERMISSIONS.get(user_type, self.PERMISSIONS['user'])
    
    def has_permission(self, user_type: str, permission: str) -> bool:
        """
        Check if user type has specific permission.
        
        Args:
            user_type (str): User type
            permission (str): Permission to check
        
        Returns:
            bool: True if user has permission
        """
        user_permissions = self.get_user_permissions(user_type)
        return permission in user_permissions
    
    def get_all_users(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Get all users in the system.
        
        Args:
            include_inactive (bool): Include inactive users
        
        Returns:
            List[Dict[str, Any]]: List of users
        """
        try:
            where_clause = "" if include_inactive else "WHERE is_active = 1"
            
            return self.db.execute_query(f"""
                SELECT id, username, full_name, email, user_type, department, 
                       is_active, created_at, updated_at
                FROM users 
                {where_clause}
                ORDER BY user_type, full_name
            """)
        
        except Exception as e:
            self.logger.error(f"Failed to get users: {str(e)}")
            return []
    
    def get_professor_count(self) -> int:
        """
        Get count of professors in the system.
        
        Returns:
            int: Number of professors
        """
        try:
            result = self.db.execute_query(
                "SELECT COUNT(*) as count FROM users WHERE user_type = 'professor' AND is_active = 1",
                fetch_all=False
            )
            return result['count'] if result else 0
        
        except Exception as e:
            self.logger.error(f"Failed to get professor count: {str(e)}")
            return 0
    
    def deactivate_user(self, user_id: int, deactivated_by: int = None) -> bool:
        """
        Deactivate user account.
        
        Args:
            user_id (int): User ID to deactivate
            deactivated_by (int): ID of user performing deactivation
        
        Returns:
            bool: Success status
        """
        try:
            affected_rows = self.db.execute_update(
                "UPDATE users SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,)
            )
            
            if affected_rows > 0:
                # Remove from active sessions
                if user_id in self.active_sessions:
                    del self.active_sessions[user_id]
                
                self.logger.info(f"User {user_id} deactivated by {deactivated_by}")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Failed to deactivate user {user_id}: {str(e)}")
            return False
    
    def _validate_user_data(self, username: str, password: str, email: str) -> Dict[str, Any]:
        """
        Validate user registration data.
        
        Args:
            username (str): Username
            password (str): Password
            email (str): Email address
        
        Returns:
            Dict[str, Any]: Validation result
        """
        # Validate username
        if not username or len(username) < 3:
            return {'valid': False, 'error': 'Username must be at least 3 characters long'}
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return {'valid': False, 'error': 'Username can only contain letters, numbers, hyphens, and underscores'}
        
        # Validate password
        password_validation = self._validate_password(password)
        if not password_validation['valid']:
            return password_validation
        
        # Validate email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return {'valid': False, 'error': 'Invalid email address format'}
        
        return {'valid': True}
    
    def _validate_password(self, password: str) -> Dict[str, Any]:
        """
        Validate password against security requirements.
        
        Args:
            password (str): Password to validate
        
        Returns:
            Dict[str, Any]: Validation result
        """
        if not password:
            return {'valid': False, 'error': 'Password is required'}
        
        if len(password) < self.security_config['password_min_length']:
            return {'valid': False, 'error': f'Password must be at least {self.security_config["password_min_length"]} characters long'}
        
        if self.security_config['password_require_uppercase'] and not re.search(r'[A-Z]', password):
            return {'valid': False, 'error': 'Password must contain at least one uppercase letter'}
        
        if self.security_config['password_require_lowercase'] and not re.search(r'[a-z]', password):
            return {'valid': False, 'error': 'Password must contain at least one lowercase letter'}
        
        if self.security_config['password_require_numbers'] and not re.search(r'\d', password):
            return {'valid': False, 'error': 'Password must contain at least one number'}
        
        if self.security_config['password_require_special'] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return {'valid': False, 'error': 'Password must contain at least one special character'}
        
        return {'valid': True}
    
    def _is_account_locked(self, username: str) -> bool:
        """
        Check if account is locked due to failed login attempts.
        
        Args:
            username (str): Username to check
        
        Returns:
            bool: True if account is locked
        """
        if username not in self.failed_attempts:
            return False
        
        attempt_data = self.failed_attempts[username]
        
        # Check if lockout period has expired
        if datetime.now() - attempt_data['last_attempt'] > timedelta(minutes=self.security_config['lockout_duration_minutes']):
            # Clear expired lockout
            del self.failed_attempts[username]
            return False
        
        # Check if max attempts exceeded
        return attempt_data['count'] >= self.security_config['max_login_attempts']
    
    def _record_failed_attempt(self, username: str, ip_address: str = None) -> None:
        """
        Record failed login attempt.
        
        Args:
            username (str): Username
            ip_address (str): Client IP address
        """
        if username not in self.failed_attempts:
            self.failed_attempts[username] = {'count': 0, 'last_attempt': datetime.now()}
        
        self.failed_attempts[username]['count'] += 1
        self.failed_attempts[username]['last_attempt'] = datetime.now()
        
        # Log failed attempt
        self.logger.warning(f"Failed login attempt {self.failed_attempts[username]['count']} for {username} from {ip_address}")
    
    def _clear_failed_attempts(self, username: str) -> None:
        """
        Clear failed login attempts for user.
        
        Args:
            username (str): Username
        """
        if username in self.failed_attempts:
            del self.failed_attempts[username]
    
    def _create_user_session(self, user: Dict[str, Any], ip_address: str = None, 
                            user_agent: str = None) -> UserSession:
        """
        Create user session.
        
        Args:
            user (Dict[str, Any]): User information
            ip_address (str): Client IP address
            user_agent (str): Client user agent
        
        Returns:
            UserSession: Created session
        """
        session = UserSession(
            user_id=user['id'],
            username=user['username'],
            user_type=user['user_type'],
            full_name=user['full_name'],
            login_time=datetime.now(),
            last_activity=datetime.now(),
            ip_address=ip_address or 'unknown',
            user_agent=user_agent or 'unknown',
            is_active=True
        )
        
        self.active_sessions[user['id']] = session
        return session
    
    def _log_login_event(self, user_id: int, success: bool, ip_address: str = None, 
                        user_agent: str = None) -> None:
        """
        Log login event for security audit.
        
        Args:
            user_id (int): User ID
            success (bool): Login success status
            ip_address (str): Client IP address
            user_agent (str): Client user agent
        """
        try:
            # In production, this would log to a security audit table
            log_message = f"Login {'successful' if success else 'failed'} for user {user_id}"
            if ip_address:
                log_message += f" from {ip_address}"
            
            if success:
                self.logger.info(log_message)
            else:
                self.logger.warning(log_message)
        
        except Exception as e:
            self.logger.error(f"Failed to log login event: {str(e)}")
    
    def _is_password_in_history(self, user_id: int, new_password: str) -> bool:
        """
        Check if password was used recently (password history).
        
        Args:
            user_id (int): User ID
            new_password (str): New password to check
        
        Returns:
            bool: True if password is in recent history
        """
        # This would check against a password history table in production
        # For now, we'll just return False (no history check)
        return False
    
    def _store_password_history(self, user_id: int, old_password_hash: str) -> None:
        """
        Store old password hash in history.
        
        Args:
            user_id (int): User ID
            old_password_hash (str): Old password hash
        """
        # In production, this would store in a password_history table
        pass
    
    def update_session_activity(self, user_id: int) -> None:
        """
        Update session last activity time.
        
        Args:
            user_id (int): User ID
        """
        if user_id in self.active_sessions:
            self.active_sessions[user_id].last_activity = datetime.now()
    
    def is_session_valid(self, user_id: int) -> bool:
        """
        Check if user session is valid and not expired.
        
        Args:
            user_id (int): User ID
        
        Returns:
            bool: True if session is valid
        """
        if user_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[user_id]
        
        # Check session timeout
        timeout_delta = timedelta(minutes=self.security_config['session_timeout_minutes'])
        if datetime.now() - session.last_activity > timeout_delta:
            # Remove expired session
            del self.active_sessions[user_id]
            return False
        
        return session.is_active
    
    def terminate_session(self, user_id: int) -> bool:
        """
        Terminate user session.
        
        Args:
            user_id (int): User ID
        
        Returns:
            bool: Success status
        """
        try:
            if user_id in self.active_sessions:
                del self.active_sessions[user_id]
                self.logger.info(f"Session terminated for user {user_id}")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Failed to terminate session for user {user_id}: {str(e)}")
            return False
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get list of active sessions.
        
        Returns:
            List[Dict[str, Any]]: Active sessions
        """
        try:
            active_sessions = []
            current_time = datetime.now()
            
            for user_id, session in list(self.active_sessions.items()):
                # Check if session is still valid
                timeout_delta = timedelta(minutes=self.security_config['session_timeout_minutes'])
                if current_time - session.last_activity > timeout_delta:
                    # Remove expired session
                    del self.active_sessions[user_id]
                    continue
                
                active_sessions.append({
                    'user_id': session.user_id,
                    'username': session.username,
                    'full_name': session.full_name,
                    'user_type': session.user_type,
                    'login_time': session.login_time.isoformat(),
                    'last_activity': session.last_activity.isoformat(),
                    'ip_address': session.ip_address,
                    'session_duration': str(current_time - session.login_time)
                })
            
            return active_sessions
        
        except Exception as e:
            self.logger.error(f"Failed to get active sessions: {str(e)}")
            return []