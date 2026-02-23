/* ============================================
   AUREVIA MEDICAL INSTITUTE - JAVASCRIPT
   ============================================ */

// Constants
const API_BASE_URL = '';

// DOM Elements
const navbar = document.getElementById('navbar');
const navMenu = document.getElementById('navMenu');
const hamburger = document.getElementById('hamburger');
const navLinks = document.querySelectorAll('.nav-link');
const feedbackForm = document.getElementById('feedbackForm');
const submitBtn = document.getElementById('submitBtn');
const loadingSpinner = document.getElementById('loadingSpinner');
const feedbackModal = document.getElementById('feedbackModal');
const modalClose = document.getElementById('modalClose');
const modalBtn = document.getElementById('modalBtn');
const feedbackMessage = document.getElementById('feedbackMessage');
const charCount = document.getElementById('charCount');

// ============================================
// STICKY NAVBAR
// ============================================

window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
        navbar.classList.add('sticky');
    } else {
        navbar.classList.remove('sticky');
    }
});

// ============================================
// MOBILE MENU
// ============================================

hamburger.addEventListener('click', () => {
    navMenu.classList.toggle('active');
    hamburger.classList.toggle('active');
});

navLinks.forEach(link => {
    link.addEventListener('click', () => {
        navMenu.classList.remove('active');
        hamburger.classList.remove('active');
    });
});

// ============================================
// CHARACTER COUNTER
// ============================================

feedbackMessage.addEventListener('input', (e) => {
    const maxLength = 500;
    const currentLength = e.target.value.length;
    charCount.textContent = Math.min(currentLength, maxLength);

    // Truncate if exceeds max length
    if (currentLength > maxLength) {
        e.target.value = e.target.value.substring(0, maxLength);
        charCount.textContent = maxLength;
    }
});

// ============================================
// FORM VALIDATION
// ============================================

const validateForm = () => {
    let isValid = true;

    // Clear previous errors
    clearAllErrors();

    // Validate Patient ID
    const patientId = document.getElementById('patientId').value.trim();
    if (!patientId) {
        showError('patientId', 'Patient ID is required');
        isValid = false;
    }

    // Validate Feedback Message
    const feedback = document.getElementById('feedbackMessage').value.trim();
    if (!feedback) {
        showError('feedbackMessage', 'Feedback is required');
        isValid = false;
    } else if (feedback.length < 10) {
        showError('feedbackMessage', 'Feedback must be at least 10 characters');
        isValid = false;
    }

    // Validate Rating
    const rating = document.querySelector('input[name="rating"]:checked');
    if (!rating) {
        showError('rating', 'Please select a rating');
        isValid = false;
    }

    return isValid;
};

const showError = (fieldName, message) => {
    const errorElement = document.getElementById(fieldName + 'Error');
    const inputElement = document.getElementById(fieldName);

    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.add('show');
    }

    if (inputElement && inputElement.type !== 'radio') {
        inputElement.classList.add('error');
    }
};

const clearAllErrors = () => {
    document.querySelectorAll('.error-message').forEach(el => {
        el.classList.remove('show');
        el.textContent = '';
    });

    document.querySelectorAll('.form-input, .form-textarea').forEach(el => {
        el.classList.remove('error');
    });
};

// Remove error on input
document.querySelectorAll('.form-input, .form-textarea').forEach(input => {
    input.addEventListener('input', function () {
        if (this.classList.contains('error')) {
            this.classList.remove('error');
            const errorId = this.id + 'Error';
            const errorEl = document.getElementById(errorId);
            if (errorEl) {
                errorEl.classList.remove('show');
            }
        }
    });
});

// Remove rating error on selection
document.querySelectorAll('input[name="rating"]').forEach(radio => {
    radio.addEventListener('change', function () {
        const errorEl = document.getElementById('ratingError');
        if (errorEl) {
            errorEl.classList.remove('show');
        }
    });
});

// ============================================
// FORM SUBMISSION
// ============================================

feedbackForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Validate form
    if (!validateForm()) {
        return;
    }

    try {
        // Show loading state
        submitBtn.disabled = true;
        loadingSpinner.classList.add('show');

        // Collect form data
        const patientId = document.getElementById('patientId').value.trim();
        const fullName = document.getElementById('fullName').value.trim();
        const email = document.getElementById('email').value.trim();
        const department = document.getElementById('department').value;
        const visitDate = document.getElementById('visitDate').value;
        const rating = document.querySelector('input[name="rating"]:checked').value;
        const feedbackText = document.getElementById('feedbackMessage').value.trim();

        // Prepare payload
        const payload = {
            patient_id: patientId,
            feedback_text: feedbackText,
            full_name: fullName || null,
            email: email || null,
            department: department || null,
            visit_date: visitDate || null,
            rating: parseInt(rating) || null
        };

        // Make API request
        const response = await fetch(`${API_BASE_URL}/api/submit-feedback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.statusText}`);
        }

        const data = await response.json();

        // Handle success
        if (data.status === 'success') {
            showSuccessModal(data.data);
            feedbackForm.reset();
            charCount.textContent = '0';
            clearAllErrors();
        } else {
            showErrorModal(data.message || 'Unable to process feedback. Please try again.');
        }

    } catch (error) {
        console.error('Submission Error:', error);
        showErrorModal('An error occurred. Please check your connection and try again.');
    } finally {
        // Hide loading state
        submitBtn.disabled = false;
        loadingSpinner.classList.remove('show');
    }
});

// ============================================
// MODAL HANDLERS
// ============================================

const showSuccessModal = (data) => {
    document.getElementById('modalIcon').textContent = '✓';
    document.getElementById('modalIcon').className = 'modal-icon success';
    document.getElementById('modalTitle').textContent = 'Thank You!';
    document.getElementById('modalMessage').textContent = 'Your feedback has been recorded successfully. We appreciate your valuable insights.';

    // Display response data
    document.getElementById('modalSentiment').textContent = data.sentiment || 'N/A';
    document.getElementById('modalIssueType').textContent = data.issue_type || 'N/A';
    document.getElementById('modalSeverity').textContent = data.severity || 'N/A';

    feedbackModal.classList.add('show');
};

const showErrorModal = (message) => {
    document.getElementById('modalIcon').textContent = '✕';
    document.getElementById('modalIcon').className = 'modal-icon error';
    document.getElementById('modalTitle').textContent = 'Error';
    document.getElementById('modalMessage').textContent = message;
    document.getElementById('modalSentiment').textContent = '-';
    document.getElementById('modalIssueType').textContent = '-';
    document.getElementById('modalSeverity').textContent = '-';

    feedbackModal.classList.add('show');
};

const closeModal = () => {
    feedbackModal.classList.remove('show');
};

// Modal close handlers
modalClose.addEventListener('click', closeModal);
modalBtn.addEventListener('click', closeModal);

// Close modal on outside click
feedbackModal.addEventListener('click', (e) => {
    if (e.target === feedbackModal) {
        closeModal();
    }
});

// ============================================
// SMOOTH SCROLL FOR ANCHOR LINKS
// ============================================

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href !== '#') {
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                const offsetTop = target.offsetTop - 80;
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        }
    });
});

// ============================================
// CTA BUTTON HANDLERS
// ============================================

const bookAppointmentBtn = document.querySelector('.hero .btn-primary');
const emergencyBtn = document.querySelector('.hero .btn-secondary');

if (bookAppointmentBtn) {
    bookAppointmentBtn.addEventListener('click', () => {
        const feedbackSection = document.getElementById('feedback');
        const offsetTop = feedbackSection.offsetTop - 80;
        window.scrollTo({
            top: offsetTop,
            behavior: 'smooth'
        });
    });
}

if (emergencyBtn) {
    emergencyBtn.addEventListener('click', () => {
        const contactSection = document.getElementById('contact');
        const offsetTop = contactSection.offsetTop - 80;
        window.scrollTo({
            top: offsetTop,
            behavior: 'smooth'
        });
    });
}

// ============================================
// INITIAL SETUP
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialize any required setup
    console.log('Aurevia Medical Institute Website Loaded');
});
