/**
 * HeySeen Application Logic
 * Handles UI, user management, and PDF conversion
 */

// Global variables
const API_URL = "";
let currentUser = null;
let selectedFile = null;

// DOM Elements - will be initialized after DOM loads
let dropZone, fileInput, convertBtn, statusCard, progressBar, statusText;
let resultCard, errorCard, downloadLink, errorText;
let userAvatar, userDropdown;

/**
 * Initialize DOM Elements
 */
function initDOMElements() {
    dropZone = document.getElementById('drop-zone');
    fileInput = document.getElementById('file-input');
    convertBtn = document.getElementById('convert-btn');
    statusCard = document.getElementById('status-card');
    progressBar = document.getElementById('progress-bar');
    statusText = document.getElementById('status-text');
    resultCard = document.getElementById('result-card');
    errorCard = document.getElementById('error-card');
    downloadLink = document.getElementById('download-link');
    errorText = document.getElementById('error-text');
    userAvatar = document.getElementById('user-avatar');
    userDropdown = document.getElementById('user-dropdown');
}

/**
 * Initialize Application
 */
async function initApp() {
    try {
        // Initialize DOM elements first
        initDOMElements();
        // Initialize database
        await dbManager.init();
        
        // Load current user
        currentUser = await dbManager.getCurrentUser();
        
        // Update UI
        updateUserUI();
        
        // Setup event listeners
        setupEventListeners();
        
        console.log('✅ HeySeen initialized successfully');
    } catch (error) {
        console.error('❌ Failed to initialize app:', error);
        // Show a more user-friendly error
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #fee2e2; color: #991b1b; padding: 16px 20px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 9999; max-width: 400px;';
        errorDiv.innerHTML = `
            <div style="display: flex; align-items: start; gap: 12px;">
                <i class="fa-solid fa-exclamation-triangle" style="font-size: 20px; margin-top: 2px;"></i>
                <div>
                    <div style="font-weight: 600; margin-bottom: 4px;">Initialization Error</div>
                    <div style="font-size: 13px;">${error.message || 'Please refresh the page or clear your browser cache.'}</div>
                    <button onclick="location.reload()" style="margin-top: 10px; background: #991b1b; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">
                        Refresh Page
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(errorDiv);
    }
}

/**
 * Setup Event Listeners
 */
function setupEventListeners() {
    // Avatar dropdown toggle
    userAvatar.addEventListener('click', (e) => {
        e.stopPropagation();
        userDropdown.classList.toggle('active');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', () => {
        userDropdown.classList.remove('active');
    });

    userDropdown.addEventListener('click', (e) => {
        e.stopPropagation();
    });

    // File upload
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('border-blue-500', 'bg-blue-50');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('border-blue-500', 'bg-blue-50');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-blue-500', 'bg-blue-50');
        if (e.dataTransfer.files.length) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFile(e.target.files[0]);
        }
    });

    convertBtn.addEventListener('click', convertFile);
    
    // Avatar upload
    const profileAvatarLarge = document.getElementById('profile-avatar-large');
    const avatarInput = document.getElementById('avatar-input');
    
    if (profileAvatarLarge && avatarInput) {
        profileAvatarLarge.addEventListener('click', () => {
            avatarInput.click();
        });
        
        avatarInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            // Validate image
            if (!file.type.startsWith('image/')) {
                alert('Please upload an image file (JPG, PNG, etc.)');
                return;
            }
            
            // Check size (max 2MB)
            if (file.size > 2 * 1024 * 1024) {
                alert('Image size must be less than 2MB');
                return;
            }
            
            try {
                // Read and convert to base64
                const base64 = await readFileAsBase64(file);
                
                // Update user avatar in database
                currentUser.avatar = base64;
                await dbManager.saveUser(currentUser);
                
                // Update UI
                updateAvatarDisplay(base64);
                
                console.log('✅ Avatar updated successfully');
            } catch (error) {
                console.error('❌ Failed to update avatar:', error);
                alert('Failed to upload avatar. Please try again.');
            }
        });
    }
}

/**
 * Read file as base64
 */
function readFileAsBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

/**
 * Update avatar display in UI
 */
function updateAvatarDisplay(avatarBase64) {
    if (!avatarBase64) {
        // Show initials
        const initials = getInitials(currentUser.name);
        ['avatar-text', 'dropdown-avatar-text', 'profile-avatar-text'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = initials;
                el.style.display = '';
            }
        });
        
        ['profile-avatar-img'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
        
        return;
    }
    
    // Show avatar image
    ['profile-avatar-img'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.src = avatarBase64;
            el.style.display = 'block';
        }
    });
    
    // Hide initials in large avatar
    const profileAvatarText = document.getElementById('profile-avatar-text');
    if (profileAvatarText) profileAvatarText.style.display = 'none';
    
    // Small avatars - create img if not exists
    ['user-avatar', 'dropdown-avatar-small'].forEach((id, idx) => {
        const avatarContainer = document.getElementById(id === 'user-avatar' ? id : 'dropdown-avatar-text')?.parentElement;
        if (!avatarContainer) return;
        
        let img = avatarContainer.querySelector('.avatar-image');
        if (!img) {
            img = document.createElement('img');
            img.className = 'avatar-image';
            img.style.cssText = 'width: 100%; height: 100%; border-radius: 50%; object-fit: cover; position: absolute; top: 0; left: 0; pointer-events: none;';
            avatarContainer.style.position = 'relative';
            avatarContainer.appendChild(img);
        }
        img.src = avatarBase64;
        
        // Hide text
        const textEl = document.getElementById(id === 'user-avatar' ? 'avatar-text' : 'dropdown-avatar-text');
        if (textEl) textEl.style.display = 'none';
    });
}

/**
 * Update User UI
 */
function updateUserUI() {
    try {
        const initials = getInitials(currentUser.name);
        const limits = dbManager.getRoleLimits(currentUser.role);
        
        // Helper function to safely set text content
        const safeSetText = (id, text) => {
            const el = document.getElementById(id);
            if (el) el.textContent = text;
        };
        
        const safeSetClass = (id, className) => {
            const el = document.getElementById(id);
            if (el) el.className = className;
        };
        
        // Avatar
        safeSetText('avatar-text', initials);
        
        // Dropdown
        safeSetText('dropdown-avatar-text', initials);
        safeSetText('dropdown-name', currentUser.name);
        safeSetText('dropdown-email', currentUser.email);
        safeSetText('dropdown-limits', `${limits.maxPages} pages / ${(limits.maxSize / 1024 / 1024).toFixed(0)}MB`);
        
        const roleElement = document.getElementById('dropdown-role');
        if (roleElement) {
            roleElement.textContent = currentUser.role.toUpperCase();
            roleElement.className = `role-badge role-${currentUser.role.toLowerCase()}`;
        }
        
        // Update project count in dropdown
        dbManager.getUserProjects(currentUser.email).then(projects => {
            const count = projects.length;
            safeSetText('dropdown-project-count', `${count} project${count !== 1 ? 's' : ''}`);
        });
        
        // Upload limit text
        safeSetText('upload-limit-text', `Maximum: ${limits.maxPages} pages, ${(limits.maxSize / 1024 / 1024).toFixed(0)}MB`);
        
        // Show admin menu if admin with Experts role
        const adminBtn = document.getElementById('admin-menu-btn');
        if (adminBtn) {
            if (dbManager.isAdmin(currentUser.email) && currentUser.role === 'Experts') {
                adminBtn.classList.remove('hidden');
            } else {
                adminBtn.classList.add('hidden');
            }
        }
        
        // Update avatar display (clear for Guest)
        if (currentUser.role === 'Guest') {
            updateAvatarDisplay('');  // Clear avatar for Guest
        } else if (currentUser.avatar) {
            updateAvatarDisplay(currentUser.avatar);
        }
        
        // Update footer buttons based on role
        const logoutBtn = document.getElementById('logout-btn');
        const guestButtons = document.getElementById('guest-buttons');
        
        if (currentUser.role === 'Guest') {
            if (logoutBtn) logoutBtn.classList.add('hidden');
            if (guestButtons) guestButtons.classList.remove('hidden');
        } else {
            if (logoutBtn) logoutBtn.classList.remove('hidden');
            if (guestButtons) guestButtons.classList.add('hidden');
        }
    } catch (error) {
        console.error('Error updating UI:', error);
    }
}

/**
 * Get initials from name
 */
function getInitials(name) {
    const parts = name.trim().split(' ');
    if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
}

/**
 * Handle file selection
 */
function handleFile(file) {
    if (file.type !== 'application/pdf') {
        alert('Please upload a PDF file.');
        return;
    }
    
    // Validate file size
    const validation = dbManager.validateFile(file, currentUser.role);
    if (!validation.valid) {
        alert(validation.errors.join('\n'));
        return;
    }
    
    selectedFile = file;
    dropZone.innerHTML = `
        <i class="fa-solid fa-file-pdf text-4xl text-red-500 mb-2"></i>
        <p class="font-bold text-gray-800">${file.name}</p>
        <p class="text-sm text-gray-500">${(file.size / 1024 / 1024).toFixed(2)} MB</p>
        <p class="text-xs text-blue-500 mt-2">Click to change</p>
    `;
}

/**
 * Convert file to LaTeX
 */
async function convertFile() {
    if (!selectedFile) {
        alert('Please select a file first.');
        return;
    }

    const useMath = document.getElementById('math-ocr').checked;
    const useLLM = document.getElementById('use-llm').checked;
    
    // UI Update
    convertBtn.disabled = true;
    convertBtn.classList.add('opacity-50', 'cursor-not-allowed');
    statusCard.classList.remove('hidden');
    resultCard.classList.add('hidden');
    errorCard.classList.add('hidden');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        // 1. Create Job
        const response = await fetch(`${API_URL}/convert?math_ocr=${useMath}&use_llm=${useLLM}`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error('Upload failed');
        
        const job = await response.json();
        const jobId = job.job_id;
        
        // Save project to database
        const project = {
            id: jobId,
            userEmail: currentUser.email,
            fileName: selectedFile.name,
            fileSize: selectedFile.size,
            status: 'queued',
            useMath,
            useLLM,
            progress: 0,
            message: 'Queued',
            downloadUrl: null
        };
        await dbManager.createProject(project);
        
        // Update user project count
        currentUser.projectCount++;
        await dbManager.saveUser(currentUser);
        
        pollStatus(jobId);

    } catch (error) {
        showError(error.message);
    }
}

/**
 * Poll job status
 */
async function pollStatus(jobId) {
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`${API_URL}/status/${jobId}`);
            const data = await res.json();
            
            // Update UI
            const percentage = Math.round(data.progress * 100);
            progressBar.style.width = `${percentage}%`;
            statusText.textContent = `${data.message} (${percentage}%)`;
            
            // Update project in database
            const project = await dbManager.getProject(jobId);
            if (project) {
                project.status = data.status;
                project.progress = data.progress;
                project.message = data.message;
                await dbManager.updateProject(project);
            }
            
            if (data.status === 'completed') {
                clearInterval(interval);
                
                // Update project
                if (project) {
                    project.downloadUrl = `${API_URL}/download/${jobId}`;
                    project.completedAt = Date.now();
                    await dbManager.updateProject(project);
                }
                
                showResult(jobId);
            } else if (data.status === 'failed') {
                clearInterval(interval);
                showError(data.message);
            }
            
        } catch (e) {
            clearInterval(interval);
            showError("Connection lost");
        }
    }, 1000);
}

/**
 * Show result
 */
function showResult(jobId) {
    statusCard.classList.add('hidden');
    resultCard.classList.remove('hidden');
    downloadLink.href = `${API_URL}/download/${jobId}`;
    
    // Update project count in dropdown
    updateUserUI();
}

/**
 * Show error
 */
function showError(msg) {
    statusCard.classList.add('hidden');
    errorCard.classList.remove('hidden');
    errorText.textContent = msg;
    convertBtn.disabled = false;
    convertBtn.classList.remove('opacity-50', 'cursor-not-allowed');
}

/**
 * Open Profile Modal
 */
async function openProfileModal() {
    userDropdown.classList.remove('active');
    
    // Load user data
    const projects = await dbManager.getUserProjects(currentUser.email);
    const limits = dbManager.getRoleLimits(currentUser.role);
    
    // Update avatar display in modal
    const profileAvatarText = document.getElementById('profile-avatar-text');
    const profileAvatarImg = document.getElementById('profile-avatar-img');
    
    if (currentUser.avatar) {
        if (profileAvatarImg) {
            profileAvatarImg.src = currentUser.avatar;
            profileAvatarImg.style.display = 'block';
        }
        if (profileAvatarText) {
            profileAvatarText.style.display = 'none';
        }
    } else {
        if (profileAvatarText) {
            profileAvatarText.textContent = getInitials(currentUser.name);
            profileAvatarText.style.display = '';
        }
        if (profileAvatarImg) {
            profileAvatarImg.style.display = 'none';
        }
    }
    
    document.getElementById('profile-name').value = currentUser.name;
    document.getElementById('profile-email').value = currentUser.email;
    document.getElementById('profile-role').textContent = currentUser.role;
    document.getElementById('profile-projects').textContent = projects.length;
    document.getElementById('profile-max-pages').textContent = limits.maxPages;
    document.getElementById('profile-max-size').textContent = `${(limits.maxSize / 1024 / 1024).toFixed(0)}MB`;
    
    document.getElementById('profile-modal').classList.add('active');
}

/**
 * Save Profile
 */
async function saveProfile() {
    const name = document.getElementById('profile-name').value.trim();
    const email = document.getElementById('profile-email').value.trim();
    
    if (!name || !email) {
        alert('Please enter both name and email.');
        return;
    }
    
    if (!email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
        alert('Please enter a valid email address.');
        return;
    }
    
    // Check if email changed
    if (email !== currentUser.email) {
        // Check if new email already exists
        const existingUser = await dbManager.getUser(email);
        if (existingUser) {
            alert('This email is already registered. Please use a different email.');
            return;
        }
        
        // Delete old user and create new one
        await dbManager.deleteUser(currentUser.email);
        
        // Update all projects
        const projects = await dbManager.getUserProjects(currentUser.email);
        for (const project of projects) {
            project.userEmail = email;
            await dbManager.updateProject(project);
        }
    }
    
    currentUser.name = name;
    currentUser.email = email;
    await dbManager.saveUser(currentUser);
    
    updateUserUI();
    closeModal('profile-modal');
    
    alert('Profile updated successfully!');
}

/**
 * Open Projects Modal
 */
async function openProjectsModal() {
    userDropdown.classList.remove('active');
    
    const projects = await dbManager.getUserProjects(currentUser.email);
    const projectsList = document.getElementById('projects-list');
    
    if (projects.length === 0) {
        projectsList.innerHTML = `
            <div class="text-center text-gray-500 py-8">
                <i class="fa-solid fa-folder-open text-4xl mb-3"></i>
                <p>No projects yet. Start by converting your first PDF!</p>
            </div>
        `;
    } else {
        projectsList.innerHTML = projects.map(p => `
            <div class="border rounded-lg p-4 hover:shadow-md transition">
                <div class="flex items-center justify-between">
                    <div class="flex-1">
                        <div class="font-semibold text-gray-800">${escapeHtml(p.fileName)}</div>
                        <div class="text-xs text-gray-500 mt-1">
                            ${new Date(p.createdAt).toLocaleString()} • ${(p.fileSize / 1024 / 1024).toFixed(2)} MB
                        </div>
                        <div class="mt-2">
                            <span class="text-xs px-2 py-1 rounded ${getStatusClass(p.status)}">
                                ${getStatusText(p.status)}
                            </span>
                        </div>
                    </div>
                    <div class="flex space-x-2">
                        ${p.status === 'completed' && p.downloadUrl ? 
                            `<a href="${p.downloadUrl}" class="bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded text-sm">
                                <i class="fa-solid fa-download"></i>
                            </a>` : ''}
                        ${p.status === 'processing' ? 
                            `<button class="bg-blue-600 text-white px-3 py-2 rounded text-sm cursor-default">
                                ${Math.round(p.progress * 100)}%
                            </button>` : ''}
                        <button onclick="deleteProject('${p.id}')" class="bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded text-sm">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    document.getElementById('projects-modal').classList.add('active');
}

/**
 * Delete Project
 */
async function deleteProject(projectId) {
    if (!confirm('Are you sure you want to delete this project?')) {
        return;
    }
    
    await dbManager.deleteProject(projectId);
    
    // Update project count
    currentUser.projectCount = Math.max(0, (currentUser.projectCount || 0) - 1);
    await dbManager.saveUser(currentUser);
    updateUserUI();
    
    await openProjectsModal(); // Refresh the list
}

/**
 * Open Admin Modal
 */
async function openAdminModal() {
    if (!dbManager.isAdmin(currentUser.email)) {
        alert('Access denied. Admin only.');
        return;
    }
    
    userDropdown.classList.remove('active');
    
    // Load statistics
    await loadStatistics();
    await refreshUsersList();
    await loadAllProjects();
    
    document.getElementById('admin-modal').classList.add('active');
}

/**
 * Load Statistics
 */
async function loadStatistics() {
    const stats = await dbManager.getStatistics(currentUser.email);
    
    document.getElementById('stat-users').textContent = stats.totalUsers;
    document.getElementById('stat-projects').textContent = stats.totalProjects;
    document.getElementById('stat-completed').textContent = stats.projectsByStatus.completed || 0;
    
    // Users by role
    const usersByRoleHtml = Object.entries(stats.usersByRole)
        .map(([role, count]) => `
            <div class="flex justify-between items-center">
                <span class="role-badge role-${role.toLowerCase()}">${role}</span>
                <span class="font-bold">${count}</span>
            </div>
        `).join('');
    document.getElementById('users-by-role').innerHTML = usersByRoleHtml || '<p class="text-gray-500">No users</p>';
    
    // Projects by status
    const projectsByStatusHtml = Object.entries(stats.projectsByStatus)
        .map(([status, count]) => `
            <div class="flex justify-between items-center">
                <span class="${getStatusClass(status)}">${getStatusText(status)}</span>
                <span class="font-bold">${count}</span>
            </div>
        `).join('');
    document.getElementById('projects-by-status').innerHTML = projectsByStatusHtml || '<p class="text-gray-500">No projects</p>';
}

/**
 * Refresh Users List
 */
async function refreshUsersList() {
    try {
        const users = await dbManager.getAllUsers(currentUser.email);
        const tbody = document.getElementById('users-table-body');
    
        if (users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-gray-500">No users found</td></tr>';
            return;
        }
    
        tbody.innerHTML = users.map(u => {
            const projects = u.projectCount || 0;
            return `
            <tr class="border-t hover:bg-gray-50">
                <td class="px-4 py-3 text-sm">${escapeHtml(u.name)}</td>
                <td class="px-4 py-3 text-sm">${escapeHtml(u.email)}</td>
                <td class="px-4 py-3 text-sm">
                    <select onchange="updateUserRole('${escapeHtml(u.email)}', this.value)" 
                            class="role-badge role-${u.role.toLowerCase()} border-none cursor-pointer">
                        ${Object.keys(dbManager.USER_ROLES).map(role => 
                            `<option value="${role}" ${u.role === role ? 'selected' : ''}>${role}</option>`
                        ).join('')}
                    </select>
                </td>
                <td class="px-4 py-3 text-sm">${projects}</td>
                <td class="px-4 py-3 text-sm">
                    ${u.email !== dbManager.ADMIN_EMAIL ? 
                        `<button onclick="deleteUserAdmin('${escapeHtml(u.email)}')" 
                                class="text-red-600 hover:text-red-800">
                            <i class="fa-solid fa-trash"></i>
                        </button>` : 
                        '<span class="text-purple-600"><i class="fa-solid fa-crown"></i> Admin</span>'}
                </td>
            </tr>
        `;
        }).join('');
    } catch (error) {
        console.error('Failed to refresh users list:', error);
        const tbody = document.getElementById('users-table-body');
        tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-red-500">Failed to load users</td></tr>';
    }
}

/**
 * Update User Role
 */
async function updateUserRole(email, newRole) {
    try {
        await dbManager.updateUserRole(email, newRole, currentUser.email);
        await loadStatistics();
        await refreshUsersList();
        alert(`Role updated to ${newRole}`);
    } catch (error) {
        alert(`Failed to update role: ${error.message}`);
    }
}

/**
 * Delete User (Admin)
 */
async function deleteUserAdmin(email) {
    if (!confirm(`Are you sure you want to delete user ${email}?`)) {
        return;
    }
    
    try {
        await dbManager.deleteUser(email, currentUser.email);
        await refreshUsersList();
        await loadStatistics();
    } catch (error) {
        alert(`Failed to delete user: ${error.message}`);
    }
}

/**
 * Load All Projects
 */
async function loadAllProjects() {
    const projects = await dbManager.getAllProjects();
    const projectsList = document.getElementById('all-projects-list');
    
    if (projects.length === 0) {
        projectsList.innerHTML = '<div class="text-center text-gray-500 py-8">No projects found</div>';
        return;
    }
    
    projectsList.innerHTML = projects.map(p => `
        <div class="border rounded-lg p-3 hover:shadow transition">
            <div class="flex items-center justify-between">
                <div class="flex-1">
                    <div class="font-semibold text-sm">${escapeHtml(p.fileName)}</div>
                    <div class="text-xs text-gray-500 mt-1">
                        User: ${escapeHtml(p.userEmail)} • ${new Date(p.createdAt).toLocaleString()}
                    </div>
                    <span class="text-xs px-2 py-1 rounded ${getStatusClass(p.status)} inline-block mt-1">
                        ${getStatusText(p.status)}
                    </span>
                </div>
                <button onclick="deleteProjectAdmin('${p.id}')" class="text-red-600 hover:text-red-800 ml-2">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

/**
 * Delete Project (Admin)
 */
async function deleteProjectAdmin(projectId) {
    if (!confirm('Delete this project?')) return;
    
    await dbManager.deleteProject(projectId);
    await loadAllProjects();
    await loadStatistics();
}

/**
 * Hash password using SHA-256 (with fallback for non-HTTPS)
 */
async function hashPassword(password) {
    // For consistency, always use simpleHash since users may sign up on HTTP and login on HTTPS
    // In production with proper backend, replace this with bcrypt or similar server-side
    return simpleHash(password);
}

/**
 * Simple hash function (fallback for non-HTTPS)
 * Using djb2 algorithm - NOT cryptographically secure!
 */
function simpleHash(str) {
    let hash = 5381;
    for (let i = 0; i < str.length; i++) {
        hash = ((hash << 5) + hash) + str.charCodeAt(i);
        hash = hash >>> 0; // Convert to unsigned 32-bit integer
    }
    // Convert to hex string (8 characters) and pad with additional rounds for length
    let result = hash.toString(16).padStart(8, '0');
    
    // Add more rounds for better distribution (still not secure, but better than single hash)
    for (let round = 0; round < 3; round++) {
        hash = 5381;
        for (let i = 0; i < result.length; i++) {
            hash = ((hash << 5) + hash) + result.charCodeAt(i);
            hash = hash >>> 0;
        }
        result += hash.toString(16).padStart(8, '0');
    }
    
    return result;
}

/**
 * Open Sign Up Modal (for Guest users)
 */
function openSignUpModal() {
    userDropdown.classList.remove('active');
    document.getElementById('signup-name').value = '';
    document.getElementById('signup-email').value = '';
    document.getElementById('signup-password').value = '';
    document.getElementById('signup-modal').classList.add('active');
}

/**
 * Open Login Modal (for Guest users)
 */
function openLoginModal() {
    userDropdown.classList.remove('active');
    document.getElementById('login-email').value = '';
    document.getElementById('login-password').value = '';
    document.getElementById('login-modal').classList.add('active');
}

/**
 * Perform Sign Up
 */
async function performSignUp() {
    const name = document.getElementById('signup-name').value.trim();
    const email = document.getElementById('signup-email').value.trim();
    const password = document.getElementById('signup-password').value;
    
    // Validation
    if (!name) {
        alert('Please enter your full name.');
        return;
    }
    
    if (!email || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
        alert('Please enter a valid email address.');
        return;
    }
    
    if (password.length < 8) {
        alert('Password must be at least 8 characters long.');
        return;
    }
    
    // Check if user already exists
    const existingUser = await dbManager.getUser(email);
    if (existingUser) {
        alert('This email is already registered. Please login instead.');
        closeModal('signup-modal');
        openLoginModal();
        return;
    }
    
    // Hash password
    const hashedPassword = await hashPassword(password);
    
    try {
        // Create user on server
        const user = await dbManager.createUserOnServer(email, name, hashedPassword);
        
        // Save to localStorage and login
        localStorage.setItem('currentUserEmail', user.email);
        
        currentUser = user;
        updateUserUI();
        closeModal('signup-modal');
        
        if (user.role === 'Experts') {
            alert('🎉 Welcome Admin! You have been assigned Expert role with full access.');
        } else {
            alert(`✅ Account created successfully!\nYou are now a ${user.role} with ${dbManager.getRoleLimits(user.role).maxPages} pages / ${(dbManager.getRoleLimits(user.role).maxSize / 1024 / 1024).toFixed(0)}MB limit.`);
        }
        
        location.reload();
    } catch (error) {
        alert(`❌ Sign up failed: ${error.message}`);
    }
}

/**
 * Perform Login
 */
async function performLogin() {
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    
    // Validation
    if (!email || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
        alert('Please enter a valid email address.');
        return;
    }
    
    if (!password) {
        alert('Please enter your password.');
        return;
    }
    
    // Hash password
    const hashedPassword = await hashPassword(password);
    
    try {
        // Verify login on server
        const user = await dbManager.verifyLogin(email, hashedPassword);
        
        // Save to localStorage and login
        localStorage.setItem('currentUserEmail', user.email);
        
        currentUser = user;
        updateUserUI();
        closeModal('login-modal');
        
        location.reload();
    } catch (error) {
        alert(`❌ ${error.message}`);
    }
}

/**
 * Perform Logout
 */
async function performLogout() {
    if (!confirm('Are you sure you want to logout?')) {
        return;
    }
    
    userDropdown.classList.remove('active');
    
    // Clear guest avatar if exists
    const guestUser = await dbManager.getUser('guest@heyseen.local');
    if (guestUser && guestUser.avatar) {
        guestUser.avatar = '';
        await dbManager.saveUser(guestUser);
    }
    
    // Logout to guest
    localStorage.setItem('currentUserEmail', 'guest@heyseen.local');
    location.reload();
}

/**
 * Close Modal
 */
function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

/**
 * Switch Tab
 */
function switchTab(tabName) {
    // Update buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.closest('.tab-button').classList.add('active');
    
    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`tab-${tabName}`).classList.add('active');
}

/**
 * Get status class
 */
function getStatusClass(status) {
    const classes = {
        'queued': 'bg-yellow-100 text-yellow-800',
        'processing': 'bg-blue-100 text-blue-800',
        'completed': 'bg-green-100 text-green-800',
        'failed': 'bg-red-100 text-red-800'
    };
    return classes[status] || 'bg-gray-100 text-gray-800';
}

/**
 * Get status text
 */
function getStatusText(status) {
    const texts = {
        'queued': 'Queued',
        'processing': 'Processing',
        'completed': 'Completed',
        'failed': 'Failed'
    };
    return texts[status] || status;
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize app when page loads
document.addEventListener('DOMContentLoaded', initApp);
