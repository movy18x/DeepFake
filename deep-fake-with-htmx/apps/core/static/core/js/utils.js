
/* core/static/core/js/utils.js */
class DeepfakeUtils {
    static showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 1060; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    static formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    static validateFile(file, maxSize = 50 * 1024 * 1024) { // 50MB default
        const allowedTypes = [
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
            'video/mp4', 'video/avi', 'video/mov', 'video/wmv'
        ];

        if (!allowedTypes.includes(file.type)) {
            throw new Error('File type not supported. Please upload an image or video file.');
        }

        if (file.size > maxSize) {
            throw new Error(`File size exceeds limit. Maximum size is ${this.formatFileSize(maxSize)}.`);
        }

        return true;
    }

    static createProgressBar(container, fileName) {
        const progressHTML = `
            <div class="progress-container mb-3">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <small class="text-muted">${fileName}</small>
                    <small class="text-muted progress-text">0%</small>
                </div>
                <div class="progress">
                    <div class="progress-bar progress-bar-striped progress-bar-animated"
                         role="progressbar" style="width: 0%"></div>
                </div>
            </div>
        `;

        container.innerHTML = progressHTML;
        return container.querySelector('.progress-bar');
    }

    static updateProgress(progressBar, percent) {
        progressBar.style.width = `${percent}%`;
        progressBar.parentElement.parentElement
            .querySelector('.progress-text').textContent = `${Math.round(percent)}%`;
    }

    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    static copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showNotification('Copied to clipboard!', 'success');
        }).catch(() => {
            this.showNotification('Failed to copy to clipboard', 'error');
        });
    }

    static downloadFile(url, filename) {
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// File upload handling with drag and drop
class FileUploadHandler {
    constructor(element, options = {}) {
        this.element = element;
        this.options = {
            maxFiles: 1,
            maxSize: 50 * 1024 * 1024, // 50MB
            allowedTypes: [
                'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
                'video/mp4', 'video/avi', 'video/mov', 'video/wmv'
            ],
            ...options
        };

        this.files = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.createFileInput();
    }

    setupEventListeners() {
        // Drag and drop
        this.element.addEventListener('dragover', this.handleDragOver.bind(this));
        this.element.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.element.addEventListener('drop', this.handleDrop.bind(this));

        // Click to upload
        this.element.addEventListener('click', () => {
            this.fileInput.click();
        });
    }

    createFileInput() {
        this.fileInput = document.createElement('input');
        this.fileInput.type = 'file';
        this.fileInput.multiple = this.options.maxFiles > 1;
        this.fileInput.accept = this.options.allowedTypes.join(',');
        this.fileInput.style.display = 'none';
        this.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        this.element.appendChild(this.fileInput);
    }

    handleDragOver(e) {
        e.preventDefault();
        this.element.classList.add('dragover');
    }

    handleDragLeave(e) {
        e.preventDefault();
        this.element.classList.remove('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        this.element.classList.remove('dragover');

        const files = Array.from(e.dataTransfer.files);
        this.processFiles(files);
    }

    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.processFiles(files);
    }

    processFiles(files) {
        try {
            // Validate number of files
            if (files.length > this.options.maxFiles) {
                throw new Error(`Maximum ${this.options.maxFiles} file(s) allowed`);
            }

            // Validate each file
            files.forEach(file => {
                DeepfakeUtils.validateFile(file, this.options.maxSize);
            });

            this.files = files;
            this.onFilesSelected(files);

        } catch (error) {
            DeepfakeUtils.showNotification(error.message, 'danger');
        }
    }

    onFilesSelected(files) {
        // Override this method to handle selected files
        console.log('Files selected:', files);
    }
}

// HTMX event handlers
document.addEventListener('htmx:configRequest', (evt) => {
    // Add CSRF token to all HTMX requests
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (csrfToken) {
        evt.detail.headers['X-CSRFToken'] = csrfToken;
    }
});

document.addEventListener('htmx:beforeRequest', (evt) => {
    // Show loading indicator
    const target = document.querySelector(evt.detail.target);
    if (target) {
        target.innerHTML = `
            <div class="text-center py-3">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
    }
});

document.addEventListener('htmx:responseError', (evt) => {
    DeepfakeUtils.showNotification('An error occurred. Please try again.', 'danger');
});

document.addEventListener('htmx:afterRequest', (evt) => {
    // Handle response messages
    const response = evt.detail.xhr.response;
    if (response && typeof response === 'string') {
        try {
            const data = JSON.parse(response);
            if (data.message) {
                DeepfakeUtils.showNotification(data.message, data.type || 'info');
            }
        } catch (e) {
            // Response is not JSON, ignore
        }
    }
});

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize file upload areas
    document.querySelectorAll('.upload-area').forEach(element => {
        new FileUploadHandler(element);
    });
});

// core/static/core/js/dashboard.js
class DashboardManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupRealtimeUpdates();
        this.setupSystemHealth();
    }

    setupRealtimeUpdates() {
        // Update dashboard stats every 30 seconds
        setInterval(() => {
            this.updateStats();
        }, 30000);
    }

    updateStats() {
        fetch('/api/dashboard/stats/')
            .then(response => response.json())
            .then(data => {
                this.updateStatsCards(data);
            })
            .catch(error => {
                console.error('Failed to update stats:', error);
            });
    }

    updateStatsCards(data) {
        const cards = document.querySelectorAll('.stats-card');
        cards.forEach(card => {
            const metric = card.dataset.metric;
            if (data[metric] !== undefined) {
                const valueElement = card.querySelector('.stat-value');
                if (valueElement) {
                    this.animateValue(valueElement, parseInt(valueElement.textContent), data[metric]);
                }
            }
        });
    }

    animateValue(element, start, end, duration = 1000) {
        const startTime = performance.now();
        const difference = end - start;

        const updateValue = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            const currentValue = Math.floor(start + (difference * progress));
            element.textContent = currentValue.toLocaleString();

            if (progress < 1) {
                requestAnimationFrame(updateValue);
            }
        };

        requestAnimationFrame(updateValue);
    }

    setupSystemHealth() {
        this.checkSystemHealth();

        // Check system health every 2 minutes
        setInterval(() => {
            this.checkSystemHealth();
        }, 120000);
    }

    checkSystemHealth() {
        fetch('/core/health/')
            .then(response => response.json())
            .then(data => {
                this.updateSystemStatus(data.status === 'healthy');
            })
            .catch(() => {
                this.updateSystemStatus(false);
            });
    }

    updateSystemStatus(isHealthy) {
        const statusElement = document.getElementById('system-status');
        if (statusElement) {
            statusElement.className = `alert ${isHealthy ? 'alert-success' : 'alert-warning'}`;
            statusElement.innerHTML = `
                <i class="fas ${isHealthy ? 'fa-check-circle' : 'fa-exclamation-triangle'} me-2"></i>
                ${isHealthy ? 'All systems operational' : 'System issues detected'}
            `;
        }
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('main-dashboard-content')) {
        new DashboardManager();
    }
});

// Export utilities for use in other modules
window.DeepfakeUtils = DeepfakeUtils;
window.FileUploadHandler = FileUploadHandler;