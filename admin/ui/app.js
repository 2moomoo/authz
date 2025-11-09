// Admin Dashboard JavaScript

const API_BASE = '/api';
let authToken = localStorage.getItem('admin_token');
let usageChart = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    if (authToken) {
        showDashboard();
    } else {
        showLogin();
    }

    // Login form
    document.getElementById('login-form').addEventListener('submit', handleLogin);

    // Create key form
    document.getElementById('create-key-form').addEventListener('submit', handleCreateKey);
});

function showLogin() {
    document.getElementById('login-page').classList.remove('hidden');
    document.getElementById('dashboard-page').classList.add('hidden');
}

function showDashboard() {
    document.getElementById('login-page').classList.add('hidden');
    document.getElementById('dashboard-page').classList.remove('hidden');
    loadDashboard();
}

async function handleLogin(e) {
    e.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });

        if (!response.ok) {
            throw new Error('Invalid credentials');
        }

        const data = await response.json();
        authToken = data.access_token;
        localStorage.setItem('admin_token', authToken);
        localStorage.setItem('admin_username', username);

        showDashboard();
    } catch (error) {
        const errorEl = document.getElementById('login-error');
        errorEl.textContent = error.message;
        errorEl.classList.remove('hidden');
    }
}

function logout() {
    authToken = null;
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_username');
    showLogin();
}

async function loadDashboard() {
    const username = localStorage.getItem('admin_username');
    document.getElementById('admin-username').textContent = username;

    await Promise.all([
        loadAPIKeys(),
        loadUsageStats(),
    ]);
}

async function loadAPIKeys() {
    try {
        const response = await fetch(`${API_BASE}/keys`, {
            headers: {
                'Authorization': `Bearer ${authToken}`,
            },
        });

        if (!response.ok) {
            if (response.status === 401) {
                logout();
                return;
            }
            throw new Error('Failed to load API keys');
        }

        const keys = await response.json();

        // Update stats
        document.getElementById('stat-total-keys').textContent = keys.length;
        document.getElementById('stat-active-keys').textContent = keys.filter(k => k.is_active).length;

        // Populate table
        const tbody = document.getElementById('keys-table-body');
        tbody.innerHTML = keys.map(key => `
            <tr>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${key.user_id}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-500">
                    <span class="cursor-pointer hover:text-gray-700" onclick="copyToClipboard('${key.key}')" title="Click to copy">
                        ${key.key.substring(0, 20)}...
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getTierColor(key.tier)}">
                        ${key.tier}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${key.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                        ${key.is_active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${new Date(key.created_at).toLocaleDateString()}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                    <button onclick="toggleKeyStatus(${key.id}, ${!key.is_active})" class="text-blue-600 hover:text-blue-800">
                        ${key.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button onclick="deleteKey(${key.id})" class="text-red-600 hover:text-red-800">
                        Delete
                    </button>
                </td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error loading API keys:', error);
    }
}

async function loadUsageStats() {
    try {
        const response = await fetch(`${API_BASE}/usage?days=7`, {
            headers: {
                'Authorization': `Bearer ${authToken}`,
            },
        });

        if (!response.ok) throw new Error('Failed to load usage stats');

        const stats = await response.json();

        // Update stats cards
        const totalRequests = stats.reduce((sum, s) => sum + s.requests, 0);
        const totalTokens = stats.reduce((sum, s) => sum + s.total_tokens, 0);

        document.getElementById('stat-requests').textContent = totalRequests.toLocaleString();
        document.getElementById('stat-tokens').textContent = totalTokens.toLocaleString();

        // Draw chart
        drawUsageChart(stats);

    } catch (error) {
        console.error('Error loading usage stats:', error);
    }
}

function drawUsageChart(stats) {
    const ctx = document.getElementById('usage-chart');

    if (usageChart) {
        usageChart.destroy();
    }

    usageChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: stats.map(s => s.date),
            datasets: [
                {
                    label: 'Requests',
                    data: stats.map(s => s.requests),
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    yAxisID: 'y',
                },
                {
                    label: 'Tokens',
                    data: stats.map(s => s.total_tokens),
                    borderColor: 'rgb(16, 185, 129)',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    yAxisID: 'y1',
                }
            ]
        },
        options: {
            responsive: true,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Requests'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Tokens'
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                },
            }
        },
    });
}

function showCreateKeyModal() {
    document.getElementById('create-key-modal').classList.remove('hidden');
    document.getElementById('create-key-modal').classList.add('flex');
}

function hideCreateKeyModal() {
    document.getElementById('create-key-modal').classList.add('hidden');
    document.getElementById('create-key-modal').classList.remove('flex');
    document.getElementById('create-key-form').reset();
}

async function handleCreateKey(e) {
    e.preventDefault();

    const userId = document.getElementById('new-user-id').value;
    const tier = document.getElementById('new-tier').value;
    const description = document.getElementById('new-description').value;
    const expiresInDays = document.getElementById('new-expires').value;

    const payload = {
        user_id: userId,
        tier: tier,
        description: description || null,
        expires_in_days: expiresInDays ? parseInt(expiresInDays) : null,
    };

    try {
        const response = await fetch(`${API_BASE}/keys`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) throw new Error('Failed to create API key');

        const newKey = await response.json();

        alert(`API Key created successfully!\n\nKey: ${newKey.key}\n\nPlease save this key, it won't be shown again.`);

        hideCreateKeyModal();
        loadAPIKeys();

    } catch (error) {
        alert('Error creating API key: ' + error.message);
    }
}

async function toggleKeyStatus(keyId, isActive) {
    try {
        const response = await fetch(`${API_BASE}/keys/${keyId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ is_active: isActive }),
        });

        if (!response.ok) throw new Error('Failed to update API key');

        loadAPIKeys();

    } catch (error) {
        alert('Error updating API key: ' + error.message);
    }
}

async function deleteKey(keyId) {
    if (!confirm('Are you sure you want to delete this API key?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/keys/${keyId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${authToken}`,
            },
        });

        if (!response.ok) throw new Error('Failed to delete API key');

        loadAPIKeys();

    } catch (error) {
        alert('Error deleting API key: ' + error.message);
    }
}

function getTierColor(tier) {
    switch(tier) {
        case 'premium': return 'bg-purple-100 text-purple-800';
        case 'standard': return 'bg-blue-100 text-blue-800';
        case 'free': return 'bg-gray-100 text-gray-800';
        default: return 'bg-gray-100 text-gray-800';
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('API key copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}
