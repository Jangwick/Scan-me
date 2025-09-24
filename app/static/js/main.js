// Main JavaScript functionality for QR Attendance System
class QRAttendanceSystem {
    constructor() {
        this.wsConnection = null;
        this.notifications = [];
        this.init();
    }
    
    init() {
        this.initializeWebSocket();
        this.setupEventListeners();
        this.loadNotifications();
        this.startPeriodicUpdates();
    }
    
    // WebSocket connection for real-time updates
    initializeWebSocket() {
        if (typeof(WebSocket) !== "undefined") {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            try {
                this.wsConnection = new WebSocket(wsUrl);
                
                this.wsConnection.onopen = () => {
                    console.log('WebSocket connected');
                    this.showNotification('System Connected', 'Real-time updates enabled', 'success');
                };
                
                this.wsConnection.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                };
                
                this.wsConnection.onclose = () => {
                    console.log('WebSocket disconnected');
                    // Attempt to reconnect after 5 seconds
                    setTimeout(() => {
                        this.initializeWebSocket();
                    }, 5000);
                };
                
                this.wsConnection.onerror = (error) => {
                    console.error('WebSocket error:', error);
                };
            } catch (error) {
                console.error('WebSocket not supported or connection failed:', error);
            }
        }
    }
    
    // Handle incoming WebSocket messages
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'scan_update':
                this.updateRecentScans(data.payload);
                this.updateStatistics(data.stats);
                break;
            case 'notification':
                this.showNotification(data.title, data.message, data.level);
                break;
            case 'system_alert':
                this.showSystemAlert(data.message, data.level);
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }
    
    // Update recent scans display
    updateRecentScans(scanData) {
        const recentScansContainer = document.getElementById('recentScans');
        if (recentScansContainer) {
            const scanElement = this.createScanElement(scanData);
            recentScansContainer.insertBefore(scanElement, recentScansContainer.firstChild);
            
            // Remove oldest scan if more than 10
            const scans = recentScansContainer.children;
            if (scans.length > 10) {
                recentScansContainer.removeChild(scans[scans.length - 1]);
            }
        }
    }
    
    // Create scan element for display
    createScanElement(scanData) {
        const scanElement = document.createElement('div');
        scanElement.className = 'activity-item flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition duration-200';
        
        const statusClass = scanData.status === 'present' ? 'green' : 'yellow';
        const statusIcon = scanData.status === 'present' ? 'check' : 'clock';
        
        scanElement.innerHTML = `
            <div class="flex items-center space-x-3">
                <div class="flex-shrink-0">
                    <div class="w-8 h-8 bg-${statusClass}-100 rounded-full flex items-center justify-center">
                        <i class="fas fa-${statusIcon} text-${statusClass}-600 text-sm"></i>
                    </div>
                </div>
                <div>
                    <p class="font-semibold text-gray-800 text-sm">
                        ${scanData.first_name} ${scanData.last_name}
                    </p>
                    <p class="text-xs text-gray-600">
                        ${scanData.room_name} • ${scanData.scan_time}
                    </p>
                </div>
            </div>
            <div class="text-right">
                <span class="text-xs px-2 py-1 rounded-full bg-${statusClass}-100 text-${statusClass}-800">
                    ${scanData.status.charAt(0).toUpperCase() + scanData.status.slice(1)}
                </span>
            </div>
        `;
        
        return scanElement;
    }
    
    // Update statistics display
    updateStatistics(stats) {
        const statElements = {
            todayScans: document.querySelector('[data-stat="today-scans"]'),
            presentToday: document.querySelector('[data-stat="present-today"]'),
            lateToday: document.querySelector('[data-stat="late-today"]'),
            activeRooms: document.querySelector('[data-stat="active-rooms"]')
        };
        
        if (statElements.todayScans) {
            this.animateStatChange(statElements.todayScans, stats.today_scans || 0);
        }
        if (statElements.presentToday) {
            this.animateStatChange(statElements.presentToday, stats.present_today || 0);
        }
        if (statElements.lateToday) {
            this.animateStatChange(statElements.lateToday, stats.late_today || 0);
        }
        if (statElements.activeRooms) {
            this.animateStatChange(statElements.activeRooms, stats.active_rooms || 0);
        }
    }
    
    // Animate statistic value changes
    animateStatChange(element, newValue) {
        const currentValue = parseInt(element.textContent) || 0;
        if (currentValue === newValue) return;
        
        element.style.transform = 'scale(1.1)';
        element.style.transition = 'transform 0.2s ease';
        
        setTimeout(() => {
            element.textContent = newValue;
            element.style.transform = 'scale(1)';
        }, 100);
    }
    
    // Setup event listeners
    setupEventListeners() {
        // Navigation mobile toggle
        const mobileMenuButton = document.getElementById('mobile-menu-button');
        const mobileMenu = document.getElementById('mobile-menu');
        
        if (mobileMenuButton && mobileMenu) {
            mobileMenuButton.addEventListener('click', () => {
                mobileMenu.classList.toggle('hidden');
            });
        }
        
        // Notification click handlers
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-notification-close]')) {
                e.target.closest('[data-notification]').remove();
            }
        });
        
        // Form validation
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', this.handleFormSubmit.bind(this));
        });
        
        // Auto-refresh data periodically
        this.startPeriodicUpdates();
    }
    
    // Handle form submissions with validation
    handleFormSubmit(event) {
        const form = event.target;
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                this.showFieldError(field, 'This field is required');
            } else {
                this.clearFieldError(field);
            }
        });
        
        if (!isValid) {
            event.preventDefault();
            this.showNotification('Form Error', 'Please fill in all required fields', 'error');
        }
    }
    
    // Show field error
    showFieldError(field, message) {
        field.classList.add('border-red-300', 'bg-red-50');
        
        let errorElement = field.parentNode.querySelector('.field-error');
        if (!errorElement) {
            errorElement = document.createElement('p');
            errorElement.className = 'field-error text-sm text-red-600 mt-1';
            field.parentNode.appendChild(errorElement);
        }
        errorElement.textContent = message;
    }
    
    // Clear field error
    clearFieldError(field) {
        field.classList.remove('border-red-300', 'bg-red-50');
        const errorElement = field.parentNode.querySelector('.field-error');
        if (errorElement) {
            errorElement.remove();
        }
    }
    
    // Show notification popup
    showNotification(title, message, type = 'info', duration = 5000) {
        const notification = {
            id: Date.now(),
            title,
            message,
            type,
            timestamp: new Date()
        };
        
        this.notifications.unshift(notification);
        this.displayNotification(notification);
        
        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                this.removeNotification(notification.id);
            }, duration);
        }
    }
    
    // Display notification in UI
    displayNotification(notification) {
        const container = this.getNotificationContainer();
        const notificationElement = this.createNotificationElement(notification);
        
        container.appendChild(notificationElement);
        
        // Animate in
        setTimeout(() => {
            notificationElement.classList.add('opacity-100', 'translate-x-0');
            notificationElement.classList.remove('opacity-0', 'translate-x-full');
        }, 100);
    }
    
    // Create notification element
    createNotificationElement(notification) {
        const element = document.createElement('div');
        element.className = `fixed top-4 right-4 max-w-sm w-full bg-white border-l-4 rounded-lg shadow-lg transform transition-all duration-300 opacity-0 translate-x-full z-50`;
        element.setAttribute('data-notification-id', notification.id);
        
        const borderColor = {
            success: 'border-green-500',
            error: 'border-red-500',
            warning: 'border-yellow-500',
            info: 'border-blue-500'
        }[notification.type] || 'border-blue-500';
        
        const iconClass = {
            success: 'fas fa-check-circle text-green-500',
            error: 'fas fa-exclamation-circle text-red-500',
            warning: 'fas fa-exclamation-triangle text-yellow-500',
            info: 'fas fa-info-circle text-blue-500'
        }[notification.type] || 'fas fa-info-circle text-blue-500';
        
        element.className += ` ${borderColor}`;
        
        element.innerHTML = `
            <div class="p-4">
                <div class="flex items-center justify-between">
                    <div class="flex items-center">
                        <i class="${iconClass} mr-3"></i>
                        <div>
                            <p class="font-semibold text-gray-800">${notification.title}</p>
                            <p class="text-gray-600 text-sm">${notification.message}</p>
                        </div>
                    </div>
                    <button 
                        data-notification-close 
                        class="text-gray-400 hover:text-gray-600 ml-3"
                    >
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;
        
        return element;
    }
    
    // Get or create notification container
    getNotificationContainer() {
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'fixed top-0 right-0 p-4 space-y-2 z-50';
            document.body.appendChild(container);
        }
        return container;
    }
    
    // Remove notification
    removeNotification(id) {
        const element = document.querySelector(`[data-notification-id="${id}"]`);
        if (element) {
            element.classList.add('opacity-0', 'translate-x-full');
            setTimeout(() => {
                element.remove();
            }, 300);
        }
        
        this.notifications = this.notifications.filter(n => n.id !== id);
    }
    
    // Show system alert
    showSystemAlert(message, level = 'info') {
        const alert = document.createElement('div');
        alert.className = `fixed top-0 left-0 right-0 p-4 text-center font-semibold z-50`;
        
        const bgColor = {
            success: 'bg-green-600',
            error: 'bg-red-600',
            warning: 'bg-yellow-600',
            info: 'bg-blue-600'
        }[level] || 'bg-blue-600';
        
        alert.className += ` ${bgColor} text-white`;
        alert.textContent = message;
        
        document.body.appendChild(alert);
        
        setTimeout(() => {
            alert.remove();
        }, 5000);
    }
    
    // Load notifications from server
    async loadNotifications() {
        try {
            const response = await fetch('/api/notifications');
            const data = await response.json();
            
            if (data.success && data.notifications) {
                this.notifications = data.notifications;
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }
    
    // Start periodic updates
    startPeriodicUpdates() {
        // Update statistics every 30 seconds
        setInterval(async () => {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                if (data.success) {
                    this.updateStatistics(data.stats);
                }
            } catch (error) {
                console.error('Error updating stats:', error);
            }
        }, 30000);
        
        // Update recent scans every 10 seconds
        setInterval(async () => {
            try {
                const response = await fetch('/api/recent-scans');
                const data = await response.json();
                
                if (data.success) {
                    this.refreshRecentScans(data.scans);
                }
            } catch (error) {
                console.error('Error updating recent scans:', error);
            }
        }, 10000);
    }
    
    // Refresh recent scans display
    refreshRecentScans(scans) {
        const container = document.getElementById('recentScans');
        if (container && scans) {
            container.innerHTML = '';
            scans.slice(0, 10).forEach(scan => {
                const scanElement = this.createScanElement(scan);
                container.appendChild(scanElement);
            });
        }
    }
    
    // Utility functions
    formatDate(date) {
        return new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(date));
    }
    
    formatTime(time) {
        return new Intl.DateTimeFormat('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        }).format(new Date(time));
    }
    
    // Export data functionality
    async exportData(format, filters = {}) {
        try {
            const params = new URLSearchParams(filters);
            params.append('format', format);
            
            const response = await fetch(`/api/export?${params.toString()}`);
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `attendance_report_${new Date().toISOString().split('T')[0]}.${format}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showNotification('Export Complete', `Report exported as ${format.toUpperCase()}`, 'success');
            } else {
                throw new Error('Export failed');
            }
        } catch (error) {
            console.error('Export error:', error);
            this.showNotification('Export Failed', 'Unable to export data', 'error');
        }
    }
    
    // Search functionality
    setupSearch() {
        const searchInputs = document.querySelectorAll('[data-search]');
        
        searchInputs.forEach(input => {
            let searchTimeout;
            
            input.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.performSearch(e.target.value, e.target.dataset.search);
                }, 300);
            });
        });
    }
    
    async performSearch(query, type) {
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&type=${type}`);
            const data = await response.json();
            
            if (data.success) {
                this.displaySearchResults(data.results, type);
            }
        } catch (error) {
            console.error('Search error:', error);
        }
    }
    
    displaySearchResults(results, type) {
        const resultsContainer = document.getElementById(`${type}-results`);
        if (resultsContainer) {
            resultsContainer.innerHTML = '';
            
            results.forEach(result => {
                const resultElement = this.createSearchResultElement(result, type);
                resultsContainer.appendChild(resultElement);
            });
        }
    }
    
    createSearchResultElement(result, type) {
        const element = document.createElement('div');
        element.className = 'p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer';
        
        // Customize based on type
        if (type === 'students') {
            element.innerHTML = `
                <div class="flex items-center space-x-3">
                    <div class="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                        <i class="fas fa-user text-blue-600"></i>
                    </div>
                    <div>
                        <p class="font-semibold">${result.first_name} ${result.last_name}</p>
                        <p class="text-sm text-gray-600">${result.student_id} • ${result.department}</p>
                    </div>
                </div>
            `;
        } else if (type === 'rooms') {
            element.innerHTML = `
                <div class="flex items-center space-x-3">
                    <div class="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                        <i class="fas fa-door-open text-green-600"></i>
                    </div>
                    <div>
                        <p class="font-semibold">${result.room_name}</p>
                        <p class="text-sm text-gray-600">${result.building} • Capacity: ${result.capacity}</p>
                    </div>
                </div>
            `;
        }
        
        return element;
    }
}

// Initialize the system when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.qrAttendanceSystem = new QRAttendanceSystem();
});

// Additional utility functions
function showGlobalNotification(title, message, type = 'info') {
    if (window.qrAttendanceSystem) {
        window.qrAttendanceSystem.showNotification(title, message, type);
    }
}

function exportAttendanceData(format) {
    if (window.qrAttendanceSystem) {
        window.qrAttendanceSystem.exportData(format);
    }
}

// Service Worker registration for offline functionality
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => {
                console.log('ServiceWorker registered:', registration);
            })
            .catch(registrationError => {
                console.log('ServiceWorker registration failed:', registrationError);
            });
    });
}

// Handle online/offline status
window.addEventListener('online', () => {
    showGlobalNotification('Connection Restored', 'You are back online', 'success');
});

window.addEventListener('offline', () => {
    showGlobalNotification('Connection Lost', 'You are currently offline', 'warning');
});

// QR Code generation utilities
class QRCodeGenerator {
    constructor() {
        this.baseUrl = '/api/qr/generate';
    }
    
    async generateStudentQR(studentId) {
        try {
            const response = await fetch(this.baseUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    type: 'student',
                    student_id: studentId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                return data.qr_code_url;
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('QR generation error:', error);
            throw error;
        }
    }
    
    async generateBulkQR(studentIds) {
        try {
            const response = await fetch(`${this.baseUrl}/bulk`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    student_ids: studentIds
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                return data.download_url;
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('Bulk QR generation error:', error);
            throw error;
        }
    }
}

// Make QR generator available globally
window.qrGenerator = new QRCodeGenerator();

// Data validation utilities
class DataValidator {
    static validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    static validatePhone(phone) {
        const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
        return phoneRegex.test(phone.replace(/\s+/g, ''));
    }
    
    static validateStudentId(studentId) {
        return studentId && studentId.length >= 3 && studentId.length <= 20;
    }
    
    static validateRequired(value) {
        return value !== null && value !== undefined && value.toString().trim() !== '';
    }
}

// Make validator available globally
window.dataValidator = DataValidator;