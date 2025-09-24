"""
Room Manager Module - Flask QR Code Attendance System
Author: GitHub Copilot
Date: September 2025

This module handles room management operations for the attendance system.
It provides comprehensive room administration including room creation, updates,
scheduling, occupancy tracking, and utilization analytics.

Features:
- Room creation and management
- Room scheduling and assignments
- Occupancy tracking and analytics
- Room utilization reports
- Building and floor management
- Capacity management
- Room availability checking
- Assignment management for professors
"""

from datetime import datetime, timedelta, time
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass

@dataclass
class RoomAssignment:
    """Data structure for room assignment information."""
    id: Optional[int]
    professor_id: int
    room_id: int
    subject_id: Optional[int]
    day_of_week: int
    start_time: str
    end_time: str
    is_active: bool

@dataclass
class RoomOccupancy:
    """Data structure for room occupancy information."""
    room_id: int
    room_name: str
    current_occupancy: int
    capacity: int
    utilization_percentage: float
    last_updated: datetime

class RoomManager:
    """
    Comprehensive room management system for the QR code attendance system.
    Handles all aspects of room administration, scheduling, and analytics.
    """
    
    def __init__(self, database_manager):
        """
        Initialize the room manager with database connection.
        
        Args:
            database_manager: Database manager instance
        """
        self.db = database_manager
        self.logger = logging.getLogger(__name__)
        
        # Room types
        self.ROOM_TYPES = {
            'CLASSROOM': 'classroom',
            'LABORATORY': 'laboratory',
            'LECTURE_HALL': 'lecture_hall',
            'CONFERENCE': 'conference',
            'STUDY_AREA': 'study_area',
            'LIBRARY': 'library',
            'OFFICE': 'office',
            'OTHER': 'other'
        }
        
        # Days of week (0 = Monday, 6 = Sunday)
        self.DAYS_OF_WEEK = {
            0: 'Monday',
            1: 'Tuesday',
            2: 'Wednesday',
            3: 'Thursday',
            4: 'Friday',
            5: 'Saturday',
            6: 'Sunday'
        }
        
        self.logger.info("Room manager initialized")
    
    def create_room(self, room_code: str, room_name: str, building: str = None,
                   floor: int = None, capacity: int = 0, room_type: str = 'classroom',
                   created_by: int = None) -> Dict[str, Any]:
        """
        Create a new room in the system.
        
        Args:
            room_code (str): Unique room code
            room_name (str): Room name
            building (str): Building name
            floor (int): Floor number
            capacity (int): Room capacity
            room_type (str): Type of room
            created_by (int): ID of user creating the room
        
        Returns:
            Dict[str, Any]: Creation result
        """
        try:
            # Validate input
            if not room_code or not room_name:
                return {
                    'success': False,
                    'error': 'Room code and name are required'
                }
            
            # Check if room code already exists
            existing_room = self.db.execute_query(
                "SELECT id FROM rooms WHERE room_code = ?",
                (room_code,),
                fetch_all=False
            )
            
            if existing_room:
                return {
                    'success': False,
                    'error': 'Room code already exists'
                }
            
            # Validate room type
            if room_type not in self.ROOM_TYPES.values():
                room_type = self.ROOM_TYPES['CLASSROOM']
            
            # Insert new room
            room_id = self.db.execute_update(
                """INSERT INTO rooms (room_code, room_name, building, floor, 
                                    capacity, room_type, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                (room_code, room_name, building, floor, capacity, room_type)
            )
            
            self.logger.info(f"Room created successfully: {room_code} (ID: {room_id})")
            
            return {
                'success': True,
                'room_id': room_id,
                'room_code': room_code,
                'message': 'Room created successfully'
            }
        
        except Exception as e:
            self.logger.error(f"Room creation failed for {room_code}: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to create room'
            }
    
    def update_room(self, room_id: int, room_data: Dict[str, Any],
                   updated_by: int = None) -> Dict[str, Any]:
        """
        Update room information.
        
        Args:
            room_id (int): Room ID
            room_data (Dict[str, Any]): Updated room data
            updated_by (int): ID of user making the update
        
        Returns:
            Dict[str, Any]: Update result
        """
        try:
            # Check if room exists
            existing_room = self.db.execute_query(
                "SELECT * FROM rooms WHERE id = ?",
                (room_id,),
                fetch_all=False
            )
            
            if not existing_room:
                return {
                    'success': False,
                    'error': 'Room not found'
                }
            
            # Build update query
            update_fields = []
            params = []
            
            # Map of allowed fields to update
            allowed_fields = {
                'room_name': 'room_name',
                'building': 'building',
                'floor': 'floor',
                'capacity': 'capacity',
                'room_type': 'room_type',
                'is_active': 'is_active'
            }
            
            for field, db_field in allowed_fields.items():
                if field in room_data:
                    update_fields.append(f"{db_field} = ?")
                    params.append(room_data[field])
            
            if not update_fields:
                return {
                    'success': False,
                    'error': 'No valid fields to update'
                }
            
            # Add updated timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(room_id)
            
            # Execute update
            query = f"UPDATE rooms SET {', '.join(update_fields)} WHERE id = ?"
            affected_rows = self.db.execute_update(query, params)
            
            if affected_rows > 0:
                self.logger.info(f"Room {room_id} updated successfully")
                return {
                    'success': True,
                    'message': 'Room updated successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'No changes made to room'
                }
        
        except Exception as e:
            self.logger.error(f"Room update failed for ID {room_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to update room'
            }
    
    def delete_room(self, room_id: int, deleted_by: int = None) -> bool:
        """
        Soft delete a room (mark as inactive).
        
        Args:
            room_id (int): Room ID
            deleted_by (int): ID of user deleting the room
        
        Returns:
            bool: Success status
        """
        try:
            # Check if room has attendance records
            has_attendance = self.db.execute_query(
                "SELECT COUNT(*) as count FROM attendance WHERE room_id = ?",
                (room_id,),
                fetch_all=False
            )['count'] > 0
            
            if has_attendance:
                # Soft delete - mark as inactive
                affected_rows = self.db.execute_update(
                    "UPDATE rooms SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (room_id,)
                )
            else:
                # Hard delete if no attendance records
                affected_rows = self.db.execute_update(
                    "DELETE FROM rooms WHERE id = ?",
                    (room_id,)
                )
            
            if affected_rows > 0:
                self.logger.info(f"Room {room_id} deleted by user {deleted_by}")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Failed to delete room {room_id}: {str(e)}")
            return False
    
    def get_all_rooms(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Get all rooms in the system.
        
        Args:
            include_inactive (bool): Include inactive rooms
        
        Returns:
            List[Dict[str, Any]]: List of rooms
        """
        try:
            where_clause = "" if include_inactive else "WHERE is_active = 1"
            
            return self.db.execute_query(f"""
                SELECT r.*, 
                       COUNT(a.id) as total_attendance,
                       COUNT(DISTINCT a.student_id) as unique_students
                FROM rooms r
                LEFT JOIN attendance a ON r.id = a.room_id
                {where_clause}
                GROUP BY r.id, r.room_code, r.room_name, r.building, r.floor, 
                         r.capacity, r.room_type, r.is_active, r.created_at, r.updated_at
                ORDER BY r.building, r.floor, r.room_name
            """)
        
        except Exception as e:
            self.logger.error(f"Failed to get rooms: {str(e)}")
            return []
    
    def get_room_by_id(self, room_id: int) -> Optional[Dict[str, Any]]:
        """
        Get room by ID.
        
        Args:
            room_id (int): Room ID
        
        Returns:
            Dict[str, Any]: Room information or None
        """
        try:
            return self.db.execute_query(
                """SELECT r.*, 
                          COUNT(a.id) as total_attendance,
                          COUNT(DISTINCT a.student_id) as unique_students,
                          MAX(a.created_at) as last_attendance
                   FROM rooms r
                   LEFT JOIN attendance a ON r.id = a.room_id
                   WHERE r.id = ?
                   GROUP BY r.id""",
                (room_id,),
                fetch_all=False
            )
        
        except Exception as e:
            self.logger.error(f"Failed to get room {room_id}: {str(e)}")
            return None
    
    def get_room_by_code(self, room_code: str) -> Optional[Dict[str, Any]]:
        """
        Get room by room code.
        
        Args:
            room_code (str): Room code
        
        Returns:
            Dict[str, Any]: Room information or None
        """
        try:
            return self.db.execute_query(
                "SELECT * FROM rooms WHERE room_code = ? AND is_active = 1",
                (room_code,),
                fetch_all=False
            )
        
        except Exception as e:
            self.logger.error(f"Failed to get room by code {room_code}: {str(e)}")
            return None
    
    def get_room_count(self) -> int:
        """
        Get total count of active rooms.
        
        Returns:
            int: Number of active rooms
        """
        try:
            result = self.db.execute_query(
                "SELECT COUNT(*) as count FROM rooms WHERE is_active = 1",
                fetch_all=False
            )
            return result['count'] if result else 0
        
        except Exception as e:
            self.logger.error(f"Failed to get room count: {str(e)}")
            return 0
    
    def get_rooms_by_building(self, building: str) -> List[Dict[str, Any]]:
        """
        Get rooms in a specific building.
        
        Args:
            building (str): Building name
        
        Returns:
            List[Dict[str, Any]]: Rooms in the building
        """
        try:
            return self.db.execute_query(
                """SELECT * FROM rooms 
                   WHERE building = ? AND is_active = 1 
                   ORDER BY floor, room_name""",
                (building,)
            )
        
        except Exception as e:
            self.logger.error(f"Failed to get rooms for building {building}: {str(e)}")
            return []
    
    def get_rooms_by_professor(self, professor_id: int) -> List[Dict[str, Any]]:
        """
        Get rooms assigned to a specific professor.
        
        Args:
            professor_id (int): Professor ID
        
        Returns:
            List[Dict[str, Any]]: Assigned rooms
        """
        try:
            return self.db.execute_query(
                """SELECT DISTINCT r.*, ra.day_of_week, ra.start_time, ra.end_time,
                          s.subject_name, s.subject_code
                   FROM rooms r
                   JOIN room_assignments ra ON r.id = ra.room_id
                   LEFT JOIN subjects s ON ra.subject_id = s.id
                   WHERE ra.professor_id = ? AND ra.is_active = 1 AND r.is_active = 1
                   ORDER BY ra.day_of_week, ra.start_time""",
                (professor_id,)
            )
        
        except Exception as e:
            self.logger.error(f"Failed to get rooms for professor {professor_id}: {str(e)}")
            return []
    
    def assign_room_to_professor(self, professor_id: int, room_id: int, 
                                subject_id: int = None, day_of_week: int = 0,
                                start_time: str = "08:00", end_time: str = "09:00",
                                assigned_by: int = None) -> Dict[str, Any]:
        """
        Assign a room to a professor for a specific schedule.
        
        Args:
            professor_id (int): Professor ID
            room_id (int): Room ID
            subject_id (int): Subject ID (optional)
            day_of_week (int): Day of week (0=Monday, 6=Sunday)
            start_time (str): Start time (HH:MM format)
            end_time (str): End time (HH:MM format)
            assigned_by (int): ID of user making the assignment
        
        Returns:
            Dict[str, Any]: Assignment result
        """
        try:
            # Validate professor exists
            professor = self.db.execute_query(
                "SELECT id FROM users WHERE id = ? AND user_type = 'professor' AND is_active = 1",
                (professor_id,),
                fetch_all=False
            )
            
            if not professor:
                return {
                    'success': False,
                    'error': 'Professor not found or inactive'
                }
            
            # Validate room exists
            room = self.db.execute_query(
                "SELECT id FROM rooms WHERE id = ? AND is_active = 1",
                (room_id,),
                fetch_all=False
            )
            
            if not room:
                return {
                    'success': False,
                    'error': 'Room not found or inactive'
                }
            
            # Check for scheduling conflicts
            conflict = self.db.execute_query(
                """SELECT id FROM room_assignments 
                   WHERE room_id = ? AND day_of_week = ? 
                   AND is_active = 1
                   AND ((start_time <= ? AND end_time > ?) 
                        OR (start_time < ? AND end_time >= ?))""",
                (room_id, day_of_week, start_time, start_time, end_time, end_time),
                fetch_all=False
            )
            
            if conflict:
                return {
                    'success': False,
                    'error': 'Room is already assigned for the specified time slot'
                }
            
            # Create assignment
            assignment_id = self.db.execute_update(
                """INSERT INTO room_assignments 
                   (professor_id, room_id, subject_id, day_of_week, start_time, end_time)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (professor_id, room_id, subject_id, day_of_week, start_time, end_time)
            )
            
            self.logger.info(f"Room {room_id} assigned to professor {professor_id}")
            
            return {
                'success': True,
                'assignment_id': assignment_id,
                'message': 'Room assigned successfully'
            }
        
        except Exception as e:
            self.logger.error(f"Room assignment failed: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to assign room'
            }
    
    def remove_room_assignment(self, assignment_id: int, removed_by: int = None) -> bool:
        """
        Remove a room assignment.
        
        Args:
            assignment_id (int): Assignment ID
            removed_by (int): ID of user removing the assignment
        
        Returns:
            bool: Success status
        """
        try:
            affected_rows = self.db.execute_update(
                "UPDATE room_assignments SET is_active = 0 WHERE id = ?",
                (assignment_id,)
            )
            
            if affected_rows > 0:
                self.logger.info(f"Room assignment {assignment_id} removed by user {removed_by}")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Failed to remove room assignment {assignment_id}: {str(e)}")
            return False
    
    def get_room_schedule(self, room_id: int) -> List[Dict[str, Any]]:
        """
        Get schedule for a specific room.
        
        Args:
            room_id (int): Room ID
        
        Returns:
            List[Dict[str, Any]]: Room schedule
        """
        try:
            return self.db.execute_query(
                """SELECT ra.*, 
                          u.full_name as professor_name,
                          s.subject_name, s.subject_code
                   FROM room_assignments ra
                   JOIN users u ON ra.professor_id = u.id
                   LEFT JOIN subjects s ON ra.subject_id = s.id
                   WHERE ra.room_id = ? AND ra.is_active = 1
                   ORDER BY ra.day_of_week, ra.start_time""",
                (room_id,)
            )
        
        except Exception as e:
            self.logger.error(f"Failed to get room schedule for {room_id}: {str(e)}")
            return []
    
    def get_room_occupancy_stats(self) -> List[Dict[str, Any]]:
        """
        Get current room occupancy statistics.
        
        Returns:
            List[Dict[str, Any]]: Room occupancy data
        """
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            return self.db.execute_query(
                """SELECT r.id, r.room_name, r.room_code, r.capacity, r.building,
                          COUNT(DISTINCT a.student_id) as current_occupancy,
                          CASE WHEN r.capacity > 0 
                               THEN ROUND((COUNT(DISTINCT a.student_id) * 100.0) / r.capacity, 2)
                               ELSE 0 
                          END as utilization_percentage,
                          MAX(a.scan_time) as last_scan_time
                   FROM rooms r
                   LEFT JOIN attendance a ON r.id = a.room_id AND a.scan_date = ?
                   WHERE r.is_active = 1
                   GROUP BY r.id, r.room_name, r.room_code, r.capacity, r.building
                   ORDER BY utilization_percentage DESC""",
                (today,)
            )
        
        except Exception as e:
            self.logger.error(f"Failed to get room occupancy stats: {str(e)}")
            return []
    
    def get_room_utilization_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Generate room utilization report for date range.
        
        Args:
            start_date (str): Start date (YYYY-MM-DD)
            end_date (str): End date (YYYY-MM-DD)
        
        Returns:
            Dict[str, Any]: Utilization report
        """
        try:
            # Get room utilization data
            room_stats = self.db.execute_query(
                """SELECT r.id, r.room_name, r.room_code, r.building, r.capacity, r.room_type,
                          COUNT(a.id) as total_scans,
                          COUNT(DISTINCT a.student_id) as unique_students,
                          COUNT(DISTINCT a.scan_date) as active_days,
                          ROUND(AVG(daily_stats.daily_count), 2) as avg_daily_scans,
                          MAX(daily_stats.daily_count) as peak_daily_scans,
                          CASE WHEN r.capacity > 0 
                               THEN ROUND((AVG(daily_stats.daily_count) * 100.0) / r.capacity, 2)
                               ELSE 0 
                          END as avg_utilization_percentage
                   FROM rooms r
                   LEFT JOIN attendance a ON r.id = a.room_id 
                       AND a.scan_date BETWEEN ? AND ?
                   LEFT JOIN (
                       SELECT room_id, scan_date, COUNT(*) as daily_count
                       FROM attendance
                       WHERE scan_date BETWEEN ? AND ?
                       GROUP BY room_id, scan_date
                   ) daily_stats ON r.id = daily_stats.room_id
                   WHERE r.is_active = 1
                   GROUP BY r.id, r.room_name, r.room_code, r.building, r.capacity, r.room_type
                   ORDER BY total_scans DESC""",
                (start_date, end_date, start_date, end_date)
            )
            
            # Get peak hours analysis
            hourly_usage = self.db.execute_query(
                """SELECT CAST(SUBSTR(a.scan_time, 1, 2) AS INTEGER) as hour,
                          COUNT(*) as total_scans,
                          COUNT(DISTINCT a.room_id) as rooms_used,
                          COUNT(DISTINCT a.student_id) as students_scanned
                   FROM attendance a
                   WHERE a.scan_date BETWEEN ? AND ?
                   GROUP BY hour
                   ORDER BY hour""",
                (start_date, end_date)
            )
            
            # Calculate summary statistics
            total_rooms = len([r for r in room_stats if r['total_scans'] > 0])
            total_scans = sum(r['total_scans'] for r in room_stats)
            avg_utilization = sum(r['avg_utilization_percentage'] for r in room_stats) / len(room_stats) if room_stats else 0
            
            return {
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'summary': {
                    'total_active_rooms': total_rooms,
                    'total_scans': total_scans,
                    'average_utilization': round(avg_utilization, 2)
                },
                'room_stats': room_stats,
                'hourly_usage': hourly_usage
            }
        
        except Exception as e:
            self.logger.error(f"Failed to generate room utilization report: {str(e)}")
            return {
                'error': str(e),
                'date_range': {'start_date': start_date, 'end_date': end_date}
            }
    
    def check_room_availability(self, room_id: int, day_of_week: int, 
                               start_time: str, end_time: str) -> Dict[str, Any]:
        """
        Check if a room is available for a specific time slot.
        
        Args:
            room_id (int): Room ID
            day_of_week (int): Day of week (0=Monday, 6=Sunday)
            start_time (str): Start time (HH:MM)
            end_time (str): End time (HH:MM)
        
        Returns:
            Dict[str, Any]: Availability information
        """
        try:
            # Check for existing assignments
            conflicts = self.db.execute_query(
                """SELECT ra.*, u.full_name as professor_name, s.subject_name
                   FROM room_assignments ra
                   JOIN users u ON ra.professor_id = u.id
                   LEFT JOIN subjects s ON ra.subject_id = s.id
                   WHERE ra.room_id = ? AND ra.day_of_week = ? 
                   AND ra.is_active = 1
                   AND ((ra.start_time <= ? AND ra.end_time > ?) 
                        OR (ra.start_time < ? AND ra.end_time >= ?))""",
                (room_id, day_of_week, start_time, start_time, end_time, end_time)
            )
            
            is_available = len(conflicts) == 0
            
            return {
                'available': is_available,
                'conflicts': conflicts,
                'day_name': self.DAYS_OF_WEEK.get(day_of_week, 'Unknown'),
                'time_slot': f"{start_time} - {end_time}"
            }
        
        except Exception as e:
            self.logger.error(f"Failed to check room availability: {str(e)}")
            return {
                'available': False,
                'error': str(e)
            }
    
    def get_buildings(self) -> List[str]:
        """
        Get list of unique buildings.
        
        Returns:
            List[str]: List of building names
        """
        try:
            results = self.db.execute_query(
                """SELECT DISTINCT building FROM rooms 
                   WHERE building IS NOT NULL AND is_active = 1 
                   ORDER BY building"""
            )
            return [r['building'] for r in results]
        
        except Exception as e:
            self.logger.error(f"Failed to get buildings: {str(e)}")
            return []
    
    def get_room_types(self) -> List[Dict[str, str]]:
        """
        Get available room types.
        
        Returns:
            List[Dict[str, str]]: Room types with descriptions
        """
        return [
            {'value': self.ROOM_TYPES['CLASSROOM'], 'label': 'Classroom'},
            {'value': self.ROOM_TYPES['LABORATORY'], 'label': 'Laboratory'},
            {'value': self.ROOM_TYPES['LECTURE_HALL'], 'label': 'Lecture Hall'},
            {'value': self.ROOM_TYPES['CONFERENCE'], 'label': 'Conference Room'},
            {'value': self.ROOM_TYPES['STUDY_AREA'], 'label': 'Study Area'},
            {'value': self.ROOM_TYPES['LIBRARY'], 'label': 'Library'},
            {'value': self.ROOM_TYPES['OFFICE'], 'label': 'Office'},
            {'value': self.ROOM_TYPES['OTHER'], 'label': 'Other'}
        ]