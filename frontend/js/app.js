// GetRank.fun - Frontend Application
const API_BASE = 'http://localhost:5002/api';

// State
let currentUser = null;
let currentCategory = 'all';

// DOM Elements
const elements = {
    leaderboardGrid: document.getElementById('leaderboardGrid'),
    categoryFilters: document.getElementById('categoryFilters'),
    statLeaderboards: document.getElementById('statLeaderboards'),
    statEntries: document.getElementById('statEntries'),
    statVotes: document.getElementById('statVotes'),
    loginBtn: document.getElementById('loginBtn'),
    registerBtn: document.getElementById('registerBtn'),
    loginModal: document.getElementById('loginModal'),
    registerModal: document.getElementById('registerModal'),
    leaderboardModal: document.getElementById('leaderboardModal'),
    leaderboardDetail: document.getElementById('leaderboardDetail'),
    createLeaderboardForm: document.getElementById('createLeaderboardForm'),
    loginForm: document.getElementById('loginForm'),
    registerForm: document.getElementById('registerForm')
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    loadLeaderboards();
    setupEventListeners();
});

// API Functions
async function apiCall(endpoint, options = {}) {
    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    };
    
    if (localStorage.getItem('token')) {
        config.headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
    }
    
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, config);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'API Error');
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Load Leaderboards
async function loadLeaderboards() {
    try {
        const params = currentCategory !== 'all' ? `?category=${currentCategory}` : '';
        const data = await apiCall(`/leaderboards${params}`);
        
        renderLeaderboards(data.leaderboards || []);
        updateStats(data.stats || {});
    } catch (error) {
        console.error('Failed to load leaderboards:', error);
        elements.leaderboardGrid.innerHTML = '<div class="loading">Failed to load leaderboards. Is the backend running on port 5002?</div>';
    }
}

// Render Leaderboards
function renderLeaderboards(leaderboards) {
    if (leaderboards.length === 0) {
        elements.leaderboardGrid.innerHTML = '<div class="loading">No leaderboards found. Create one!</div>';
        return;
    }
    
    elements.leaderboardGrid.innerHTML = leaderboards.map(board => `
        <div class="leaderboard-card" onclick="viewLeaderboard('${board.id}')">
            <div class="leaderboard-card-header">
                <h3>${board.name}</h3>
                <span class="leaderboard-category">${board.category}</span>
            </div>
            <p>${board.description || 'No description'}</p>
            <div class="leaderboard-stats">
                <span>📊 ${board.entry_count || 0} entries</span>
                <span>🗳️ ${board.vote_count || 0} votes</span>
            </div>
        </div>
    `).join('');
}

// Update Stats
function updateStats(stats) {
    if (elements.statLeaderboards) {
        elements.statLeaderboards.textContent = stats.leaderboards || 0;
    }
    if (elements.statEntries) {
        elements.statEntries.textContent = stats.entries || 0;
    }
    if (elements.statVotes) {
        elements.statVotes.textContent = stats.votes || 0;
    }
}

// View Leaderboard Detail
window.viewLeaderboard = async function(id) {
    try {
        const data = await apiCall(`/leaderboards/${id}`);
        renderLeaderboardDetail(data);
        elements.leaderboardModal.classList.add('active');
    } catch (error) {
        console.error('Failed to load leaderboard:', error);
    }
};

// Render Leaderboard Detail
function renderLeaderboardDetail(data) {
    const entries = data.entries || [];
    
    elements.leaderboardDetail.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
            <div>
                <h2>${data.name}</h2>
                <p style="color: var(--gray);">${data.description || ''}</p>
                <span class="leaderboard-category">${data.category}</span>
            </div>
        </div>
        
        ${entries.length === 0 ? '<p>No entries yet. Be the first to submit!</p>' : `
        <div class="entries-list">
            ${entries.map((entry, index) => `
                <div class="entry-card" style="background: var(--light); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4>#${index + 1} ${entry.title}</h4>
                            <p style="color: var(--gray);">${entry.submitter} - ${entry.description || ''}</p>
                        </div>
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <button onclick="voteEntry('${entry.id}', 1)" style="background: var(--secondary); color: white; border: none; padding: 0.5rem; border-radius: 8px; cursor: pointer;">▲</button>
                            <span>${entry.score || 0}</span>
                            <button onclick="voteEntry('${entry.id}', -1)" style="background: #e74c3c; color: white; border: none; padding: 0.5rem; border-radius: 8px; cursor: pointer;">▼</button>
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
        
        <div style="margin-top: 2rem; padding-top: 2rem; border-top: 1px solid #e0e0e0;">
            <h3>Submit Entry</h3>
            <form id="entryForm" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem;">
                <div>
                    <label>Title</label>
                    <input type="text" id="entryTitle" required style="width: 100%; padding: 0.5rem; border: 2px solid #e0e0e0; border-radius: 8px;">
                </div>
                <div>
                    <label>Submitter</label>
                    <input type="text" id="entrySubmitter" required style="width: 100%; padding: 0.5rem; border: 2px solid #e0e0e0; border-radius: 8px;">
                </div>
                <div style="grid-column: 1 / -1;">
                    <label>Description</label>
                    <textarea id="entryDescription" rows="3" style="width: 100%; padding: 0.5rem; border: 2px solid #e0e0e0; border-radius: 8px;"></textarea>
                </div>
                <div style="grid-column: 1 / -1;">
                    <button type="submit" class="btn btn-primary">Submit Entry</button>
                </div>
            </form>
        </div>
        `}`;
    
    // Setup entry form
    const entryForm = document.getElementById('entryForm');
    if (entryForm) {
        entryForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await submitEntry(data.id);
        });
    }
}

// Vote Entry
window.voteEntry = async function(entryId, direction) {
    try {
        await apiCall(`/entries/${entryId}/vote`, {
            method: 'POST',
            body: JSON.stringify({ direction })
        });
        // Reload leaderboard
        const currentId = window.location.hash.match(/leaderboard-(\w+)/);
        if (currentId) {
            window.viewLeaderboard(currentId[1]);
        }
    } catch (error) {
        alert('Failed to vote. Please login first.');
    }
};

// Submit Entry
async function submitEntry(leaderboardId) {
    const title = document.getElementById('entryTitle').value;
    const submitter = document.getElementById('entrySubmitter').value;
    const description = document.getElementById('entryDescription').value;
    
    try {
        await apiCall(`/leaderboards/${leaderboardId}/entries`, {
            method: 'POST',
            body: JSON.stringify({ title, submitter, description })
        });
        
        alert('Entry submitted successfully!');
        window.viewLeaderboard(leaderboardId);
    } catch (error) {
        alert('Failed to submit entry: ' + error.message);
    }
}

// Auth Functions
async function checkAuth() {
    const token = localStorage.getItem('token');
    if (token) {
        try {
            currentUser = await apiCall('/auth/me');
            updateUserUI();
        } catch (error) {
            localStorage.removeItem('token');
        }
    }
}

function updateUserUI() {
    if (currentUser) {
        document.querySelector('.nav-auth').innerHTML = `
            <span>Welcome, ${currentUser.display_name}!</span>
            <button id="logoutBtn" class="btn btn-outline">Logout</button>
        `;
        document.getElementById('logoutBtn').addEventListener('click', logout);
    }
}

// Login
elements.loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        const data = await apiCall('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        
        localStorage.setItem('token', data.token);
        currentUser = data.user;
        updateUserUI();
        elements.loginModal.classList.remove('active');
    } catch (error) {
        alert('Login failed: ' + error.message);
    }
});

// Register
elements.registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const displayName = document.getElementById('registerName').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    
    try {
        const data = await apiCall('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password, display_name: displayName })
        });
        
        localStorage.setItem('token', data.token);
        currentUser = data.user;
        updateUserUI();
        elements.registerModal.classList.remove('active');
    } catch (error) {
        alert('Registration failed: ' + error.message);
    }
});

// Logout
function logout() {
    localStorage.removeItem('token');
    currentUser = null;
    document.querySelector('.nav-auth').innerHTML = `
        <button id="loginBtn" class="btn btn-outline">Login</button>
        <button id="registerBtn" class="btn btn-primary">Register</button>
    `;
    elements.loginBtn = document.getElementById('loginBtn');
    elements.registerBtn = document.getElementById('registerBtn');
    setupEventListeners();
}

// Create Leaderboard
elements.createLeaderboardForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('leaderboardName').value;
    const category = document.getElementById('leaderboardCategory').value;
    const description = document.getElementById('leaderboardDescription').value;
    
    try {
        await apiCall('/leaderboards', {
            method: 'POST',
            body: JSON.stringify({ name, category, description })
        });
        
        alert('Leaderboard created successfully!');
        elements.createLeaderboardForm.reset();
        loadLeaderboards();
    } catch (error) {
        alert('Failed to create leaderboard: ' + error.message);
    }
});

// Event Listeners
function setupEventListeners() {
    // Modal open/close
    if (elements.loginBtn) {
        elements.loginBtn.addEventListener('click', () => elements.loginModal.classList.add('active'));
    }
    if (elements.registerBtn) {
        elements.registerBtn.addEventListener('click', () => elements.registerModal.classList.add('active'));
    }
    
    document.querySelectorAll('.modal-close').forEach(close => {
        close.addEventListener('click', () => {
            close.closest('.modal').classList.remove('active');
        });
    });
    
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });
    
    // Category filters
    elements.categoryFilters.addEventListener('click', (e) => {
        if (e.target.classList.contains('filter-btn')) {
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            e.target.classList.add('active');
            currentCategory = e.target.dataset.category;
            loadLeaderboards();
        }
    });
}

// Load categories
async function loadCategories() {
    try {
        const data = await apiCall('/categories');
        const categories = data.categories || [];
        
        elements.categoryFilters.innerHTML = `
            <button class="filter-btn active" data-category="all">All</button>
            ${categories.map(cat => `<button class="filter-btn" data-category="${cat}">${cat}</button>`).join('')}
        `;
    } catch (error) {
        console.error('Failed to load categories:', error);
    }
}

// Initialize categories on load
setTimeout(loadCategories, 1000);