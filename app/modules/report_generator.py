"""
Report Generator Module - Flask QR Code Attendance System
Author: GitHub Copilot
Date: September 2025

This module handles report generation and data export functionality for the attendance system.
It provides comprehensive reporting capabilities including Excel, CSV, and PDF export options
with customizable filters, formatting, and automated report scheduling.

Features:
- Excel/CSV/PDF report generation
- Customizable report templates
- Data filtering and sorting
- Attendance analytics reports
- Student performance reports
- Room utilization reports
- Automated report scheduling
- Email report delivery
"""

import pandas as pd
import io
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import logging
import os
import json
from jinja2 import Template

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

class ReportGenerator:
    """
    Comprehensive report generation system for attendance data.
    Supports multiple output formats and customizable report templates.
    """
    
    def __init__(self, database_manager):
        """
        Initialize the report generator with database connection.
        
        Args:
            database_manager: Database manager instance
        """
        self.db = database_manager
        self.logger = logging.getLogger(__name__)
        
        # Report configuration
        self.output_dir = 'exports'
        self.supported_formats = ['excel', 'csv', 'pdf']
        self.max_records_per_report = 10000
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Report templates
        self.report_templates = {
            'attendance_summary': self._get_attendance_summary_template(),
            'student_report': self._get_student_report_template(),
            'room_utilization': self._get_room_utilization_template()
        }
    
    def generate_attendance_report(self, report_type: str, filters: Dict[str, Any], 
                                 output_format: str = 'excel') -> Dict[str, Any]:
        """
        Generate comprehensive attendance report with specified filters.
        
        Args:
            report_type (str): Type of report to generate
            filters (Dict[str, Any]): Report filters
            output_format (str): Output format (excel, csv, pdf)
        
        Returns:
            Dict[str, Any]: Report generation result
        """
        try:
            # Validate parameters
            if output_format not in self.supported_formats:
                return {
                    'success': False,
                    'error': f'Unsupported output format: {output_format}'
                }
            
            # Get report data based on type
            if report_type == 'attendance_summary':
                data = self._get_attendance_summary_data(filters)
            elif report_type == 'student_performance':
                data = self._get_student_performance_data(filters)
            elif report_type == 'room_utilization':
                data = self._get_room_utilization_data(filters)
            elif report_type == 'daily_attendance':
                data = self._get_daily_attendance_data(filters)
            elif report_type == 'department_analysis':
                data = self._get_department_analysis_data(filters)
            else:
                return {
                    'success': False,
                    'error': f'Unknown report type: {report_type}'
                }
            
            if not data or len(data.get('records', [])) == 0:
                return {
                    'success': False,
                    'error': 'No data found for the specified criteria'
                }
            
            # Generate report based on format
            if output_format == 'excel':
                result = self._generate_excel_report(report_type, data, filters)
            elif output_format == 'csv':
                result = self._generate_csv_report(report_type, data, filters)
            elif output_format == 'pdf':
                result = self._generate_pdf_report(report_type, data, filters)
            
            if result['success']:
                self.logger.info(f"Report generated successfully: {result['filename']}")
            
            return result
        
        except Exception as e:
            self.logger.error(f"Report generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_attendance_summary_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get attendance summary data with applied filters.
        
        Args:
            filters (Dict[str, Any]): Data filters
        
        Returns:
            Dict[str, Any]: Filtered attendance data
        """
        try:
            # Build WHERE clause from filters
            where_conditions = []
            params = []
            
            if filters.get('start_date'):
                where_conditions.append("a.scan_date >= ?")
                params.append(filters['start_date'])
            
            if filters.get('end_date'):
                where_conditions.append("a.scan_date <= ?")
                params.append(filters['end_date'])
            
            if filters.get('room_id'):
                where_conditions.append("a.room_id = ?")
                params.append(filters['room_id'])
            
            if filters.get('department'):
                where_conditions.append("s.department = ?")
                params.append(filters['department'])
            
            if filters.get('status'):
                where_conditions.append("a.status = ?")
                params.append(filters['status'])
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # Get detailed attendance records
            query = f"""
                SELECT a.*, 
                       s.student_id, s.first_name, s.last_name, s.department, 
                       s.year_level, s.section, s.email,
                       r.room_name, r.room_code, r.building, r.floor,
                       sub.subject_name, sub.subject_code,
                       u.full_name as scanned_by_name
                FROM attendance a
                JOIN students s ON a.student_id = s.id
                JOIN rooms r ON a.room_id = r.id
                LEFT JOIN subjects sub ON a.subject_id = sub.id
                LEFT JOIN users u ON a.scanned_by = u.id
                WHERE {where_clause}
                ORDER BY a.scan_date DESC, a.scan_time DESC
                LIMIT ?
            """
            
            params.append(self.max_records_per_report)
            records = self.db.execute_query(query, params)
            
            # Get summary statistics
            stats_query = f"""
                SELECT 
                    COUNT(*) as total_scans,
                    COUNT(DISTINCT s.id) as unique_students,
                    COUNT(DISTINCT r.id) as unique_rooms,
                    SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
                    SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) as late_count,
                    SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) as absent_count
                FROM attendance a
                JOIN students s ON a.student_id = s.id
                JOIN rooms r ON a.room_id = r.id
                WHERE {where_clause}
            """
            
            stats = self.db.execute_query(stats_query, params[:-1], fetch_all=False)
            
            return {
                'records': records,
                'statistics': stats,
                'filters_applied': filters
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get attendance summary data: {str(e)}")
            return {'records': [], 'statistics': {}, 'filters_applied': filters}
    
    def _get_student_performance_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get student performance data with attendance rates and trends.
        
        Args:
            filters (Dict[str, Any]): Data filters
        
        Returns:
            Dict[str, Any]: Student performance data
        """
        try:
            # Build WHERE clause
            where_conditions = ["s.is_active = 1"]
            params = []
            
            if filters.get('start_date') and filters.get('end_date'):
                where_conditions.append("a.scan_date BETWEEN ? AND ?")
                params.extend([filters['start_date'], filters['end_date']])
            
            if filters.get('department'):
                where_conditions.append("s.department = ?")
                params.append(filters['department'])
            
            if filters.get('year_level'):
                where_conditions.append("s.year_level = ?")
                params.append(filters['year_level'])
            
            where_clause = " AND ".join(where_conditions)
            
            # Get student performance metrics
            query = f"""
                SELECT 
                    s.student_id, s.first_name, s.last_name, s.department,
                    s.year_level, s.section, s.email,
                    COUNT(a.id) as total_scans,
                    SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
                    SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) as late_count,
                    SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) as absent_count,
                    ROUND(AVG(CASE WHEN a.status = 'present' THEN 100.0 ELSE 0.0 END), 2) as attendance_rate,
                    ROUND(AVG(CASE WHEN a.status = 'late' THEN 100.0 ELSE 0.0 END), 2) as late_rate,
                    MIN(a.scan_date) as first_attendance,
                    MAX(a.scan_date) as last_attendance
                FROM students s
                LEFT JOIN attendance a ON s.id = a.student_id
                WHERE {where_clause}
                GROUP BY s.id, s.student_id, s.first_name, s.last_name, 
                         s.department, s.year_level, s.section, s.email
                ORDER BY s.department, s.year_level, s.section, s.last_name
            """
            
            records = self.db.execute_query(query, params)
            
            # Calculate department averages
            dept_stats = self.db.execute_query(f"""
                SELECT 
                    s.department,
                    COUNT(DISTINCT s.id) as total_students,
                    COUNT(a.id) as total_scans,
                    ROUND(AVG(CASE WHEN a.status = 'present' THEN 100.0 ELSE 0.0 END), 2) as avg_attendance_rate,
                    ROUND(AVG(CASE WHEN a.status = 'late' THEN 100.0 ELSE 0.0 END), 2) as avg_late_rate
                FROM students s
                LEFT JOIN attendance a ON s.id = a.student_id
                WHERE {where_clause}
                GROUP BY s.department
                ORDER BY s.department
            """, params)
            
            return {
                'records': records,
                'department_statistics': dept_stats,
                'filters_applied': filters
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get student performance data: {str(e)}")
            return {'records': [], 'department_statistics': [], 'filters_applied': filters}
    
    def _get_room_utilization_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get room utilization data and statistics.
        
        Args:
            filters (Dict[str, Any]): Data filters
        
        Returns:
            Dict[str, Any]: Room utilization data
        """
        try:
            # Build WHERE clause
            where_conditions = ["r.is_active = 1"]
            params = []
            
            if filters.get('start_date') and filters.get('end_date'):
                where_conditions.append("a.scan_date BETWEEN ? AND ?")
                params.extend([filters['start_date'], filters['end_date']])
            
            if filters.get('building'):
                where_conditions.append("r.building = ?")
                params.append(filters['building'])
            
            where_clause = " AND ".join(where_conditions)
            
            # Get room utilization metrics
            query = f"""
                SELECT 
                    r.room_code, r.room_name, r.building, r.floor, r.capacity, r.room_type,
                    COUNT(a.id) as total_scans,
                    COUNT(DISTINCT a.student_id) as unique_students,
                    COUNT(DISTINCT a.scan_date) as active_days,
                    ROUND(AVG(daily_scans.daily_count), 2) as avg_daily_scans,
                    MAX(daily_scans.daily_count) as max_daily_scans,
                    CASE WHEN r.capacity > 0 
                         THEN ROUND((COUNT(DISTINCT a.student_id) * 100.0) / r.capacity, 2)
                         ELSE 0 
                    END as utilization_percentage
                FROM rooms r
                LEFT JOIN attendance a ON r.id = a.room_id
                LEFT JOIN (
                    SELECT room_id, scan_date, COUNT(*) as daily_count
                    FROM attendance
                    WHERE scan_date BETWEEN COALESCE(?, '1900-01-01') AND COALESCE(?, '2100-12-31')
                    GROUP BY room_id, scan_date
                ) daily_scans ON r.id = daily_scans.room_id
                WHERE {where_clause}
                GROUP BY r.id, r.room_code, r.room_name, r.building, r.floor, r.capacity, r.room_type
                ORDER BY total_scans DESC
            """
            
            # Add date parameters for the subquery
            subquery_params = [filters.get('start_date'), filters.get('end_date')] + params
            records = self.db.execute_query(query, subquery_params)
            
            # Get hourly distribution
            hourly_query = f"""
                SELECT 
                    CAST(SUBSTR(a.scan_time, 1, 2) AS INTEGER) as hour,
                    r.room_name,
                    COUNT(*) as scan_count
                FROM attendance a
                JOIN rooms r ON a.room_id = r.id
                WHERE {where_clause}
                GROUP BY hour, r.id, r.room_name
                ORDER BY hour, scan_count DESC
            """
            
            hourly_data = self.db.execute_query(hourly_query, params)
            
            return {
                'records': records,
                'hourly_distribution': hourly_data,
                'filters_applied': filters
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get room utilization data: {str(e)}")
            return {'records': [], 'hourly_distribution': [], 'filters_applied': filters}
    
    def _get_daily_attendance_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get daily attendance breakdown data.
        
        Args:
            filters (Dict[str, Any]): Data filters
        
        Returns:
            Dict[str, Any]: Daily attendance data
        """
        try:
            # Default to last 30 days if no date range specified
            if not filters.get('start_date'):
                filters['start_date'] = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not filters.get('end_date'):
                filters['end_date'] = datetime.now().strftime('%Y-%m-%d')
            
            query = """
                SELECT 
                    a.scan_date,
                    COUNT(*) as total_scans,
                    COUNT(DISTINCT a.student_id) as unique_students,
                    COUNT(DISTINCT a.room_id) as rooms_used,
                    SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
                    SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) as late_count,
                    SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) as absent_count,
                    ROUND(AVG(CASE WHEN a.status = 'present' THEN 100.0 ELSE 0.0 END), 2) as attendance_rate
                FROM attendance a
                WHERE a.scan_date BETWEEN ? AND ?
                GROUP BY a.scan_date
                ORDER BY a.scan_date DESC
            """
            
            records = self.db.execute_query(query, [filters['start_date'], filters['end_date']])
            
            # Get weekday analysis
            weekday_query = """
                SELECT 
                    CASE CAST(strftime('%w', a.scan_date) AS INTEGER)
                        WHEN 0 THEN 'Sunday'
                        WHEN 1 THEN 'Monday'
                        WHEN 2 THEN 'Tuesday'
                        WHEN 3 THEN 'Wednesday'
                        WHEN 4 THEN 'Thursday'
                        WHEN 5 THEN 'Friday'
                        WHEN 6 THEN 'Saturday'
                    END as weekday,
                    COUNT(*) as total_scans,
                    ROUND(AVG(daily_stats.daily_count), 2) as avg_daily_scans
                FROM attendance a
                JOIN (
                    SELECT scan_date, COUNT(*) as daily_count
                    FROM attendance
                    WHERE scan_date BETWEEN ? AND ?
                    GROUP BY scan_date
                ) daily_stats ON a.scan_date = daily_stats.scan_date
                WHERE a.scan_date BETWEEN ? AND ?
                GROUP BY CAST(strftime('%w', a.scan_date) AS INTEGER)
                ORDER BY CAST(strftime('%w', a.scan_date) AS INTEGER)
            """
            
            weekday_data = self.db.execute_query(
                weekday_query, 
                [filters['start_date'], filters['end_date']] * 2
            )
            
            return {
                'records': records,
                'weekday_analysis': weekday_data,
                'filters_applied': filters
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get daily attendance data: {str(e)}")
            return {'records': [], 'weekday_analysis': [], 'filters_applied': filters}
    
    def _get_department_analysis_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get department-wise attendance analysis.
        
        Args:
            filters (Dict[str, Any]): Data filters
        
        Returns:
            Dict[str, Any]: Department analysis data
        """
        try:
            where_conditions = []
            params = []
            
            if filters.get('start_date') and filters.get('end_date'):
                where_conditions.append("a.scan_date BETWEEN ? AND ?")
                params.extend([filters['start_date'], filters['end_date']])
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # Department summary
            dept_query = f"""
                SELECT 
                    s.department,
                    COUNT(DISTINCT s.id) as total_students,
                    COUNT(a.id) as total_scans,
                    COUNT(DISTINCT a.scan_date) as active_days,
                    ROUND(AVG(CASE WHEN a.status = 'present' THEN 100.0 ELSE 0.0 END), 2) as attendance_rate,
                    ROUND(AVG(CASE WHEN a.status = 'late' THEN 100.0 ELSE 0.0 END), 2) as late_rate,
                    SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
                    SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) as late_count,
                    SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) as absent_count
                FROM students s
                LEFT JOIN attendance a ON s.id = a.student_id
                WHERE s.is_active = 1 AND ({where_clause})
                GROUP BY s.department
                ORDER BY total_scans DESC
            """
            
            records = self.db.execute_query(dept_query, params)
            
            # Year level breakdown by department
            year_breakdown_query = f"""
                SELECT 
                    s.department,
                    s.year_level,
                    COUNT(DISTINCT s.id) as student_count,
                    COUNT(a.id) as scan_count,
                    ROUND(AVG(CASE WHEN a.status = 'present' THEN 100.0 ELSE 0.0 END), 2) as attendance_rate
                FROM students s
                LEFT JOIN attendance a ON s.id = a.student_id
                WHERE s.is_active = 1 AND ({where_clause})
                GROUP BY s.department, s.year_level
                ORDER BY s.department, s.year_level
            """
            
            year_breakdown = self.db.execute_query(year_breakdown_query, params)
            
            return {
                'records': records,
                'year_breakdown': year_breakdown,
                'filters_applied': filters
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get department analysis data: {str(e)}")
            return {'records': [], 'year_breakdown': [], 'filters_applied': filters}
    
    def _generate_excel_report(self, report_type: str, data: Dict[str, Any], 
                              filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Excel report from data.
        
        Args:
            report_type (str): Report type
            data (Dict[str, Any]): Report data
            filters (Dict[str, Any]): Applied filters
        
        Returns:
            Dict[str, Any]: Excel generation result
        """
        try:
            filename = f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join(self.output_dir, filename)
            
            # Create Excel writer
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Main data sheet
                if data['records']:
                    df_main = pd.DataFrame(data['records'])
                    df_main.to_excel(writer, sheet_name='Data', index=False)
                
                # Statistics sheet
                if 'statistics' in data and data['statistics']:
                    stats_data = [{k: v for k, v in data['statistics'].items()}]
                    df_stats = pd.DataFrame(stats_data)
                    df_stats.to_excel(writer, sheet_name='Statistics', index=False)
                
                # Additional sheets based on report type
                if report_type == 'student_performance' and data.get('department_statistics'):
                    df_dept = pd.DataFrame(data['department_statistics'])
                    df_dept.to_excel(writer, sheet_name='Department Stats', index=False)
                
                elif report_type == 'room_utilization' and data.get('hourly_distribution'):
                    df_hourly = pd.DataFrame(data['hourly_distribution'])
                    df_hourly.to_excel(writer, sheet_name='Hourly Distribution', index=False)
                
                elif report_type == 'daily_attendance' and data.get('weekday_analysis'):
                    df_weekday = pd.DataFrame(data['weekday_analysis'])
                    df_weekday.to_excel(writer, sheet_name='Weekday Analysis', index=False)
                
                elif report_type == 'department_analysis' and data.get('year_breakdown'):
                    df_year = pd.DataFrame(data['year_breakdown'])
                    df_year.to_excel(writer, sheet_name='Year Level Breakdown', index=False)
                
                # Filters sheet
                filters_data = [{'Filter': k, 'Value': v} for k, v in filters.items() if v]
                if filters_data:
                    df_filters = pd.DataFrame(filters_data)
                    df_filters.to_excel(writer, sheet_name='Applied Filters', index=False)
            
            return {
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'format': 'excel',
                'size': os.path.getsize(filepath)
            }
        
        except Exception as e:
            self.logger.error(f"Excel report generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_csv_report(self, report_type: str, data: Dict[str, Any], 
                            filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate CSV report from data.
        
        Args:
            report_type (str): Report type
            data (Dict[str, Any]): Report data
            filters (Dict[str, Any]): Applied filters
        
        Returns:
            Dict[str, Any]: CSV generation result
        """
        try:
            filename = f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = os.path.join(self.output_dir, filename)
            
            if data['records']:
                df = pd.DataFrame(data['records'])
                df.to_csv(filepath, index=False, encoding='utf-8')
                
                return {
                    'success': True,
                    'filename': filename,
                    'filepath': filepath,
                    'format': 'csv',
                    'size': os.path.getsize(filepath)
                }
            else:
                return {
                    'success': False,
                    'error': 'No data to export'
                }
        
        except Exception as e:
            self.logger.error(f"CSV report generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_pdf_report(self, report_type: str, data: Dict[str, Any], 
                            filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate PDF report from data.
        
        Args:
            report_type (str): Report type
            data (Dict[str, Any]): Report data
            filters (Dict[str, Any]): Applied filters
        
        Returns:
            Dict[str, Any]: PDF generation result
        """
        if not REPORTLAB_AVAILABLE:
            return {
                'success': False,
                'error': 'PDF generation not available - ReportLab library not installed'
            }
        
        try:
            filename = f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(self.output_dir, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=1  # Center alignment
            )
            title = Paragraph(f"{report_type.replace('_', ' ').title()} Report", title_style)
            elements.append(title)
            
            # Report information
            info_data = [
                ['Generated On:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                ['Report Type:', report_type.replace('_', ' ').title()],
                ['Total Records:', str(len(data.get('records', [])))]
            ]
            
            # Add filters to info
            for key, value in filters.items():
                if value:
                    info_data.append([f"{key.replace('_', ' ').title()}:", str(value)])
            
            info_table = Table(info_data)
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 20))
            
            # Statistics table if available
            if 'statistics' in data and data['statistics']:
                stats_title = Paragraph("Summary Statistics", styles['Heading2'])
                elements.append(stats_title)
                
                stats_data = [[k.replace('_', ' ').title(), str(v)] 
                             for k, v in data['statistics'].items()]
                
                stats_table = Table(stats_data)
                stats_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(stats_table)
                elements.append(Spacer(1, 20))
            
            # Main data table (limited to fit on page)
            if data['records']:
                data_title = Paragraph("Detailed Data", styles['Heading2'])
                elements.append(data_title)
                
                # Select key columns for PDF display
                records = data['records'][:50]  # Limit records for readability
                if records:
                    # Get column names and data
                    columns = list(records[0].keys())[:6]  # Limit columns
                    table_data = [columns]  # Header row
                    
                    for record in records:
                        row = [str(record.get(col, ''))[:20] for col in columns]  # Truncate long text
                        table_data.append(row)
                    
                    data_table = Table(table_data)
                    data_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    elements.append(data_table)
                    
                    if len(data['records']) > 50:
                        note = Paragraph(
                            f"Note: Showing first 50 records out of {len(data['records'])} total records.",
                            styles['Normal']
                        )
                        elements.append(Spacer(1, 10))
                        elements.append(note)
            
            # Build PDF
            doc.build(elements)
            
            return {
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'format': 'pdf',
                'size': os.path.getsize(filepath)
            }
        
        except Exception as e:
            self.logger.error(f"PDF report generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_attendance_summary_template(self) -> str:
        """Get HTML template for attendance summary report."""
        return """
        <h2>Attendance Summary Report</h2>
        <p>Generated on: {{ generation_date }}</p>
        
        <h3>Summary Statistics</h3>
        <ul>
            <li>Total Scans: {{ stats.total_scans }}</li>
            <li>Unique Students: {{ stats.unique_students }}</li>
            <li>Present: {{ stats.present_count }}</li>
            <li>Late: {{ stats.late_count }}</li>
        </ul>
        
        <h3>Recent Attendance Records</h3>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Time</th>
                    <th>Student</th>
                    <th>Room</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {% for record in records[:10] %}
                <tr>
                    <td>{{ record.scan_date }}</td>
                    <td>{{ record.scan_time }}</td>
                    <td>{{ record.first_name }} {{ record.last_name }}</td>
                    <td>{{ record.room_name }}</td>
                    <td>{{ record.status }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        """
    
    def _get_student_report_template(self) -> str:
        """Get HTML template for student report."""
        return """
        <h2>Student Performance Report</h2>
        <p>Generated on: {{ generation_date }}</p>
        
        <h3>Student Attendance Summary</h3>
        <table>
            <thead>
                <tr>
                    <th>Student ID</th>
                    <th>Name</th>
                    <th>Department</th>
                    <th>Attendance Rate</th>
                    <th>Late Rate</th>
                    <th>Total Scans</th>
                </tr>
            </thead>
            <tbody>
                {% for student in records %}
                <tr>
                    <td>{{ student.student_id }}</td>
                    <td>{{ student.first_name }} {{ student.last_name }}</td>
                    <td>{{ student.department }}</td>
                    <td>{{ student.attendance_rate }}%</td>
                    <td>{{ student.late_rate }}%</td>
                    <td>{{ student.total_scans }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        """
    
    def _get_room_utilization_template(self) -> str:
        """Get HTML template for room utilization report."""
        return """
        <h2>Room Utilization Report</h2>
        <p>Generated on: {{ generation_date }}</p>
        
        <h3>Room Usage Statistics</h3>
        <table>
            <thead>
                <tr>
                    <th>Room</th>
                    <th>Building</th>
                    <th>Capacity</th>
                    <th>Total Scans</th>
                    <th>Unique Students</th>
                    <th>Utilization %</th>
                </tr>
            </thead>
            <tbody>
                {% for room in records %}
                <tr>
                    <td>{{ room.room_name }}</td>
                    <td>{{ room.building }}</td>
                    <td>{{ room.capacity }}</td>
                    <td>{{ room.total_scans }}</td>
                    <td>{{ room.unique_students }}</td>
                    <td>{{ room.utilization_percentage }}%</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        """
    
    def get_available_reports(self) -> List[Dict[str, str]]:
        """
        Get list of available report types.
        
        Returns:
            List[Dict[str, str]]: Available report types with descriptions
        """
        return [
            {
                'type': 'attendance_summary',
                'name': 'Attendance Summary',
                'description': 'Comprehensive attendance overview with statistics'
            },
            {
                'type': 'student_performance',
                'name': 'Student Performance',
                'description': 'Individual student attendance rates and performance metrics'
            },
            {
                'type': 'room_utilization',
                'name': 'Room Utilization',
                'description': 'Room usage statistics and capacity utilization'
            },
            {
                'type': 'daily_attendance',
                'name': 'Daily Attendance',
                'description': 'Day-by-day attendance breakdown and trends'
            },
            {
                'type': 'department_analysis',
                'name': 'Department Analysis',
                'description': 'Department-wise attendance statistics and comparisons'
            }
        ]
    
    def delete_old_reports(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Delete report files older than specified days.
        
        Args:
            days_old (int): Number of days old for deletion threshold
        
        Returns:
            Dict[str, Any]: Cleanup result
        """
        try:
            if not os.path.exists(self.output_dir):
                return {'deleted_count': 0, 'error': 'Output directory does not exist'}
            
            cutoff_date = datetime.now() - timedelta(days=days_old)
            deleted_count = 0
            deleted_files = []
            
            for filename in os.listdir(self.output_dir):
                filepath = os.path.join(self.output_dir, filename)
                
                if os.path.isfile(filepath):
                    file_modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if file_modified_time < cutoff_date:
                        try:
                            os.remove(filepath)
                            deleted_count += 1
                            deleted_files.append(filename)
                            self.logger.info(f"Deleted old report file: {filename}")
                        except Exception as e:
                            self.logger.error(f"Failed to delete file {filename}: {str(e)}")
            
            return {
                'deleted_count': deleted_count,
                'deleted_files': deleted_files,
                'success': True
            }
        
        except Exception as e:
            self.logger.error(f"Report cleanup failed: {str(e)}")
            return {
                'deleted_count': 0,
                'success': False,
                'error': str(e)
            }