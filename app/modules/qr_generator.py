"""
QR Code Generator Module - Flask QR Code Attendance System
Author: GitHub Copilot
Date: September 2025

This module handles QR code generation and validation for the attendance system.
It provides comprehensive QR code creation with customizable options, validation,
and integration with the student database. The module ensures unique QR codes
for each student and provides utilities for QR code management.

Features:
- Dynamic QR code generation
- Customizable QR code styling
- QR code validation and verification
- Batch QR code generation
- QR code image export
- Student QR code management
- Error correction and optimization
"""

import qrcode
try:
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, SquareModuleDrawer, CircleModuleDrawer
    from qrcode.image.styles.colorfills import SolidFillColorMask, SquareGradiantColorMask
    STYLED_QR_AVAILABLE = True
except ImportError:
    STYLED_QR_AVAILABLE = False
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import json
import hashlib
import secrets
import string
from datetime import datetime, timedelta
import os
import logging
from typing import Optional, Dict, Any, List, Tuple

class QRGenerator:
    """
    Comprehensive QR code generator for the attendance system.
    Handles creation, validation, and management of QR codes for students
    with customizable styling and security features.
    """
    
    def __init__(self):
        """Initialize the QR code generator with default settings."""
        self.logger = logging.getLogger(__name__)
        
        # Default QR code settings
        self.default_settings = {
            'version': 1,  # Controls the size of the QR Code
            'error_correction': qrcode.constants.ERROR_CORRECT_M,  # ~15% error correction
            'box_size': 10,  # Size of each box in pixels
            'border': 4,    # Size of the border (minimum is 4)
            'fill_color': 'black',
            'back_color': 'white'
        }
        
        # Styling options
        self.style_options = {}
        if STYLED_QR_AVAILABLE:
            self.style_options = {
                'module_drawer': {
                    'square': SquareModuleDrawer(),
                    'rounded': RoundedModuleDrawer(),
                    'circle': CircleModuleDrawer()
                }
            }
        
        # Security settings
        self.security_settings = {
            'token_length': 32,
            'include_timestamp': True,
            'include_checksum': True,
            'encryption_key': self._generate_encryption_key()
        }
    
    def _generate_encryption_key(self) -> str:
        """
        Generate a secure encryption key for QR code data.
        
        Returns:
            str: Base64 encoded encryption key
        """
        key = secrets.token_bytes(32)
        return base64.b64encode(key).decode('utf-8')
    
    def _generate_secure_token(self, student_id: str, additional_data: dict = None) -> str:
        """
        Generate a secure token for QR code data.
        
        Args:
            student_id (str): Student ID
            additional_data (dict): Additional data to include
        
        Returns:
            str: Secure token string
        """
        # Create base data
        token_data = {
            'student_id': student_id,
            'generated_at': datetime.now().isoformat(),
            'token': secrets.token_urlsafe(self.security_settings['token_length'])
        }
        
        # Add additional data if provided
        if additional_data:
            token_data.update(additional_data)
        
        # Create JSON string
        json_data = json.dumps(token_data, sort_keys=True)
        
        # Add checksum if enabled
        if self.security_settings['include_checksum']:
            checksum = hashlib.sha256(json_data.encode()).hexdigest()[:16]
            token_data['checksum'] = checksum
            json_data = json.dumps(token_data, sort_keys=True)
        
        return json_data
    
    def generate_student_qr_code(self, student_data: dict, 
                                style: str = 'default',
                                custom_settings: dict = None) -> dict:
        """
        Generate a QR code for a student with their information.
        
        Args:
            student_data (dict): Student information
            style (str): QR code style preference
            custom_settings (dict): Custom QR code settings
        
        Returns:
            dict: QR code generation result with image data
        """
        try:
            # Validate required student data
            required_fields = ['id', 'student_id', 'first_name', 'last_name', 'department']
            for field in required_fields:
                if field not in student_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Generate secure QR code data
            qr_data = self._generate_secure_token(
                student_data['student_id'],
                {
                    'name': f"{student_data['first_name']} {student_data['last_name']}",
                    'department': student_data['department'],
                    'year': student_data.get('year_level', ''),
                    'section': student_data.get('section', ''),
                    'type': 'student_attendance'
                }
            )
            
            # Apply custom settings if provided
            settings = self.default_settings.copy()
            if custom_settings:
                settings.update(custom_settings)
            
            # Create QR code instance
            qr = qrcode.QRCode(
                version=settings['version'],
                error_correction=settings['error_correction'],
                box_size=settings['box_size'],
                border=settings['border']
            )
            
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Generate QR code image based on style
            if style == 'styled' and 'module_drawer' in settings and STYLED_QR_AVAILABLE:
                img = qr.make_image(
                    image_factory=StyledPilImage,
                    module_drawer=settings['module_drawer']
                )
            else:
                img = qr.make_image(
                    fill_color=settings['fill_color'],
                    back_color=settings['back_color']
                )
            
            # Add student information overlay if requested
            if style == 'with_info':
                img = self._add_student_info_overlay(img, student_data)
            
            # Convert image to base64 string
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Generate filename
            filename = f"qr_{student_data['student_id']}_{datetime.now().strftime('%Y%m%d')}.png"
            
            result = {
                'success': True,
                'qr_data': qr_data,
                'image_base64': img_base64,
                'image_size': img.size,
                'filename': filename,
                'student_id': student_data['student_id'],
                'generated_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"QR code generated successfully for student {student_data['student_id']}")
            return result
        
        except Exception as e:
            self.logger.error(f"QR code generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'student_id': student_data.get('student_id', 'unknown')
            }
    
    def _add_student_info_overlay(self, qr_img: Image.Image, student_data: dict) -> Image.Image:
        """
        Add student information overlay to QR code image.
        
        Args:
            qr_img (Image.Image): QR code image
            student_data (dict): Student information
        
        Returns:
            Image.Image: QR code with overlay
        """
        try:
            # Create a larger canvas to accommodate text
            original_size = qr_img.size
            new_height = original_size[1] + 120  # Add space for text
            new_img = Image.new('RGB', (original_size[0], new_height), 'white')
            
            # Paste QR code at the top
            new_img.paste(qr_img, (0, 0))
            
            # Add text overlay
            draw = ImageDraw.Draw(new_img)
            
            # Try to use a better font, fallback to default if not available
            try:
                font_large = ImageFont.truetype("arial.ttf", 16)
                font_small = ImageFont.truetype("arial.ttf", 12)
            except (IOError, OSError):
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Student information to display
            student_name = f"{student_data.get('first_name', '')} {student_data.get('last_name', '')}"
            student_id = student_data.get('student_id', '')
            department = student_data.get('department', '')
            year_section = f"Year {student_data.get('year_level', '')} - Section {student_data.get('section', '')}"
            
            # Calculate text positions (centered)
            img_width = new_img.size[0]
            text_y = original_size[1] + 10
            
            # Draw student information
            name_bbox = draw.textbbox((0, 0), student_name, font=font_large)
            name_width = name_bbox[2] - name_bbox[0]
            draw.text(((img_width - name_width) // 2, text_y), student_name, 
                     fill='black', font=font_large)
            
            id_bbox = draw.textbbox((0, 0), student_id, font=font_small)
            id_width = id_bbox[2] - id_bbox[0]
            draw.text(((img_width - id_width) // 2, text_y + 25), student_id, 
                     fill='black', font=font_small)
            
            dept_bbox = draw.textbbox((0, 0), department, font=font_small)
            dept_width = dept_bbox[2] - dept_bbox[0]
            draw.text(((img_width - dept_width) // 2, text_y + 45), department, 
                     fill='black', font=font_small)
            
            if year_section.strip() != "Year  - Section ":
                yr_bbox = draw.textbbox((0, 0), year_section, font=font_small)
                yr_width = yr_bbox[2] - yr_bbox[0]
                draw.text(((img_width - yr_width) // 2, text_y + 65), year_section, 
                         fill='black', font=font_small)
            
            return new_img
        
        except Exception as e:
            self.logger.warning(f"Failed to add overlay, returning original QR code: {str(e)}")
            return qr_img
    
    def validate_qr_code(self, qr_data: str) -> dict:
        """
        Validate and decode QR code data.
        
        Args:
            qr_data (str): QR code data string
        
        Returns:
            dict: Validation result with decoded data
        """
        try:
            # Parse JSON data
            try:
                decoded_data = json.loads(qr_data)
            except json.JSONDecodeError:
                return {
                    'valid': False,
                    'error': 'Invalid QR code format',
                    'error_type': 'format_error'
                }
            
            # Check required fields
            required_fields = ['student_id', 'generated_at', 'token', 'type']
            for field in required_fields:
                if field not in decoded_data:
                    return {
                        'valid': False,
                        'error': f'Missing required field: {field}',
                        'error_type': 'missing_field'
                    }
            
            # Validate checksum if present
            if 'checksum' in decoded_data:
                data_without_checksum = {k: v for k, v in decoded_data.items() if k != 'checksum'}
                json_data = json.dumps(data_without_checksum, sort_keys=True)
                expected_checksum = hashlib.sha256(json_data.encode()).hexdigest()[:16]
                
                if decoded_data['checksum'] != expected_checksum:
                    return {
                        'valid': False,
                        'error': 'Invalid checksum',
                        'error_type': 'security_error'
                    }
            
            # Check if QR code is for student attendance
            if decoded_data.get('type') != 'student_attendance':
                return {
                    'valid': False,
                    'error': 'Invalid QR code type',
                    'error_type': 'type_error'
                }
            
            # Check expiration (if applicable)
            try:
                generated_at = datetime.fromisoformat(decoded_data['generated_at'])
                # QR codes expire after 1 year for security
                if datetime.now() - generated_at > timedelta(days=365):
                    return {
                        'valid': False,
                        'error': 'QR code has expired',
                        'error_type': 'expired'
                    }
            except ValueError:
                return {
                    'valid': False,
                    'error': 'Invalid timestamp format',
                    'error_type': 'format_error'
                }
            
            return {
                'valid': True,
                'data': decoded_data,
                'student_id': decoded_data['student_id'],
                'generated_at': decoded_data['generated_at']
            }
        
        except Exception as e:
            self.logger.error(f"QR code validation error: {str(e)}")
            return {
                'valid': False,
                'error': 'Validation failed',
                'error_type': 'system_error'
            }
    
    def batch_generate_qr_codes(self, students_list: List[dict], 
                               style: str = 'default',
                               custom_settings: dict = None) -> dict:
        """
        Generate QR codes for multiple students in batch.
        
        Args:
            students_list (List[dict]): List of student data
            style (str): QR code style
            custom_settings (dict): Custom settings
        
        Returns:
            dict: Batch generation results
        """
        try:
            results = {
                'success': True,
                'total_students': len(students_list),
                'successful': 0,
                'failed': 0,
                'results': [],
                'errors': []
            }
            
            for student_data in students_list:
                try:
                    qr_result = self.generate_student_qr_code(
                        student_data, style, custom_settings
                    )
                    
                    if qr_result['success']:
                        results['successful'] += 1
                        results['results'].append({
                            'student_id': student_data['student_id'],
                            'qr_data': qr_result['qr_data'],
                            'filename': qr_result['filename']
                        })
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'student_id': student_data.get('student_id', 'unknown'),
                            'error': qr_result['error']
                        })
                
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'student_id': student_data.get('student_id', 'unknown'),
                        'error': str(e)
                    })
            
            if results['failed'] > 0:
                results['success'] = False
            
            self.logger.info(f"Batch QR generation completed: {results['successful']}/{results['total_students']} successful")
            return results
        
        except Exception as e:
            self.logger.error(f"Batch QR generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'total_students': len(students_list) if students_list else 0,
                'successful': 0,
                'failed': len(students_list) if students_list else 0
            }
    
    def save_qr_code_image(self, image_base64: str, filename: str, 
                          output_dir: str = 'exports/qr_codes') -> bool:
        """
        Save QR code image to file system.
        
        Args:
            image_base64 (str): Base64 encoded image
            filename (str): Output filename
            output_dir (str): Output directory
        
        Returns:
            bool: Success status
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Decode base64 image
            image_data = base64.b64decode(image_base64)
            
            # Save to file
            file_path = os.path.join(output_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(image_data)
            
            self.logger.info(f"QR code image saved to {file_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to save QR code image: {str(e)}")
            return False
    
    def create_bulk_qr_pdf(self, qr_results: List[dict], 
                          output_filename: str = None) -> dict:
        """
        Create a PDF containing multiple QR codes for printing.
        
        Args:
            qr_results (List[dict]): List of QR generation results
            output_filename (str): Output PDF filename
        
        Returns:
            dict: PDF creation result
        """
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.utils import ImageReader
            import io
            
            if not output_filename:
                output_filename = f"student_qr_codes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            output_path = os.path.join('exports', output_filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create PDF
            c = canvas.Canvas(output_path, pagesize=A4)
            width, height = A4
            
            # QR codes per page (2x3 grid)
            qr_per_row = 2
            qr_per_col = 3
            qr_per_page = qr_per_row * qr_per_col
            
            qr_width = width / qr_per_row * 0.8
            qr_height = height / qr_per_col * 0.8
            
            for i, qr_result in enumerate(qr_results):
                if i > 0 and i % qr_per_page == 0:
                    c.showPage()  # New page
                
                # Calculate position
                row = (i % qr_per_page) // qr_per_row
                col = (i % qr_per_page) % qr_per_row
                
                x = col * (width / qr_per_row) + (width / qr_per_row - qr_width) / 2
                y = height - (row + 1) * (height / qr_per_col) + (height / qr_per_col - qr_height) / 2
                
                # Add QR code image
                img_data = base64.b64decode(qr_result['image_base64'])
                img_buffer = io.BytesIO(img_data)
                img_reader = ImageReader(img_buffer)
                
                c.drawImage(img_reader, x, y, width=qr_width, height=qr_height)
            
            c.save()
            
            return {
                'success': True,
                'filename': output_filename,
                'path': output_path,
                'total_qr_codes': len(qr_results)
            }
        
        except ImportError:
            return {
                'success': False,
                'error': 'ReportLab library not available for PDF generation'
            }
        except Exception as e:
            self.logger.error(f"PDF generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_qr_code_stats(self, qr_data_list: List[str]) -> dict:
        """
        Analyze statistics from a list of QR code data.
        
        Args:
            qr_data_list (List[str]): List of QR code data strings
        
        Returns:
            dict: Statistics summary
        """
        try:
            stats = {
                'total_qr_codes': len(qr_data_list),
                'valid_codes': 0,
                'invalid_codes': 0,
                'expired_codes': 0,
                'departments': {},
                'generation_dates': {},
                'errors': []
            }
            
            for qr_data in qr_data_list:
                validation_result = self.validate_qr_code(qr_data)
                
                if validation_result['valid']:
                    stats['valid_codes'] += 1
                    data = validation_result['data']
                    
                    # Department statistics
                    dept = data.get('department', 'Unknown')
                    stats['departments'][dept] = stats['departments'].get(dept, 0) + 1
                    
                    # Generation date statistics
                    gen_date = data.get('generated_at', '')[:10]  # Just the date part
                    stats['generation_dates'][gen_date] = stats['generation_dates'].get(gen_date, 0) + 1
                
                else:
                    stats['invalid_codes'] += 1
                    if validation_result.get('error_type') == 'expired':
                        stats['expired_codes'] += 1
                    
                    stats['errors'].append(validation_result.get('error', 'Unknown error'))
            
            return stats
        
        except Exception as e:
            self.logger.error(f"QR code statistics analysis failed: {str(e)}")
            return {
                'error': str(e),
                'total_qr_codes': len(qr_data_list) if qr_data_list else 0
            }