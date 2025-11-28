// Form Events Enhancement Script
document.addEventListener('DOMContentLoaded', function () {

    // File Upload Enhancement
    const fileInputs = document.querySelectorAll('.file-input');

    fileInputs.forEach(input => {
        const uploadArea = input.closest('.file-upload-area');
        const uploadText = uploadArea.querySelector('.file-upload-text p');
        const originalText = uploadText.textContent;

        // File selection handler
        input.addEventListener('change', function (e) {
            const files = e.target.files;
            if (files && files.length > 0) {
                const fileName = files[0].name;
                const fileSize = (files[0].size / 1024 / 1024).toFixed(2);
                uploadText.innerHTML = `📄 <strong>${fileName}</strong><br><small class="text-success">File selezionato (${fileSize} MB)</small>`;
                uploadArea.style.borderColor = 'var(--success-color)';
                uploadArea.style.backgroundColor = '#f0fff4';
            } else {
                uploadText.textContent = originalText;
                uploadArea.style.borderColor = '';
                uploadArea.style.backgroundColor = '';
            }
        });

        // Drag and drop handlers
        uploadArea.addEventListener('dragover', function (e) {
            e.preventDefault();
            uploadArea.style.borderColor = 'var(--primary-color)';
            uploadArea.style.backgroundColor = '#f0f8ff';
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', function (e) {
            e.preventDefault();
            if (!uploadArea.contains(e.relatedTarget)) {
                uploadArea.style.borderColor = '';
                uploadArea.style.backgroundColor = '';
                uploadArea.classList.remove('dragover');
            }
        });

        uploadArea.addEventListener('drop', function (e) {
            e.preventDefault();
            uploadArea.style.borderColor = '';
            uploadArea.style.backgroundColor = '';
            uploadArea.classList.remove('dragover');

            const files = e.dataTransfer.files;
            if (files && files.length > 0) {
                // Check file type
                const file = files[0];
                if (file.type.startsWith('image/')) {
                    input.files = files;
                    const event = new Event('change', { bubbles: true });
                    input.dispatchEvent(event);
                } else {
                    showNotification('⚠️ Seleziona un file immagine valido', 'warning');
                }
            }
        });
    });

    // Form validation enhancement
    const forms = document.querySelectorAll('.event-form');

    forms.forEach(form => {
        const inputs = form.querySelectorAll('.form-control[required]');

        inputs.forEach(input => {
            input.addEventListener('blur', validateField);
            input.addEventListener('input', clearFieldError);
        });

        form.addEventListener('submit', function (e) {
            let isValid = true;

            inputs.forEach(input => {
                if (!validateField.call(input)) {
                    isValid = false;
                }
            });

            if (!isValid) {
                e.preventDefault();
                showNotification('⚠️ Correggi i campi evidenziati in rosso', 'error');

                // Scroll to first error
                const firstError = form.querySelector('.form-control.error');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    firstError.focus();
                }
            }
        });
    });

    function validateField() {
        const value = this.value.trim();
        const fieldType = this.type;
        let isValid = true;

        // Remove previous error styling
        this.classList.remove('error');
        removeFieldError(this);

        // Required validation
        if (this.hasAttribute('required') && !value) {
            showFieldError(this, 'Questo campo è obbligatorio');
            isValid = false;
        }

        // Specific validations
        if (value && fieldType === 'email' && !isValidEmail(value)) {
            showFieldError(this, 'Inserisci un indirizzo email valido');
            isValid = false;
        }

        if (value && fieldType === 'number') {
            const num = parseFloat(value);
            const min = parseFloat(this.getAttribute('min') || 0);
            const max = parseFloat(this.getAttribute('max') || Infinity);

            if (isNaN(num) || num < min || num > max) {
                showFieldError(this, `Inserisci un numero tra ${min} e ${max}`);
                isValid = false;
            }
        }

        if (value && fieldType === 'date') {
            const selectedDate = new Date(value);
            const today = new Date();
            today.setHours(0, 0, 0, 0);

            if (selectedDate < today) {
                showFieldError(this, 'La data non può essere nel passato');
                isValid = false;
            }
        }

        return isValid;
    }

    function clearFieldError() {
        this.classList.remove('error');
        removeFieldError(this);
    }

    function showFieldError(input, message) {
        input.classList.add('error');

        let errorDiv = input.parentNode.querySelector('.field-error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'field-error';
            input.parentNode.appendChild(errorDiv);
        }

        errorDiv.textContent = message;
        errorDiv.style.cssText = `
            color: var(--secondary-color);
            font-size: 0.85em;
            margin-top: 4px;
            animation: fadeInUp 0.3s ease;
        `;

        input.style.borderColor = 'var(--secondary-color)';
        input.style.boxShadow = '0 0 0 3px rgba(229, 57, 53, 0.1)';
    }

    function removeFieldError(input) {
        const errorDiv = input.parentNode.querySelector('.field-error');
        if (errorDiv) {
            errorDiv.remove();
        }

        input.style.borderColor = '';
        input.style.boxShadow = '';
    }

    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    function showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span>${message}</span>
            <button class="notification-close">&times;</button>
        `;

        // Styles
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 9999;
            animation: slideInRight 0.3s ease;
            max-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;

        // Type-specific colors
        const colors = {
            success: '#4caf50',
            error: '#f44336',
            warning: '#ff9800',
            info: '#2196f3'
        };

        notification.style.backgroundColor = colors[type] || colors.info;

        // Add to page
        document.body.appendChild(notification);

        // Auto remove
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 4000);

        // Close button
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        });
    }

    // Add notification animations to CSS
    if (!document.querySelector('#notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOutRight {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
            .notification-close {
                background: none;
                border: none;
                color: white;
                font-size: 18px;
                margin-left: 10px;
                cursor: pointer;
                opacity: 0.8;
            }
            .notification-close:hover { opacity: 1; }
            .form-control.error {
                border-color: var(--secondary-color) !important;
                box-shadow: 0 0 0 3px rgba(229, 57, 53, 0.1) !important;
            }
        `;
        document.head.appendChild(style);
    }

    // Initialize preview for existing posters
    const existingPosters = document.querySelectorAll('.poster-preview-img');
    existingPosters.forEach(img => {
        img.addEventListener('click', function () {
            // Create lightbox overlay
            const overlay = document.createElement('div');
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
                cursor: pointer;
            `;

            const largeImg = document.createElement('img');
            largeImg.src = this.src;
            largeImg.style.cssText = `
                max-width: 90%;
                max-height: 90%;
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            `;

            overlay.appendChild(largeImg);
            document.body.appendChild(overlay);

            overlay.addEventListener('click', () => {
                document.body.removeChild(overlay);
            });
        });
    });
});