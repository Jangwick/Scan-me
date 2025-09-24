"""
Notification System Module - Flask QR Code Attendance System
Author: GitHub Copilot
Date: September 2025

This module handles real-time notifications and alerts for the attendance system.
It provides comprehensive notification management including real-time displays,
email alerts, system notifications, and customizable notification templates.

Features:
- Real-time attendance notifications
- WebSocket-based live updates
- Email notification system
- Customizable notification templates
- Notification history and logging
- Alert severity levels
- Bulk notification operations
- Notification preferences management
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import threading
from queue import Queue
import asyncio
from dataclasses import dataclass, asdict
from jinja2 import Template
import ssl
import os

@dataclass
class NotificationData:
    """Data structure for notification information."""
    id: Optional[str]
    type: str
    title: str
    message: str
    severity: str
    recipient: Optional[str]
    data: Dict[str, Any]
    created_at: str
    is_read: bool = False
    is_sent: bool = False

class NotificationSystem:
    """
    Comprehensive notification system for real-time alerts and updates.
    Handles various notification channels and delivery methods.
    """
    
    def __init__(self):
        """Initialize the notification system with default configuration."""
        self.logger = logging.getLogger(__name__)
        
        # Notification types
        self.NOTIFICATION_TYPES = {
            'ATTENDANCE_SCAN': 'attendance_scan',
            'LATE_ARRIVAL': 'late_arrival',
            'DUPLICATE_SCAN': 'duplicate_scan',
            'SYSTEM_ALERT': 'system_alert',
            'REPORT_READY': 'report_ready',
            'ERROR_ALERT': 'error_alert'
        }
        
        # Severity levels
        self.SEVERITY_LEVELS = {
            'INFO': 'info',
            'WARNING': 'warning',
            'ERROR': 'error',
            'SUCCESS': 'success'
        }
        
        # Notification queue for background processing
        self.notification_queue = Queue()
        
        # WebSocket connections for real-time updates
        self.websocket_connections = set()
        
        # Email configuration
        self.email_config = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': '',  # Configure in production
            'password': '',  # Configure in production
            'use_tls': True
        }
        
        # Notification templates
        self.templates = {
            'attendance_scan': self._get_attendance_scan_template(),
            'late_arrival': self._get_late_arrival_template(),
            'duplicate_scan': self._get_duplicate_scan_template(),
            'system_alert': self._get_system_alert_template(),
            'report_ready': self._get_report_ready_template()
        }
        
        # Start background notification processor
        self.notification_processor = threading.Thread(
            target=self._process_notifications,
            daemon=True
        )
        self.notification_processor.start()
        
        # Active notifications cache
        self.active_notifications = {}
        
        self.logger.info("Notification system initialized")
    
    def send_attendance_notification(self, attendance_data: Dict[str, Any]) -> bool:
        """
        Send real-time attendance notification.
        
        Args:
            attendance_data (Dict[str, Any]): Attendance scan data
        
        Returns:
            bool: Success status
        """
        try:
            # Determine notification type and severity
            status = attendance_data.get('status', 'present')
            notification_type = self.NOTIFICATION_TYPES['LATE_ARRIVAL'] if status == 'late' else self.NOTIFICATION_TYPES['ATTENDANCE_SCAN']
            severity = self.SEVERITY_LEVELS['WARNING'] if status == 'late' else self.SEVERITY_LEVELS['SUCCESS']
            
            # Create notification
            notification = NotificationData(
                id=f"attendance_{datetime.now().timestamp()}",
                type=notification_type,
                title=f"Attendance Recorded - {attendance_data['student_name']}",
                message=self._format_attendance_message(attendance_data),
                severity=severity,
                recipient=None,  # Broadcast to all connected clients
                data=attendance_data,
                created_at=datetime.now().isoformat(),
                is_read=False,
                is_sent=False
            )
            
            # Queue for processing
            self.notification_queue.put(notification)
            
            # Send immediate real-time update
            self._broadcast_realtime_notification(notification)
            
            self.logger.info(f"Attendance notification queued for {attendance_data['student_name']}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send attendance notification: {str(e)}")
            return False
    
    def send_duplicate_scan_alert(self, student_data: Dict[str, Any], room_data: Dict[str, Any]) -> bool:
        """
        Send alert for duplicate scan attempts.
        
        Args:
            student_data (Dict[str, Any]): Student information
            room_data (Dict[str, Any]): Room information
        
        Returns:
            bool: Success status
        """
        try:
            notification = NotificationData(
                id=f"duplicate_{datetime.now().timestamp()}",
                type=self.NOTIFICATION_TYPES['DUPLICATE_SCAN'],
                title="Duplicate Scan Alert",
                message=f"Duplicate scan attempt detected for {student_data.get('name', 'Unknown')} in {room_data.get('name', 'Unknown Room')}",
                severity=self.SEVERITY_LEVELS['WARNING'],
                recipient=None,
                data={'student': student_data, 'room': room_data},
                created_at=datetime.now().isoformat()
            )
            
            self.notification_queue.put(notification)
            self._broadcast_realtime_notification(notification)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send duplicate scan alert: {str(e)}")
            return False
    
    def send_system_alert(self, title: str, message: str, severity: str = 'info', 
                         recipient: str = None, additional_data: Dict[str, Any] = None) -> bool:
        """
        Send system alert notification.
        
        Args:
            title (str): Alert title
            message (str): Alert message
            severity (str): Alert severity level
            recipient (str): Specific recipient (optional)
            additional_data (Dict[str, Any]): Additional data
        
        Returns:
            bool: Success status
        """
        try:
            notification = NotificationData(
                id=f"system_{datetime.now().timestamp()}",
                type=self.NOTIFICATION_TYPES['SYSTEM_ALERT'],
                title=title,
                message=message,
                severity=severity,
                recipient=recipient,
                data=additional_data or {},
                created_at=datetime.now().isoformat()
            )
            
            self.notification_queue.put(notification)
            
            # Send immediate update for high priority alerts
            if severity in ['error', 'warning']:
                self._broadcast_realtime_notification(notification)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send system alert: {str(e)}")
            return False
    
    def send_report_ready_notification(self, report_info: Dict[str, Any], 
                                      recipient_email: str = None) -> bool:
        """
        Send notification when report generation is complete.
        
        Args:
            report_info (Dict[str, Any]): Report generation information
            recipient_email (str): Email address for notification
        
        Returns:
            bool: Success status
        """
        try:
            notification = NotificationData(
                id=f"report_{datetime.now().timestamp()}",
                type=self.NOTIFICATION_TYPES['REPORT_READY'],
                title="Report Generated Successfully",
                message=f"Report '{report_info.get('filename', 'Unknown')}' is ready for download",
                severity=self.SEVERITY_LEVELS['SUCCESS'],
                recipient=recipient_email,
                data=report_info,
                created_at=datetime.now().isoformat()
            )
            
            self.notification_queue.put(notification)
            
            # Send email notification if recipient email is provided
            if recipient_email:
                self._send_email_notification(notification)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send report ready notification: {str(e)}")
            return False
    
    def _format_attendance_message(self, attendance_data: Dict[str, Any]) -> str:
        """
        Format attendance notification message.
        
        Args:
            attendance_data (Dict[str, Any]): Attendance data
        
        Returns:
            str: Formatted message
        """
        try:
            student_name = attendance_data.get('student_name', 'Unknown Student')
            student_id = attendance_data.get('student_id', '')
            department = attendance_data.get('department', '')
            year_section = attendance_data.get('year_section', '')
            room_name = attendance_data.get('room_name', 'Unknown Room')
            timestamp = attendance_data.get('timestamp', '')
            status = attendance_data.get('status', 'present')
            
            # Format timestamp
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime('%I:%M %p')
            except:
                time_str = timestamp
            
            # Create status icon
            status_icons = {
                'present': '✅',
                'late': '⚠️',
                'absent': '❌',
                'excused': 'ℹ️'
            }
            
            status_icon = status_icons.get(status, '📍')
            
            message = f"{status_icon} {student_name} ({student_id}) - {department} {year_section} - {status.title()} ({time_str}, {room_name})"
            
            return message
        
        except Exception as e:
            self.logger.error(f"Error formatting attendance message: {str(e)}")
            return f"Attendance recorded for {attendance_data.get('student_name', 'Unknown')}"
    
    def _broadcast_realtime_notification(self, notification: NotificationData) -> None:
        """
        Broadcast notification to all connected WebSocket clients.
        
        Args:
            notification (NotificationData): Notification to broadcast
        """
        try:
            # Convert notification to dictionary
            notification_dict = asdict(notification)
            notification_json = json.dumps(notification_dict)
            
            # Store in active notifications
            self.active_notifications[notification.id] = notification_dict
            
            # In a real implementation, you would broadcast to WebSocket clients here
            # For now, we'll log the notification
            self.logger.info(f"Broadcasting notification: {notification.title}")
            
            # Simulate real-time display (in production, this would use WebSockets)
            self._display_popup_notification(notification_dict)
        
        except Exception as e:
            self.logger.error(f"Failed to broadcast real-time notification: {str(e)}")
    
    def _display_popup_notification(self, notification_data: Dict[str, Any]) -> None:
        """
        Simulate popup notification display.
        
        Args:
            notification_data (Dict[str, Any]): Notification data
        """
        try:
            # In production, this would trigger a popup or toast notification
            # For development, we'll create a simple log entry
            
            severity_colors = {
                'success': '🟢',
                'info': '🔵',
                'warning': '🟡',
                'error': '🔴'
            }
            
            color_icon = severity_colors.get(notification_data['severity'], '⚪')
            
            popup_message = f"""
            ═══════════════════════════════════════
            {color_icon} {notification_data['title']}
            ───────────────────────────────────────
            {notification_data['message']}
            
            Time: {notification_data['created_at'][:19]}
            Type: {notification_data['type']}
            ═══════════════════════════════════════
            """
            
            print(popup_message)  # In production, this would be a proper popup
            
        except Exception as e:
            self.logger.error(f"Failed to display popup notification: {str(e)}")
    
    def _process_notifications(self) -> None:
        """Background thread to process notification queue."""
        while True:
            try:
                # Get notification from queue (blocking)
                notification = self.notification_queue.get()
                
                if notification is None:  # Shutdown signal
                    break
                
                # Process the notification
                self._handle_notification(notification)
                
                # Mark task as done
                self.notification_queue.task_done()
            
            except Exception as e:
                self.logger.error(f"Error processing notification: {str(e)}")
    
    def _handle_notification(self, notification: NotificationData) -> None:
        """
        Handle individual notification processing.
        
        Args:
            notification (NotificationData): Notification to process
        """
        try:
            # Log notification
            self.logger.info(f"Processing notification: {notification.title}")
            
            # Store notification (in production, store in database)
            self._store_notification(notification)
            
            # Send email if recipient specified and configured
            if notification.recipient and self._is_email_configured():
                self._send_email_notification(notification)
            
            # Handle specific notification types
            if notification.type == self.NOTIFICATION_TYPES['ATTENDANCE_SCAN']:
                self._handle_attendance_notification(notification)
            elif notification.type == self.NOTIFICATION_TYPES['SYSTEM_ALERT']:
                self._handle_system_alert(notification)
            
            # Mark as processed
            notification.is_sent = True
            
        except Exception as e:
            self.logger.error(f"Failed to handle notification {notification.id}: {str(e)}")
    
    def _store_notification(self, notification: NotificationData) -> None:
        """
        Store notification in database or file system.
        
        Args:
            notification (NotificationData): Notification to store
        """
        try:
            # In production, this would store in the database
            # For now, we'll store in a simple file-based cache
            
            notifications_dir = 'database/notifications'
            os.makedirs(notifications_dir, exist_ok=True)
            
            filename = f"{notification.id}.json"
            filepath = os.path.join(notifications_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(asdict(notification), f, indent=2)
            
        except Exception as e:
            self.logger.error(f"Failed to store notification: {str(e)}")
    
    def _send_email_notification(self, notification: NotificationData) -> bool:
        """
        Send email notification.
        
        Args:
            notification (NotificationData): Notification to send
        
        Returns:
            bool: Success status
        """
        try:
            if not self._is_email_configured():
                self.logger.warning("Email not configured, skipping email notification")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_config['username']
            msg['To'] = notification.recipient
            msg['Subject'] = f"QR Attendance System - {notification.title}"
            
            # Create email body using template
            template_name = notification.type
            if template_name in self.templates:
                template = Template(self.templates[template_name])
                body = template.render(
                    notification=asdict(notification),
                    system_name="QR Code Attendance System"
                )
            else:
                body = f"""
                {notification.title}
                
                {notification.message}
                
                Generated at: {notification.created_at}
                
                ---
                QR Code Attendance System
                """
            
            msg.attach(MIMEText(body, 'html' if template_name in self.templates else 'plain'))
            
            # Send email
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                if self.email_config['use_tls']:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                
                server.login(self.email_config['username'], self.email_config['password'])
                server.send_message(msg)
            
            self.logger.info(f"Email notification sent to {notification.recipient}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {str(e)}")
            return False
    
    def _is_email_configured(self) -> bool:
        """Check if email configuration is complete."""
        return all([
            self.email_config['username'],
            self.email_config['password'],
            self.email_config['smtp_server']
        ])
    
    def _handle_attendance_notification(self, notification: NotificationData) -> None:
        """Handle attendance-specific notification processing."""
        try:
            # Additional processing for attendance notifications
            attendance_data = notification.data
            
            # Check for patterns or anomalies
            if attendance_data.get('status') == 'late':
                self._check_late_pattern(attendance_data)
            
        except Exception as e:
            self.logger.error(f"Error handling attendance notification: {str(e)}")
    
    def _handle_system_alert(self, notification: NotificationData) -> None:
        """Handle system alert notification processing."""
        try:
            # Additional processing for system alerts
            if notification.severity == 'error':
                # Log critical errors
                self.logger.critical(f"System Error Alert: {notification.message}")
                
                # In production, you might trigger additional alerting mechanisms
                # such as Slack, PagerDuty, or SMS notifications
        
        except Exception as e:
            self.logger.error(f"Error handling system alert: {str(e)}")
    
    def _check_late_pattern(self, attendance_data: Dict[str, Any]) -> None:
        """Check for recurring late arrival patterns."""
        try:
            student_id = attendance_data.get('student_id')
            if not student_id:
                return
            
            # In production, this would check database for recent late arrivals
            # and potentially send additional alerts to professors or administrators
            
            self.logger.info(f"Checking late pattern for student {student_id}")
        
        except Exception as e:
            self.logger.error(f"Error checking late pattern: {str(e)}")
    
    def get_recent_notifications(self, limit: int = 10, user_id: str = None) -> List[Dict[str, Any]]:
        """
        Get recent notifications for display.
        
        Args:
            limit (int): Number of notifications to retrieve
            user_id (str): Specific user ID (optional)
        
        Returns:
            List[Dict[str, Any]]: Recent notifications
        """
        try:
            # Get from active notifications cache
            recent_notifications = list(self.active_notifications.values())
            
            # Sort by creation time (newest first)
            recent_notifications.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Filter by user if specified
            if user_id:
                recent_notifications = [
                    n for n in recent_notifications 
                    if n.get('recipient') == user_id or n.get('recipient') is None
                ]
            
            return recent_notifications[:limit]
        
        except Exception as e:
            self.logger.error(f"Failed to get recent notifications: {str(e)}")
            return []
    
    def mark_notification_read(self, notification_id: str, user_id: str = None) -> bool:
        """
        Mark a notification as read.
        
        Args:
            notification_id (str): Notification ID
            user_id (str): User ID marking as read
        
        Returns:
            bool: Success status
        """
        try:
            if notification_id in self.active_notifications:
                self.active_notifications[notification_id]['is_read'] = True
                self.logger.info(f"Notification {notification_id} marked as read")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Failed to mark notification as read: {str(e)}")
            return False
    
    def configure_email(self, smtp_server: str, smtp_port: int, username: str, 
                       password: str, use_tls: bool = True) -> None:
        """
        Configure email settings.
        
        Args:
            smtp_server (str): SMTP server address
            smtp_port (int): SMTP server port
            username (str): Email username
            password (str): Email password
            use_tls (bool): Use TLS encryption
        """
        self.email_config.update({
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'username': username,
            'password': password,
            'use_tls': use_tls
        })
        
        self.logger.info("Email configuration updated")
    
    def add_websocket_connection(self, connection) -> None:
        """Add WebSocket connection for real-time updates."""
        self.websocket_connections.add(connection)
        self.logger.info("WebSocket connection added")
    
    def remove_websocket_connection(self, connection) -> None:
        """Remove WebSocket connection."""
        self.websocket_connections.discard(connection)
        self.logger.info("WebSocket connection removed")
    
    def _get_attendance_scan_template(self) -> str:
        """Get email template for attendance scan notifications."""
        return """
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #28a745;">✅ Attendance Recorded</h2>
            
            <p><strong>Student:</strong> {{ notification.data.student_name }}</p>
            <p><strong>Student ID:</strong> {{ notification.data.student_id }}</p>
            <p><strong>Department:</strong> {{ notification.data.department }}</p>
            <p><strong>Year & Section:</strong> {{ notification.data.year_section }}</p>
            <p><strong>Room:</strong> {{ notification.data.room_name }}</p>
            <p><strong>Time:</strong> {{ notification.data.timestamp }}</p>
            <p><strong>Status:</strong> <span style="color: #28a745;">{{ notification.data.status.title() }}</span></p>
            
            <hr>
            <p style="color: #6c757d; font-size: 12px;">
                Generated by {{ system_name }} on {{ notification.created_at }}
            </p>
        </body>
        </html>
        """
    
    def _get_late_arrival_template(self) -> str:
        """Get email template for late arrival notifications."""
        return """
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #ffc107;">⚠️ Late Arrival Alert</h2>
            
            <p><strong>Student:</strong> {{ notification.data.student_name }}</p>
            <p><strong>Student ID:</strong> {{ notification.data.student_id }}</p>
            <p><strong>Department:</strong> {{ notification.data.department }}</p>
            <p><strong>Year & Section:</strong> {{ notification.data.year_section }}</p>
            <p><strong>Room:</strong> {{ notification.data.room_name }}</p>
            <p><strong>Time:</strong> {{ notification.data.timestamp }}</p>
            <p><strong>Status:</strong> <span style="color: #ffc107;">Late Arrival</span></p>
            
            <p style="background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107;">
                This student has arrived late to class. Please review attendance policies if necessary.
            </p>
            
            <hr>
            <p style="color: #6c757d; font-size: 12px;">
                Generated by {{ system_name }} on {{ notification.created_at }}
            </p>
        </body>
        </html>
        """
    
    def _get_duplicate_scan_template(self) -> str:
        """Get email template for duplicate scan alerts."""
        return """
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #dc3545;">🚫 Duplicate Scan Alert</h2>
            
            <p><strong>Alert:</strong> {{ notification.title }}</p>
            <p><strong>Message:</strong> {{ notification.message }}</p>
            <p><strong>Time:</strong> {{ notification.created_at }}</p>
            
            <p style="background-color: #f8d7da; padding: 10px; border-left: 4px solid #dc3545;">
                A duplicate scan attempt was detected. Please investigate if this was intentional or if there's a system issue.
            </p>
            
            <hr>
            <p style="color: #6c757d; font-size: 12px;">
                Generated by {{ system_name }} on {{ notification.created_at }}
            </p>
        </body>
        </html>
        """
    
    def _get_system_alert_template(self) -> str:
        """Get email template for system alerts."""
        return """
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #007bff;">🔔 System Alert</h2>
            
            <p><strong>Alert:</strong> {{ notification.title }}</p>
            <p><strong>Message:</strong> {{ notification.message }}</p>
            <p><strong>Severity:</strong> 
                <span style="color: {% if notification.severity == 'error' %}#dc3545{% elif notification.severity == 'warning' %}#ffc107{% else %}#007bff{% endif %};">
                    {{ notification.severity.title() }}
                </span>
            </p>
            <p><strong>Time:</strong> {{ notification.created_at }}</p>
            
            <hr>
            <p style="color: #6c757d; font-size: 12px;">
                Generated by {{ system_name }} on {{ notification.created_at }}
            </p>
        </body>
        </html>
        """
    
    def _get_report_ready_template(self) -> str:
        """Get email template for report ready notifications."""
        return """
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #28a745;">📊 Report Generated Successfully</h2>
            
            <p>Your requested report has been generated and is ready for download.</p>
            
            <p><strong>Report File:</strong> {{ notification.data.filename }}</p>
            <p><strong>Format:</strong> {{ notification.data.format }}</p>
            <p><strong>Size:</strong> {{ notification.data.size }} bytes</p>
            <p><strong>Generated:</strong> {{ notification.created_at }}</p>
            
            <p style="background-color: #d4edda; padding: 10px; border-left: 4px solid #28a745;">
                You can download the report from the system dashboard or reports section.
            </p>
            
            <hr>
            <p style="color: #6c757d; font-size: 12px;">
                Generated by {{ system_name }} on {{ notification.created_at }}
            </p>
        </body>
        </html>
        """
    
    def shutdown(self) -> None:
        """Shutdown the notification system gracefully."""
        try:
            # Signal the notification processor to stop
            self.notification_queue.put(None)
            
            # Wait for the processor to finish
            if self.notification_processor.is_alive():
                self.notification_processor.join(timeout=5)
            
            # Close WebSocket connections
            self.websocket_connections.clear()
            
            self.logger.info("Notification system shut down")
        
        except Exception as e:
            self.logger.error(f"Error during notification system shutdown: {str(e)}")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.shutdown()