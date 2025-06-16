"""
Authentication Module

Handles user authentication and access control.
"""

from enum import Enum
from typing import Dict, Optional
import hashlib


class UserRole(str, Enum):
    """User role enumeration."""
    JUNIOR = "Junior"
    SENIOR = "Senior"
    MANAGER = "Manager"
    ADMIN = "Admin"


class AuthenticationManager:
    """Handles user authentication and session management."""
    
    def __init__(self):
        """Initialize with demo users."""
        # In a real application, this would be a database
        # Format: username -> {password_hash, role}
        self.users = {
            "junior_user": {
                "password_hash": self._hash_password("junior123"),
                "role": UserRole.JUNIOR
            },
            "senior_user": {
                "password_hash": self._hash_password("senior123"),
                "role": UserRole.SENIOR
            },
            "manager_user": {
                "password_hash": self._hash_password("manager123"),
                "role": UserRole.MANAGER
            },
            "admin_user": {
                "password_hash": self._hash_password("admin123"),
                "role": UserRole.ADMIN
            }
        }
        
        # Active sessions
        self.active_sessions = {}
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256.
        
        In a real application, use a more secure method like bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """Authenticate a user and return session ID if successful.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            Optional[str]: Session ID if authenticated, None otherwise
        """
        if username not in self.users:
            return None
            
        user = self.users[username]
        
        if self._hash_password(password) != user["password_hash"]:
            return None
            
        # In a real app, generate a secure session token
        session_id = f"session_{username}"
        
        # Store session
        self.active_sessions[session_id] = {
            "username": username,
            "role": user["role"]
        }
        
        return session_id
    
    def get_user_role(self, session_id: str) -> Optional[UserRole]:
        """Get user role from session ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Optional[UserRole]: User role if session is valid, None otherwise
        """
        if session_id not in self.active_sessions:
            return None
            
        return self.active_sessions[session_id]["role"]
    
    def logout(self, session_id: str) -> bool:
        """Logout user by removing session.
        
        Args:
            session_id: Session ID
            
        Returns:
            bool: True if logout successful, False otherwise
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        
        return False
    
    def has_access(self, session_id: str, required_role: UserRole) -> bool:
        """Check if user has required access level.
        
        Args:
            session_id: Session ID
            required_role: Required role for access
            
        Returns:
            bool: True if user has access, False otherwise
        """
        user_role = self.get_user_role(session_id)
        
        if user_role is None:
            return False
        
        # Access hierarchy: ADMIN > MANAGER > SENIOR > JUNIOR
        role_hierarchy = {
            UserRole.JUNIOR: 1,
            UserRole.SENIOR: 2,
            UserRole.MANAGER: 3,
            UserRole.ADMIN: 4
        }
        
        return role_hierarchy[user_role] >= role_hierarchy[required_role]
