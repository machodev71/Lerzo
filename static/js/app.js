// Student Management System - Main JavaScript File

// Dark Mode Toggle
function toggleDarkMode() {
    try {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-bs-theme', newTheme);
        
        // Update icon - with null check
        const icon = document.getElementById('darkModeIcon');
        if (icon && icon.classList) {
            icon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
        
        // Save preference
        localStorage.setItem('theme', newTheme);
    } catch (error) {
        console.log('Dark mode toggle error:', error);
    }
}

// Initialize Dark Mode
function initializeDarkMode() {
    try {
        const savedTheme = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = savedTheme || (prefersDark ? 'dark' : 'light');
        
        document.documentElement.setAttribute('data-bs-theme', theme);
        
        // Update icon - with null check
        const icon = document.getElementById('darkModeIcon');
        if (icon && icon.classList) {
            icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    } catch (error) {
        console.log('Dark mode initialization error:', error);
        // Set default theme if there's an error
        document.documentElement.setAttribute('data-bs-theme', 'light');
    }
}

// Auto-uppercase input fields
function initializeUppercaseInputs() {
    const uppercaseInputs = document.querySelectorAll('.uppercase-input');
    uppercaseInputs.forEach(input => {
        input.addEventListener('input', function() {
            this.value = this.value.toUpperCase();
        });
    });
}

// Form Validation Enhancements
function initializeFormValidation() {
    // Add bootstrap validation classes
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Real-time validation for required fields
    const requiredFields = document.querySelectorAll('input[required], select[required], textarea[required]');
    requiredFields.forEach(field => {
        field.addEventListener('blur', function() {
            if (this.value.trim() === '') {
                this.classList.add('is-invalid');
                this.classList.remove('is-valid');
            } else {
                this.classList.add('is-valid');
                this.classList.remove('is-invalid');
            }
        });
        
        field.addEventListener('input', function() {
            if (this.classList.contains('is-invalid') && this.value.trim() !== '') {
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            }
        });
    });
}

// Number Input Formatting
function initializeNumberFormatting() {
    const numberInputs = document.querySelectorAll('input[type="number"], .currency-input');
    numberInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value && !isNaN(this.value)) {
                if (this.classList.contains('currency-input') || this.step === '0.01') {
                    this.value = parseFloat(this.value).toFixed(2);
                }
            }
        });
    });
}

// Mobile Number Validation
function initializeMobileValidation() {
    const mobileInputs = document.querySelectorAll('input[name*="mobile"]');
    mobileInputs.forEach(input => {
        input.addEventListener('input', function() {
            // Remove non-numeric characters
            this.value = this.value.replace(/\D/g, '');
            
            // Limit to 10 digits
            if (this.value.length > 10) {
                this.value = this.value.slice(0, 10);
            }
            
            // Validate mobile number format
            if (this.value.length === 10 && /^[6-9]\d{9}$/.test(this.value)) {
                this.classList.add('is-valid');
                this.classList.remove('is-invalid');
            } else if (this.value.length > 0) {
                this.classList.add('is-invalid');
                this.classList.remove('is-valid');
            }
        });
    });
}

// Fee Calculation Functions
function calculateNetFees(totalFeesId, concessionId, netFeesId) {
    const totalFeesInput = document.getElementById(totalFeesId);
    const concessionInput = document.getElementById(concessionId);
    const netFeesInput = document.getElementById(netFeesId);
    
    if (!totalFeesInput || !concessionInput || !netFeesInput) return;
    
    function calculate() {
        const totalFees = parseFloat(totalFeesInput.value) || 0;
        const concession = parseFloat(concessionInput.value) || 0;
        const netFees = Math.max(0, totalFees - concession);
        netFeesInput.value = netFees.toFixed(2);
    }
    
    totalFeesInput.addEventListener('input', calculate);
    concessionInput.addEventListener('input', calculate);
    
    // Calculate on page load
    calculate();
}

// Auto-save Draft Functionality
function initializeAutoSave() {
    const forms = document.querySelectorAll('form[data-autosave]');
    forms.forEach(form => {
        const formId = form.id || 'form_' + Date.now();
        const inputs = form.querySelectorAll('input, select, textarea');
        
        // Load saved data
        loadFormData(formId, inputs);
        
        // Save on input change
        inputs.forEach(input => {
            input.addEventListener('input', () => {
                saveFormData(formId, inputs);
            });
        });
        
        // Clear saved data on successful submit
        form.addEventListener('submit', () => {
            clearFormData(formId);
        });
    });
}

function saveFormData(formId, inputs) {
    const data = {};
    inputs.forEach(input => {
        if (input.type === 'checkbox') {
            data[input.name] = input.checked;
        } else if (input.type === 'radio') {
            if (input.checked) {
                data[input.name] = input.value;
            }
        } else {
            data[input.name] = input.value;
        }
    });
    localStorage.setItem(`form_draft_${formId}`, JSON.stringify(data));
}

function loadFormData(formId, inputs) {
    const savedData = localStorage.getItem(`form_draft_${formId}`);
    if (savedData) {
        try {
            const data = JSON.parse(savedData);
            inputs.forEach(input => {
                if (data.hasOwnProperty(input.name)) {
                    if (input.type === 'checkbox') {
                        input.checked = data[input.name];
                    } else if (input.type === 'radio') {
                        input.checked = input.value === data[input.name];
                    } else {
                        input.value = data[input.name];
                    }
                }
            });
        } catch (e) {
            console.log('Error loading saved form data:', e);
        }
    }
}

function clearFormData(formId) {
    localStorage.removeItem(`form_draft_${formId}`);
}

// Search Functionality Enhancement
function initializeSearchEnhancements() {
    const searchInputs = document.querySelectorAll('input[name="search"]');
    searchInputs.forEach(input => {
        let searchTimeout;
        
        input.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                if (this.value.length >= 3 || this.value.length === 0) {
                    this.form.submit();
                }
            }, 500); // Debounce search
        });
    });
}

// Notification System
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Loading States
function showLoading(element, text = 'Loading...') {
    const originalContent = element.innerHTML;
    element.innerHTML = `
        <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
        ${text}
    `;
    element.disabled = true;
    
    return function hideLoading() {
        element.innerHTML = originalContent;
        element.disabled = false;
    };
}

// Confirm Dialogs Enhancement
function initializeConfirmDialogs() {
    const confirmButtons = document.querySelectorAll('[onclick*="confirm"]');
    confirmButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const confirmText = this.getAttribute('data-confirm') || 'Are you sure?';
            if (!confirm(confirmText)) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }
        });
    });
}

// Table Enhancements
function initializeTableEnhancements() {
    // Add row highlighting
    const tables = document.querySelectorAll('.table-hover tbody tr');
    tables.forEach(row => {
        row.addEventListener('click', function() {
            // Remove previous selection
            this.parentNode.querySelectorAll('.table-active').forEach(r => {
                r.classList.remove('table-active');
            });
            
            // Add selection to current row
            this.classList.add('table-active');
        });
    });
    
    // Add sorting indicators
    const sortableHeaders = document.querySelectorAll('th[data-sortable]');
    sortableHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.innerHTML += ' <i class="fas fa-sort text-muted"></i>';
    });
}

// Keyboard Shortcuts
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + S to save form
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            const submitButton = document.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.click();
            }
        }
        
        // Ctrl/Cmd + D to toggle dark mode
        if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
            e.preventDefault();
            toggleDarkMode();
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            });
        }
    });
}

// Print Functionality
function printPage() {
    window.print();
}

function printElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
                <head>
                    <title>Print</title>
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
                    <style>
                        body { margin: 20px; }
                        .no-print { display: none !important; }
                    </style>
                </head>
                <body>
                    ${element.innerHTML}
                </body>
            </html>
        `);
        printWindow.document.close();
        printWindow.print();
    }
}

// Initialize all functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    try {
        initializeDarkMode();
        initializeUppercaseInputs();
        initializeFormValidation();
        initializeNumberFormatting();
        initializeMobileValidation();
        initializeAutoSave();
        initializeSearchEnhancements();
        initializeConfirmDialogs();
        initializeTableEnhancements();
        initializeKeyboardShortcuts();
        
        // Initialize tooltips - with null check
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        if (tooltipTriggerList.length > 0 && typeof bootstrap !== 'undefined') {
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
        
        // Initialize popovers - with null check
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        if (popoverTriggerList.length > 0 && typeof bootstrap !== 'undefined') {
            popoverTriggerList.map(function (popoverTriggerEl) {
                return new bootstrap.Popover(popoverTriggerEl);
            });
        }
        
        console.log('Student Management System initialized successfully');
    } catch (error) {
        console.error('Initialization error:', error);
        // Don't show notification for initialization errors
    }
});

// Error Handling
window.addEventListener('error', function(e) {
    console.error('JavaScript Error:', e.error);
    
    // Don't show notifications for common initialization errors
    const errorMessage = e.error ? e.error.message : '';
    const isInitializationError = errorMessage.includes('Cannot read properties of null') ||
                                 errorMessage.includes('Cannot read property') ||
                                 errorMessage.includes('is not defined') ||
                                 errorMessage.includes('classList');
    
    // Only show notification for unexpected errors, not initialization issues
    if (!isInitializationError) {
        showNotification('An error occurred. Please refresh the page.', 'danger');
    }
});

// Export functions for global use
window.SMS = {
    toggleDarkMode,
    showNotification,
    showLoading,
    printPage,
    printElement,
    calculateNetFees
};