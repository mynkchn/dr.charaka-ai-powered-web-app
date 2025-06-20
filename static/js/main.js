// Utility Functions
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-${type} alert-dismissible fade show';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    document.querySelector('main').insertAdjacentElement('afterbegin', alertDiv);
    setTimeout(() => alertDiv.remove(), 5000);
}

// Form Validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;

    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });

    return isValid;
}

// Chat Interface
function scrollToBottom(element) {
    element.scrollTop = element.scrollHeight;
}

function formatDate(date) {
    return new Date(date).toLocaleString();
}

// Prediction Forms
function updatePredictionForm(type) {
    const form = document.getElementById('prediction-form');
    if (!form) return;

    // Clear existing fields
    form.innerHTML = '';

    // Add fields based on prediction type
    switch(type) {
        case 'symptoms':
            addSymptomFields(form);
            break;
        case 'breast-cancer':
            addBreastCancerFields(form);
            break;
        case 'diabetes':
            addDiabetesFields(form);
            break;
        case 'heart-disease':
            addHeartDiseaseFields(form);
            break;
        case 'liver-disease':
            addLiverDiseaseFields(form);
            break;
    }
}

// Initialize components when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize chat interface
    const chatContainer = document.querySelector('.chat-container');
    if (chatContainer) {
        scrollToBottom(chatContainer);
    }

    // Add form validation listeners
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            if (!validateForm(form.id)) {
                e.preventDefault();
                showAlert('Please fill in all required fields', 'danger');
            }
        });
    });
});