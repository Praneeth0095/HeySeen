"""
User Manager - Handle user authentication and data persistence
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger("UserManager")

class UserManager:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.users_file = data_dir / "users.json"
        self.admin_email = "nguyendangminhphuc@dhsphue.edu.vn"
        self._ensure_data_dir()
        self._load_users()
    
    def _ensure_data_dir(self):
        """Create data directory if not exists"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.users_file.exists():
            self.users_file.write_text(json.dumps({}, indent=2))
    
    def _load_users(self) -> Dict:
        """Load users from file"""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                self.users = json.load(f)
            logger.info(f"Loaded {len(self.users)} users from {self.users_file}")
        except Exception as e:
            logger.error(f"Failed to load users: {e}")
            self.users = {}
    
    def _save_users(self):
        """Save users to file"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save users: {e}")
            raise
    
    def create_user(self, email: str, name: str, password_hash: str) -> Dict:
        """Create a new user"""
        if email in self.users:
            raise ValueError(f"User {email} already exists")
        
        # Determine role
        role = "Experts" if email == self.admin_email else "Students"
        
        user = {
            "email": email,
            "name": name,
            "password": password_hash,
            "role": role,
            "avatar": "",
            "createdAt": int(datetime.now().timestamp() * 1000),
            "lastLogin": int(datetime.now().timestamp() * 1000),
            "projectCount": 0
        }
        
        self.users[email] = user
        self._save_users()
        
        logger.info(f"Created user: {email} with role {role}")
        return user
    
    def get_user(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        return self.users.get(email)
    
    def verify_password(self, email: str, password_hash: str) -> bool:
        """Verify user password"""
        user = self.users.get(email)
        if not user:
            return False
        return user.get("password") == password_hash
    
    def update_user(self, email: str, updates: Dict) -> Dict:
        """Update user information"""
        if email not in self.users:
            raise ValueError(f"User {email} not found")
        
        # Update allowed fields
        allowed_fields = ["name", "avatar", "lastLogin", "projectCount"]
        for field in allowed_fields:
            if field in updates:
                self.users[email][field] = updates[field]
        
        self._save_users()
        return self.users[email]
    
    def update_role(self, email: str, new_role: str, admin_email: str) -> Dict:
        """Update user role (admin only)"""
        if admin_email != self.admin_email:
            raise PermissionError("Only admin can update roles")
        
        if email not in self.users:
            raise ValueError(f"User {email} not found")
        
        self.users[email]["role"] = new_role
        self._save_users()
        
        logger.info(f"Admin {admin_email} updated {email} role to {new_role}")
        return self.users[email]
    
    def get_all_users(self, admin_email: str) -> List[Dict]:
        """Get all users (admin only)"""
        if admin_email != self.admin_email:
            raise PermissionError("Only admin can view all users")
        
        return list(self.users.values())
    
    def delete_user(self, email: str, admin_email: str):
        """Delete user (admin only)"""
        if admin_email != self.admin_email:
            raise PermissionError("Only admin can delete users")
        
        if email not in self.users:
            raise ValueError(f"User {email} not found")
        
        del self.users[email]
        self._save_users()
        
        logger.info(f"Admin {admin_email} deleted user {email}")
