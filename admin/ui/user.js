// User Self-Service Portal JavaScript

const API_BASE = '/auth';
let userEmail = '';
let apiKey = '';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('email-form').addEventListener('submit', handleEmailSubmit);
    document.getElementById('verify-form').addEventListener('submit', handleVerifySubmit);

    // Auto-focus on code input when it becomes visible
    const observer = new MutationObserver((mutations) => {
        const step2 = document.getElementById('step-2');
        if (!step2.classList.contains('hidden')) {
            document.getElementById('code').focus();
        }
    });

    observer.observe(document.getElementById('step-2'), {
        attributes: true,
        attributeFilter: ['class']
    });
});

async function handleEmailSubmit(e) {
    e.preventDefault();

    const email = document.getElementById('email').value.trim();
    const errorEl = document.getElementById('email-error');
    const successEl = document.getElementById('email-success');
    const submitBtn = e.target.querySelector('button[type="submit"]');

    // Clear previous messages
    errorEl.classList.add('hidden');
    successEl.classList.add('hidden');

    // Disable button
    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending...';

    try {
        const response = await fetch(`${API_BASE}/request-code`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to send verification code');
        }

        const data = await response.json();

        // Show success message
        successEl.textContent = `✅ ${data.message}`;
        successEl.classList.remove('hidden');

        // Save email
        userEmail = email;

        // Move to step 2 after a short delay
        setTimeout(() => {
            showStep2();
        }, 1000);

    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Send Verification Code';
    }
}

async function handleVerifySubmit(e) {
    e.preventDefault();

    const code = document.getElementById('code').value.trim();
    const errorEl = document.getElementById('verify-error');
    const submitBtn = e.target.querySelector('button[type="submit"]');

    // Clear previous error
    errorEl.classList.add('hidden');

    // Validate code format
    if (code.length !== 6 || !/^\d+$/.test(code)) {
        errorEl.textContent = 'Please enter a valid 6-digit code';
        errorEl.classList.remove('hidden');
        return;
    }

    // Disable button
    submitBtn.disabled = true;
    submitBtn.textContent = 'Verifying...';

    try {
        const response = await fetch(`${API_BASE}/verify-code`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: userEmail,
                code: code,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Verification failed');
        }

        const data = await response.json();

        // Save API key
        apiKey = data.api_key;

        // Show success step
        showStep3(data.message);

    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Verify & Get API Key';
    }
}

function showStep2() {
    document.getElementById('step-1').classList.add('hidden');
    document.getElementById('step-2').classList.remove('hidden');
    document.getElementById('step-3').classList.add('hidden');

    // Display email
    document.getElementById('user-email').textContent = userEmail;

    // Clear code input
    document.getElementById('code').value = '';
    document.getElementById('code').focus();
}

function showStep3(message) {
    document.getElementById('step-1').classList.add('hidden');
    document.getElementById('step-2').classList.add('hidden');
    document.getElementById('step-3').classList.remove('hidden');

    // Display message and API key
    document.getElementById('success-message').textContent = message;
    document.getElementById('api-key-display').value = apiKey;
}

function goBackToStep1() {
    document.getElementById('step-1').classList.remove('hidden');
    document.getElementById('step-2').classList.add('hidden');
    document.getElementById('step-3').classList.add('hidden');

    // Clear inputs
    document.getElementById('code').value = '';

    // Focus email input
    document.getElementById('email').focus();
}

function startOver() {
    userEmail = '';
    apiKey = '';

    document.getElementById('step-1').classList.remove('hidden');
    document.getElementById('step-2').classList.add('hidden');
    document.getElementById('step-3').classList.add('hidden');

    // Clear all inputs
    document.getElementById('email').value = '';
    document.getElementById('code').value = '';

    // Clear messages
    document.getElementById('email-error').classList.add('hidden');
    document.getElementById('email-success').classList.add('hidden');
    document.getElementById('verify-error').classList.add('hidden');

    // Focus email input
    document.getElementById('email').focus();
}

function copyAPIKey() {
    const apiKeyInput = document.getElementById('api-key-display');
    apiKeyInput.select();
    apiKeyInput.setSelectionRange(0, 99999); // For mobile devices

    navigator.clipboard.writeText(apiKeyInput.value).then(() => {
        // Show feedback
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = '✅ Copied!';
        btn.classList.add('bg-green-600');
        btn.classList.remove('bg-blue-600');

        setTimeout(() => {
            btn.textContent = originalText;
            btn.classList.remove('bg-green-600');
            btn.classList.add('bg-blue-600');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy to clipboard. Please copy manually.');
    });
}
