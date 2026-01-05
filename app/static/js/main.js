/**
 * Sarva Gyaan Academy - Main JavaScript
 */

// Theme Management
const ThemeManager = {
    init() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        this.setTheme(savedTheme);
        this.bindEvents();
    },

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        this.updateToggleButton(theme);
    },

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    },

    updateToggleButton(theme) {
        const btn = document.getElementById('themeToggle');
        if (btn) {
            const icon = btn.querySelector('i');
            const text = btn.querySelector('span');
            if (theme === 'dark') {
                icon.className = 'bi bi-sun-fill';
                if (text) text.textContent = 'Light';
            } else {
                icon.className = 'bi bi-moon-fill';
                if (text) text.textContent = 'Dark';
            }
        }
    },

    bindEvents() {
        const btn = document.getElementById('themeToggle');
        if (btn) {
            btn.addEventListener('click', () => this.toggleTheme());
        }
    }
};

// Mobile Menu Management
const MobileMenuManager = {
    init() {
        this.moreMenu = document.getElementById('mobileMoreMenu');
        this.bindEvents();
    },

    toggle() {
        if (this.moreMenu) {
            this.moreMenu.classList.toggle('show');
        }
    },

    close() {
        if (this.moreMenu) {
            this.moreMenu.classList.remove('show');
        }
    },

    bindEvents() {
        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (this.moreMenu && this.moreMenu.classList.contains('show')) {
                const moreContainer = document.querySelector('.mobile-nav-more');
                if (moreContainer && !moreContainer.contains(e.target)) {
                    this.close();
                }
            }
        });
    }
};

// Global function for mobile menu toggle
function toggleMobileMenu() {
    MobileMenuManager.toggle();
}

// Flash Message Auto-dismiss
const FlashMessages = {
    init() {
        const alerts = document.querySelectorAll('.alert[data-auto-dismiss]');
        alerts.forEach(alert => {
            const timeout = parseInt(alert.dataset.autoDismiss) || 5000;
            setTimeout(() => {
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-10px)';
                setTimeout(() => alert.remove(), 300);
            }, timeout);
        });
    }
};

// Form Validation
const FormValidator = {
    init() {
        const forms = document.querySelectorAll('form[data-validate]');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => this.validate(e, form));
        });
    },

    validate(e, form) {
        let isValid = true;
        const required = form.querySelectorAll('[required]');

        required.forEach(field => {
            this.clearError(field);
            if (!field.value.trim()) {
                isValid = false;
                this.showError(field, 'This field is required');
            }
        });

        // Email validation
        const emails = form.querySelectorAll('input[type="email"]');
        emails.forEach(field => {
            if (field.value && !this.isValidEmail(field.value)) {
                isValid = false;
                this.showError(field, 'Please enter a valid email');
            }
        });

        // Phone validation
        const phones = form.querySelectorAll('input[data-validate-phone]');
        phones.forEach(field => {
            if (field.value && !this.isValidPhone(field.value)) {
                isValid = false;
                this.showError(field, 'Please enter a valid phone number');
            }
        });

        if (!isValid) {
            e.preventDefault();
        }
    },

    showError(field, message) {
        field.classList.add('is-invalid');
        const error = document.createElement('div');
        error.className = 'form-text text-danger';
        error.textContent = message;
        field.parentNode.appendChild(error);
    },

    clearError(field) {
        field.classList.remove('is-invalid');
        const error = field.parentNode.querySelector('.text-danger');
        if (error) error.remove();
    },

    isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    },

    isValidPhone(phone) {
        return /^[0-9]{10}$/.test(phone.replace(/\D/g, ''));
    }
};

// Student Search Autocomplete
const StudentSearch = {
    init() {
        const searchInputs = document.querySelectorAll('[data-student-search]');
        searchInputs.forEach(input => this.setupSearch(input));
    },

    setupSearch(input) {
        const resultsContainer = document.createElement('div');
        resultsContainer.className = 'search-results';
        resultsContainer.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            max-height: 300px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
        `;
        input.parentNode.style.position = 'relative';
        input.parentNode.appendChild(resultsContainer);

        let debounceTimer;
        input.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => this.search(input, resultsContainer), 300);
        });

        // Hide results on click outside
        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !resultsContainer.contains(e.target)) {
                resultsContainer.style.display = 'none';
            }
        });
    },

    async search(input, container) {
        const query = input.value.trim();
        if (query.length < 2) {
            container.style.display = 'none';
            return;
        }

        try {
            const response = await fetch(`/students/api/search?q=${encodeURIComponent(query)}`);
            const students = await response.json();

            if (students.length === 0) {
                container.innerHTML = '<div style="padding: 12px; color: var(--text-muted);">No students found</div>';
            } else {
                container.innerHTML = students.map(s => `
                    <div class="search-result-item" 
                         data-id="${s.id}" 
                         data-name="${s.name}"
                         style="padding: 12px; cursor: pointer; border-bottom: 1px solid var(--border-color);">
                        <strong>${s.name}</strong>
                        <br>
                        <small style="color: var(--text-muted);">${s.student_id} - ${s.batch}</small>
                    </div>
                `).join('');

                container.querySelectorAll('.search-result-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const hiddenInput = document.querySelector(input.dataset.studentSearch);
                        if (hiddenInput) {
                            hiddenInput.value = item.dataset.id;
                            // Trigger change event
                            hiddenInput.dispatchEvent(new Event('change'));
                        }
                        input.value = item.dataset.name;
                        container.style.display = 'none';
                    });

                    item.addEventListener('mouseenter', () => {
                        item.style.background = 'var(--bg-table-stripe)';
                    });
                    item.addEventListener('mouseleave', () => {
                        item.style.background = '';
                    });
                });
            }

            container.style.display = 'block';
        } catch (error) {
            console.error('Search error:', error);
        }
    }
};

// Confirmation Dialogs
const ConfirmDialog = {
    init() {
        document.querySelectorAll('[data-confirm]').forEach(el => {
            el.addEventListener('click', (e) => {
                const message = el.dataset.confirm || 'Are you sure?';
                if (!confirm(message)) {
                    e.preventDefault();
                }
            });
        });
    }
};

// Date Picker Enhancement
const DateHelper = {
    init() {
        // Set today's date as default for date inputs without value
        document.querySelectorAll('input[type="date"][data-default-today]').forEach(input => {
            if (!input.value) {
                input.value = new Date().toISOString().split('T')[0];
            }
        });
    }
};

// Print Functionality
const PrintHelper = {
    print(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            const printWindow = window.open('', '_blank');
            printWindow.document.write(`
                <html>
                <head>
                    <title>Print</title>
                    <link rel="stylesheet" href="/static/css/style.css">
                    <style>
                        body { padding: 20px; }
                        @media print {
                            body { padding: 0; }
                        }
                    </style>
                </head>
                <body>${element.innerHTML}</body>
                </html>
            `);
            printWindow.document.close();
            printWindow.onload = () => {
                printWindow.print();
                printWindow.close();
            };
        }
    }
};

// Attendance Marking Helper
const AttendanceHelper = {
    markAll(status) {
        document.querySelectorAll(`input[type="radio"][value="${status}"]`).forEach(radio => {
            radio.checked = true;
        });
    }
};

// Initialize all modules on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    ThemeManager.init();
    MobileMenuManager.init();
    FlashMessages.init();
    FormValidator.init();
    StudentSearch.init();
    ConfirmDialog.init();
    DateHelper.init();
});

// Export for global access
window.PrintHelper = PrintHelper;
window.AttendanceHelper = AttendanceHelper;
window.ThemeManager = ThemeManager;
