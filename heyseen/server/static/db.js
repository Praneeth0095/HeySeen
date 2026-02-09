/**
 * IndexedDB Manager for HeySeen
 * Manages user profiles and project history
 */

const DB_NAME = 'HeySeenDB';
const DB_VERSION = 1;
const USERS_STORE = 'users';
const PROJECTS_STORE = 'projects';

// User roles with their limits
const USER_ROLES = {
    Guest: { maxPages: 1, maxSize: 1 * 1024 * 1024 }, // 1MB
    Students: { maxPages: 10, maxSize: 5 * 1024 * 1024 }, // 5MB
    Masters: { maxPages: 20, maxSize: 10 * 1024 * 1024 }, // 10MB
    Lecturers: { maxPages: 50, maxSize: 20 * 1024 * 1024 }, // 20MB
    Professors: { maxPages: 100, maxSize: 50 * 1024 * 1024 }, // 50MB
    Experts: { maxPages: 200, maxSize: 100 * 1024 * 1024 } // 100MB
};

const ADMIN_EMAIL = 'nguyendangminhphuc@dhsphue.edu.vn';

class HeySeenDB {
    constructor() {
        this.db = null;
        this.USER_ROLES = USER_ROLES;
        this.ADMIN_EMAIL = ADMIN_EMAIL;
    }

    /**
     * Initialize database
     */
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve(this.db);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // Users store
                if (!db.objectStoreNames.contains(USERS_STORE)) {
                    const userStore = db.createObjectStore(USERS_STORE, { keyPath: 'email' });
                    userStore.createIndex('role', 'role', { unique: false });
                    userStore.createIndex('createdAt', 'createdAt', { unique: false });
                }

                // Projects store
                if (!db.objectStoreNames.contains(PROJECTS_STORE)) {
                    const projectStore = db.createObjectStore(PROJECTS_STORE, { keyPath: 'id' });
                    projectStore.createIndex('userEmail', 'userEmail', { unique: false });
                    projectStore.createIndex('createdAt', 'createdAt', { unique: false });
                    projectStore.createIndex('status', 'status', { unique: false });
                }
            };
        });
    }

    /**
     * Get or create current user
     */
    async getCurrentUser() {
        // Check localStorage for logged-in user
        const savedEmail = localStorage.getItem('currentUserEmail');
        
        if (savedEmail && savedEmail !== 'guest@heyseen.local') {
            const user = await this.getUser(savedEmail);
            if (user) {
                // User exists on server, update last login
                user.lastLogin = Date.now();
                await this.saveUser(user);
                return user;
            } else {
                // User not found on server, logout to guest
                console.warn('User not found on server, logging out to Guest');
                localStorage.setItem('currentUserEmail', 'guest@heyseen.local');
                // Fall through to return guest user
            }
        }
        
        // Return or create guest user
        let user = await this.getUser('guest@heyseen.local');
        if (!user) {
            user = {
                email: 'guest@heyseen.local',
                name: 'Guest User',
                role: 'Guest',
                avatar: '',
                createdAt: Date.now(),
                lastLogin: Date.now(),
                projectCount: 0
            };
            await this.saveUser(user);
        } else {
            user.lastLogin = Date.now();
            await this.saveUser(user);
        }
        
        // Save guest to localStorage
        localStorage.setItem('currentUserEmail', 'guest@heyseen.local');
        return user;
    }

    /**
     * Get user by email (from server or local guest)
     */
    async getUser(email) {
        // Guest user is local only
        if (email === 'guest@heyseen.local') {
            return new Promise((resolve, reject) => {
                const transaction = this.db.transaction([USERS_STORE], 'readonly');
                const store = transaction.objectStore(USERS_STORE);
                const request = store.get(email);
                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            });
        }
        
        // Other users: fetch from server
        try {
            const response = await fetch(`/api/users/${encodeURIComponent(email)}`);
            if (!response.ok) {
                if (response.status === 404) return null;
                throw new Error(`Failed to fetch user: ${response.status}`);
            }
            const data = await response.json();
            return data.user || null;
        } catch (error) {
            console.error('Failed to get user from server:', error);
            return null;
        }
    }

    /**
     * Save or update user (to server or local guest)
     */
    async saveUser(user) {
        // Guest user is local only
        if (user.email === 'guest@heyseen.local') {
            return new Promise((resolve, reject) => {
                const transaction = this.db.transaction([USERS_STORE], 'readwrite');
                const store = transaction.objectStore(USERS_STORE);
                const request = store.put(user);
                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            });
        }
        
        // Other users: update on server
        try {
            const updates = {
                name: user.name,
                avatar: user.avatar,
                lastLogin: user.lastLogin,
                projectCount: user.projectCount
            };
            
            const response = await fetch(`/api/users/${encodeURIComponent(user.email)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates)
            });
            
            if (!response.ok) {
                throw new Error(`Failed to update user: ${response.status}`);
            }
            
            return user;
        } catch (error) {
            console.error('Failed to save user to server:', error);
            throw error;
        }
    }

    /**
     * Create user on server (sign up)
     */
    async createUserOnServer(email, name, passwordHash) {
        try {
            const response = await fetch('/api/users/signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email,
                    name,
                    password_hash: passwordHash
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to create user');
            }
            
            const data = await response.json();
            return data.user;
        } catch (error) {
            console.error('Sign up error:', error);
            throw error;
        }
    }

    /**
     * Verify login on server
     */
    async verifyLogin(email, passwordHash) {
        try {
            const response = await fetch('/api/users/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email,
                    password_hash: passwordHash
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Login failed');
            }
            
            const data = await response.json();
            return data.user;
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    }

    /**
     * Get all users (admin only - from server)
     */
    async getAllUsers(adminEmail) {
        try {
            const response = await fetch(`/api/users?admin_email=${encodeURIComponent(adminEmail)}`);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to get users');
            }
            
            const data = await response.json();
            return data.users || [];
        } catch (error) {
            console.error('Get all users error:', error);
            throw error;
        }
    }

    /**
     * Update user role (admin only - on server)
     */
    async updateUserRole(email, newRole, adminEmail) {
        try {
            const response = await fetch(`/api/users/${encodeURIComponent(email)}/role`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    new_role: newRole,
                    admin_email: adminEmail
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to update role');
            }
            
            const data = await response.json();
            return data.user;
        } catch (error) {
            console.error('Update role error:', error);
            throw error;
        }
    }

    /**
     * Delete user (admin only - from server)
     */
    async deleteUser(email, adminEmail) {
        try {
            const response = await fetch(`/api/users/${encodeURIComponent(email)}?admin_email=${encodeURIComponent(adminEmail)}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to delete user');
            }
            
            return true;
        } catch (error) {
            console.error('Delete user error:', error);
            throw error;
        }
    }

    /**
     * Create project
     */
    async createProject(project) {
        if (!project.id) {
            project.id = this.generateId();
        }
        project.createdAt = Date.now();
        project.status = 'queued';

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([PROJECTS_STORE], 'readwrite');
            const store = transaction.objectStore(PROJECTS_STORE);
            const request = store.add(project);

            request.onsuccess = () => resolve(project);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Update project
     */
    async updateProject(project) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([PROJECTS_STORE], 'readwrite');
            const store = transaction.objectStore(PROJECTS_STORE);
            const request = store.put(project);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Get project by ID
     */
    async getProject(id) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([PROJECTS_STORE], 'readonly');
            const store = transaction.objectStore(PROJECTS_STORE);
            const request = store.get(id);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Get projects by user email
     */
    async getUserProjects(email) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([PROJECTS_STORE], 'readonly');
            const store = transaction.objectStore(PROJECTS_STORE);
            const index = store.index('userEmail');
            const request = index.getAll(email);

            request.onsuccess = () => {
                const projects = request.result;
                projects.sort((a, b) => b.createdAt - a.createdAt);
                resolve(projects);
            };
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Delete project
     */
    async deleteProject(id) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([PROJECTS_STORE], 'readwrite');
            const store = transaction.objectStore(PROJECTS_STORE);
            const request = store.delete(id);

            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Get all projects (admin only)
     */
    async getAllProjects() {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([PROJECTS_STORE], 'readonly');
            const store = transaction.objectStore(PROJECTS_STORE);
            const request = store.getAll();

            request.onsuccess = () => {
                const projects = request.result;
                projects.sort((a, b) => b.createdAt - a.createdAt);
                resolve(projects);
            };
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Check if user is admin
     */
    isAdmin(email) {
        return email === ADMIN_EMAIL;
    }

    /**
     * Get user role limits
     */
    getRoleLimits(role) {
        return USER_ROLES[role] || USER_ROLES.Guest;
    }

    /**
     * Validate file for user role
     */
    validateFile(file, role) {
        const limits = this.getRoleLimits(role);
        const errors = [];

        if (file.size > limits.maxSize) {
            errors.push(`Kích thước file vượt quá giới hạn ${(limits.maxSize / 1024 / 1024).toFixed(0)}MB của role ${role}`);
        }

        // Note: Page count validation will be done after PDF is loaded
        return {
            valid: errors.length === 0,
            errors,
            limits
        };
    }

    /**
     * Generate unique ID
     */
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    /**
     * Get statistics
     */
    async getStatistics(adminEmail) {
        const users = await this.getAllUsers(adminEmail);
        const projects = await this.getAllProjects();

        const stats = {
            totalUsers: users.length,
            totalProjects: projects.length,
            projectsByStatus: {},
            usersByRole: {},
            recentProjects: projects.slice(0, 10)
        };

        // Count projects by status
        projects.forEach(p => {
            stats.projectsByStatus[p.status] = (stats.projectsByStatus[p.status] || 0) + 1;
        });

        // Count users by role
        users.forEach(u => {
            stats.usersByRole[u.role] = (stats.usersByRole[u.role] || 0) + 1;
        });

        return stats;
    }
}

// Export singleton instance
const dbManager = new HeySeenDB();
