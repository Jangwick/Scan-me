# QR Code Attendance System

A comprehensive Flask-based attendance tracking system using QR code scanning technology.

## Features

### Core Functionality
- **QR Code Scanning**: Fast and accurate QR code scanning for attendance recording
- **Real-time Display**: Live attendance updates and notifications
- **Room-Based Management**: Organize attendance by rooms and locations
- **Automated Logging**: Automatic attendance recording with timestamps
- **Duplicate Prevention**: Intelligent duplicate scan detection
- **Late Tracking**: Automatic late arrival detection and marking

### Advanced Features
- **Professor Dashboard**: Comprehensive dashboard for educators
- **Automated Reports**: Generate detailed attendance reports
- **Data Export**: Export to Excel, CSV, and PDF formats
- **Email Notifications**: Real-time email alerts and notifications
- **Role-Based Access**: Multi-level user authentication system
- **Bulk Operations**: Mass QR code generation and student management
- **Analytics**: Detailed attendance statistics and trends
- **Mobile Responsive**: Works on desktop, tablet, and mobile devices

### Technical Features
- **WebSocket Support**: Real-time updates without page refresh
- **Offline Capability**: Service worker for offline functionality
- **Security**: Encrypted QR codes with expiration tokens
- **Performance**: Optimized database queries and caching
- **Scalability**: Designed to handle large student populations

## Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript, Tailwind CSS
- **Database**: SQLite with WAL mode for better concurrency
- **QR Processing**: qrcode library with PIL for image generation
- **Charts**: Chart.js for analytics visualization
- **UI Framework**: Alpine.js for reactive components
- **Icons**: Font Awesome for comprehensive iconography

## Project Structure

```
Scan-me/
├── app.py                      # Main Flask application
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── app/
│   ├── modules/               # Core business logic modules
│   │   ├── database_manager.py      # Database operations
│   │   ├── qr_generator.py          # QR code generation/validation
│   │   ├── attendance_manager.py    # Attendance processing
│   │   ├── report_generator.py      # Report generation
│   │   ├── notification_system.py   # Notifications & alerts
│   │   ├── auth_manager.py          # Authentication & authorization
│   │   ├── room_manager.py          # Room management
│   │   └── student_manager.py       # Student operations
│   ├── templates/             # HTML templates
│   │   ├── index.html               # Homepage
│   │   ├── login.html               # Login page
│   │   ├── dashboard.html           # Main dashboard
│   │   └── scan.html                # QR scanner interface
│   └── static/                # Static assets
│       ├── css/
│       │   └── style.css            # Custom CSS styles
│       ├── js/
│       │   └── main.js              # JavaScript functionality
│       └── qr_codes/               # Generated QR codes
├── database/                  # Database files
├── uploads/                   # File uploads
├── reports/                   # Generated reports
└── logs/                      # Application logs
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)
- Modern web browser with camera support

### Quick Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Scan-me
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   - Open your browser and navigate to `http://localhost:5000`
   - Default admin login: `admin` / `admin123`
   - Default professor login: `professor1` / `prof123`

## Configuration

### Environment Variables
Create a `.env` file in the root directory:

```env
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database
DATABASE_PATH=database/attendance.db

# Email Configuration (optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com

# Security
BCRYPT_LOG_ROUNDS=12
MAX_LOGIN_ATTEMPTS=5

# WebSocket (optional)
WEBSOCKET_ENABLED=True
```

### Application Settings
Edit `config.py` to customize:

- **QR Code Settings**: Size, error correction, expiry time
- **Attendance Rules**: Late threshold, duplicate detection window
- **Security Policies**: Password requirements, session timeout
- **Email Templates**: Notification message customization
- **Database Settings**: Connection pooling, performance tuning

## Usage Guide

### For Administrators

1. **Initial Setup**
   - Login with admin credentials
   - Configure rooms in Admin Panel
   - Add professors and staff users
   - Import student data (CSV supported)

2. **Student Management**
   - Add students individually or via CSV import
   - Generate QR codes for students
   - Manage student information and status
   - Export student lists

3. **Room Management**
   - Create and configure rooms
   - Set room capacity and schedules
   - Assign professors to rooms
   - Monitor room utilization

4. **System Monitoring**
   - View system status and health
   - Monitor attendance statistics
   - Review security logs
   - Manage user permissions

### For Professors

1. **Dashboard Access**
   - View assigned rooms and schedules
   - Monitor real-time attendance
   - Check student status and history
   - Access quick statistics

2. **Attendance Management**
   - Use QR scanner for manual entry
   - Review and edit attendance records
   - Mark late arrivals and absences
   - Generate class reports

3. **Reporting**
   - Create attendance reports by date range
   - Export data in multiple formats
   - Email reports to stakeholders
   - Analyze attendance trends

### For Students

1. **QR Code Usage**
   - Obtain QR code from administrator
   - Keep QR code secure and accessible
   - Scan QR code upon room entry
   - Verify attendance confirmation

2. **Attendance Tracking**
   - Check personal attendance history
   - View attendance statistics
   - Receive notifications for absences
   - Update personal information

## API Reference

### Authentication Endpoints
```
POST /api/login          # User authentication
POST /api/logout         # User logout
GET  /api/user/profile   # Get user profile
```

### Attendance Endpoints
```
POST /api/scan           # Process QR code scan
GET  /api/attendance     # Get attendance records
GET  /api/stats          # Get attendance statistics
```

### Management Endpoints
```
GET  /api/students       # List students
POST /api/students       # Create student
GET  /api/rooms          # List rooms
POST /api/qr/generate    # Generate QR code
```

### Report Endpoints
```
GET  /api/reports        # List available reports
POST /api/reports/generate # Generate report
GET  /api/export         # Export data
```

## Database Schema

### Core Tables

**students**
- student_id (PRIMARY KEY)
- first_name, last_name
- email, phone
- department, year_level, section
- qr_code_path, qr_security_token
- created_at, updated_at

**rooms**
- room_id (PRIMARY KEY)
- room_name, building
- capacity, room_type
- schedule_start, schedule_end
- created_at, updated_at

**attendance_scans**
- scan_id (PRIMARY KEY)
- student_id (FOREIGN KEY)
- room_id (FOREIGN KEY)
- scan_date, scan_time
- status (present/late/absent)
- created_at

**users**
- user_id (PRIMARY KEY)
- username, password_hash
- full_name, email
- user_type (admin/professor/staff/user)
- created_at, last_login

## Security Features

### Data Protection
- **Password Hashing**: Bcrypt with configurable rounds
- **Session Security**: Secure cookies with HTTPS support
- **QR Code Security**: Encrypted tokens with expiration
- **SQL Injection Prevention**: Parameterized queries
- **XSS Protection**: Template escaping and CSP headers

### Access Control
- **Role-Based Access**: Multiple user types with different permissions
- **Session Management**: Automatic timeout and regeneration
- **Login Protection**: Rate limiting and account lockout
- **Audit Logging**: Comprehensive activity tracking

### Privacy
- **Data Minimization**: Only necessary data collection
- **Secure Storage**: Encrypted sensitive information
- **Access Logging**: Monitor data access patterns
- **Data Retention**: Configurable cleanup policies

## Performance Optimization

### Database
- **Connection Pooling**: Efficient connection management
- **Query Optimization**: Indexed searches and efficient joins
- **WAL Mode**: Better concurrent access
- **Regular Maintenance**: Automated VACUUM and ANALYZE

### Application
- **Caching**: Memory-based result caching
- **Lazy Loading**: On-demand data loading
- **Compression**: Response compression for faster transfers
- **CDN Integration**: Static asset delivery optimization

### Frontend
- **Minification**: Compressed CSS and JavaScript
- **Progressive Loading**: Staged content delivery
- **Service Workers**: Offline functionality and caching
- **Responsive Design**: Mobile-optimized interfaces

## Troubleshooting

### Common Issues

1. **Camera Not Working**
   - Check browser permissions for camera access
   - Ensure HTTPS for production deployments
   - Verify camera drivers and hardware

2. **QR Code Not Scanning**
   - Ensure good lighting conditions
   - Check QR code image quality
   - Verify QR code hasn't expired
   - Clean camera lens

3. **Database Errors**
   - Check file permissions on database directory
   - Verify SQLite installation
   - Review connection settings
   - Check disk space availability

4. **Email Not Sending**
   - Verify SMTP server settings
   - Check email credentials
   - Review firewall and port settings
   - Test with email provider's settings

### Debugging

1. **Enable Debug Mode**
   ```python
   # In config.py
   DEBUG = True
   LOG_LEVEL = 'DEBUG'
   ```

2. **Check Logs**
   ```bash
   tail -f logs/attendance.log
   ```

3. **Database Inspection**
   ```bash
   sqlite3 database/attendance.db
   .schema
   SELECT * FROM students LIMIT 5;
   ```

4. **Test API Endpoints**
   ```bash
   curl -X GET http://localhost:5000/api/stats
   ```

## Deployment

### Development Deployment
```bash
# Clone and setup
git clone <repo-url>
cd Scan-me
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run development server
python app.py
```

### Production Deployment

1. **Using Gunicorn (Linux/macOS)**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **Using Docker**
   ```dockerfile
   FROM python:3.9-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   EXPOSE 5000
   CMD ["python", "app.py"]
   ```

3. **Using Apache/Nginx**
   - Configure reverse proxy
   - Set up SSL certificates
   - Configure static file serving

### Environment Configuration
```bash
# Production settings
export FLASK_ENV=production
export SECRET_KEY="your-production-secret-key"
export DATABASE_PATH="/var/lib/attendance/attendance.db"
```

## Contributing

1. **Fork the Repository**
2. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-feature
   ```
3. **Make Changes**
   - Follow PEP 8 style guide
   - Add comprehensive tests
   - Update documentation
4. **Commit Changes**
   ```bash
   git commit -m "Add new feature: description"
   ```
5. **Push and Create PR**

### Development Guidelines
- Write comprehensive docstrings
- Add unit tests for new functions
- Follow existing code structure
- Update requirements.txt if adding dependencies
- Test on multiple browsers and devices

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

### Documentation
- **API Documentation**: Available at `/api/docs` when running
- **User Manual**: Comprehensive guide in `docs/` directory
- **FAQ**: Common questions and solutions

### Contact
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Community discussions on GitHub
- **Email**: Technical support via email

### Updates
- **Version History**: See CHANGELOG.md
- **Roadmap**: Planned features in ROADMAP.md
- **Migration Guide**: Upgrade instructions for major versions

## Acknowledgments

- **Flask Team**: Web framework foundation
- **Tailwind CSS**: Utility-first CSS framework
- **Chart.js**: Beautiful chart rendering
- **QR Code Libraries**: QR code generation and processing
- **Community Contributors**: Bug reports and feature suggestions

---

**QR Code Attendance System** - Making attendance tracking simple, secure, and efficient.

For more information, visit our [documentation](docs/) or [contact support](mailto:support@attendance.local).