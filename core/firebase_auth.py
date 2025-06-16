"""
Firebase Authentication Module for TechConsult Inc Knowledge Chatbot.
Handles user authentication, role management, and session control.
"""
import os
import json
from typing import Dict, Any, Optional, Tuple
import sys
import firebase_admin
from firebase_admin import credentials, auth, firestore

# Apply patch before importing pyrebase
from utils.pyrebase_patch import patch_pyrebase
patch_pyrebase()

import pyrebase
import json
from enum import Enum
from typing import Dict, Any, List, Optional
import streamlit as st

# User roles enum (keeping the same as original)
class UserRole(str, Enum):
    JUNIOR = "Junior"
    SENIOR = "Senior"
    MANAGER = "Manager"
    ADMIN = "Admin"

class FirebaseAuthManager:
    """Firebase Authentication Manager for role-based access control."""
    
    def __init__(self, firebase_config_path: str = None, service_account_path: str = None):
        """Initialize Firebase Authentication and Firestore.
        
        Args:
            firebase_config_path: Path to Firebase web config JSON file (deprecated, use env vars)
            service_account_path: Path to Firebase Admin SDK service account JSON file (deprecated, use env vars)
        """
        # Initialize Firebase Admin SDK
        try:
            # Try to use environment variables first, fallback to JSON file
            if all(os.getenv(key) for key in ['FIREBASE_TYPE', 'FIREBASE_PROJECT_ID', 'FIREBASE_PRIVATE_KEY_ID', 'FIREBASE_PRIVATE_KEY', 'FIREBASE_CLIENT_EMAIL']):
                # Use environment variables
                service_account_info = {
                    "type": os.getenv("FIREBASE_TYPE"),
                    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
                    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
                    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
                    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
                    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
                    "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN")
                }
                cred = credentials.Certificate(service_account_info)
            else:
                # Fallback to JSON file
                service_account_path = service_account_path or os.getenv(
                    "FIREBASE_SERVICE_ACCOUNT", 
                    "./config/firebase-adminsdk.json"
                )
                cred = credentials.Certificate(service_account_path)
            
            # Check if any Firebase app is already initialized
            try:
                self.admin_app = firebase_admin.get_app()
            except ValueError:
                # No app exists, initialize default app
                self.admin_app = firebase_admin.initialize_app(cred)
            
            self.db = firestore.client()
        except Exception as e:
            st.error(f"Failed to initialize Firebase Admin SDK: {str(e)}")
            raise e
        
        # Initialize Firebase client SDK for user-facing operations
        try:
            # Try to use environment variables first, fallback to JSON file
            if all(os.getenv(key) for key in ['FIREBASE_API_KEY', 'FIREBASE_AUTH_DOMAIN', 'FIREBASE_PROJECT_ID']):
                # Use environment variables
                self.firebase_config = {
                    "apiKey": os.getenv("FIREBASE_API_KEY"),
                    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
                    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
                    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
                    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
                    "appId": os.getenv("FIREBASE_APP_ID"),
                    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID"),
                    "databaseURL": os.getenv("FIREBASE_DATABASE_URL", "")
                }
            else:
                # Fallback to JSON file
                firebase_config_path = firebase_config_path or os.getenv("FIREBASE_CONFIG", "./config/firebase_config.json")
                if os.path.exists(firebase_config_path):
                    with open(firebase_config_path, "r") as f:
                        self.firebase_config = json.load(f)
                else:
                    # Use environment variables as fallback
                    if all(os.getenv(key) for key in ['FIREBASE_API_KEY', 'FIREBASE_AUTH_DOMAIN', 'FIREBASE_PROJECT_ID']):
                        self.firebase_config = {
                            "apiKey": os.getenv("FIREBASE_API_KEY"),
                            "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
                            "projectId": os.getenv("FIREBASE_PROJECT_ID"),
                            "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", ""),
                            "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
                            "appId": os.getenv("FIREBASE_APP_ID", ""),
                            "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID", ""),
                            "databaseURL": os.getenv("FIREBASE_DATABASE_URL", "")
                        }
                    else:
                        raise ValueError("Firebase configuration not found. Please provide either a config file or set environment variables.")
            
            self.firebase = pyrebase.initialize_app(self.firebase_config)
            self.auth = self.firebase.auth()
        except Exception as e:
            st.error(f"Failed to initialize Firebase client SDK: {str(e)}")
            raise e
            
    def register_user(self, email: str, password: str, role: UserRole = UserRole.JUNIOR) -> Dict[str, Any]:
        """Register a new user with the given email and password.
        
        Args:
            email: User's email
            password: User's password
            role: User's role (default: JUNIOR)
            
        Returns:
            Dict with user information or error
        """
        try:
            # Create user in Firebase Authentication
            user = auth.create_user(
                email=email,
                password=password,
                email_verified=False
            )
            
            # Set custom claims for user role
            auth.set_custom_user_claims(user.uid, {"role": role.value})
            
            # Store additional user data in Firestore
            user_ref = self.db.collection('users').document(user.uid)
            user_ref.set({
                'email': email,
                'role': role.value,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            
            return {"success": True, "user_id": user.uid, "message": "User registered successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate a user with email and password.
        
        Args:
            email: User's email
            password: User's password
            
        Returns:
            Dict with authentication status, token, and user info
        """
        try:
            # Authenticate user with Firebase Auth
            user = self.auth.sign_in_with_email_and_password(email, password)
            
            # Get the user's role from Firestore
            uid = user['localId']
            id_token = user['idToken']
            
            # Get or create user document in Firestore
            user_ref = self.db.collection('users').document(uid)
            user_data = user_ref.get()
            
            if user_data.exists:
                user_info = user_data.to_dict()
                role = user_info.get('role', UserRole.JUNIOR.value)
            else:
                # If user doesn't exist in Firestore, create a document
                role = UserRole.JUNIOR.value
                user_ref.set({
                    'email': email,
                    'role': role,
                    'created_at': firestore.SERVER_TIMESTAMP
                })
            
            # Store in session state
            if 'user_info' not in st.session_state:
                st.session_state.user_info = {}
            
            st.session_state.user_info = {
                'uid': uid,
                'email': email,
                'role': role,
                'id_token': id_token,
                'authenticated': True
            }
            
            return {
                'success': True,
                'message': f'Logged in as {email}',
                'user': st.session_state.user_info
            }
            
        except Exception as e:
            # Convert Firebase errors to user-friendly messages
            error_msg = str(e)
            
            if "INVALID_PASSWORD" in error_msg or "INVALID_LOGIN_CREDENTIALS" in error_msg:
                friendly_error = "Incorrect password. Please try again."
            elif "EMAIL_NOT_FOUND" in error_msg:
                friendly_error = "Email not found. Please check your email or register for an account."
            elif "INVALID_EMAIL" in error_msg:
                friendly_error = "Invalid email format. Please enter a valid email address."
            elif "TOO_MANY_ATTEMPTS_TRY_LATER" in error_msg:
                friendly_error = "Too many login attempts. Please try again later."
            else:
                friendly_error = "Login failed. Please check your credentials and try again."
            
            return {
                'success': False,
                'error': friendly_error
            }
            
    def logout(self) -> None:
        """Log out the current user by clearing session state."""
        if 'user_info' in st.session_state:
            st.session_state.user_info = {
                'authenticated': False
            }
        
    def is_authenticated(self) -> bool:
        """Check if the user is authenticated.
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        if 'user_info' not in st.session_state:
            return False
        return st.session_state.user_info.get('authenticated', False)
        
    def get_user_role(self) -> Optional[str]:
        """Get the role of the authenticated user.
        
        Returns:
            str: User role or None if not authenticated
        """
        if not self.is_authenticated():
            return None
        return st.session_state.user_info.get('role')
        
    def update_user_role(self, uid: str, new_role: UserRole) -> Dict[str, Any]:
        """Update a user's role (admin only).
        
        Args:
            uid: User ID to update
            new_role: New role to assign
            
        Returns:
            Dict with update status
        """
        try:
            # Check if current user is admin
            if self.get_user_role() != UserRole.ADMIN.value:
                return {
                    "success": False, 
                    "error": "Only administrators can update user roles"
                }
            
            # Update custom claims for role
            auth.set_custom_user_claims(uid, {"role": new_role.value})
            
            # Update role in Firestore
            user_ref = self.db.collection('users').document(uid)
            user_ref.update({'role': new_role.value})
            
            return {
                "success": True, 
                "message": f"User role updated to {new_role.value}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def get_all_users(self) -> Dict[str, Any]:
        """Get all users (admin only).
        
        Returns:
            Dict with users list or error
        """
        try:
            # Check if current user is admin
            if self.get_user_role() != UserRole.ADMIN.value:
                return {
                    "success": False, 
                    "error": "Only administrators can view all users"
                }
            
            # Get users from both Firebase Authentication and Firestore
            users = []
            
            # First get users from Firebase Authentication
            auth_users = {}
            try:
                # Get all Firebase Auth users
                for user in auth.list_users().iterate_all():
                    auth_users[user.uid] = {
                        'uid': user.uid,
                        'email': user.email,
                        'role': 'Junior'  # Default role until we get from Firestore
                    }
            except Exception as auth_error:
                print(f"Error getting auth users: {str(auth_error)}")
            
            # Then get users from Firestore
            try:
                user_docs = self.db.collection('users').stream()
                
                for doc in user_docs:
                    user_data = doc.to_dict()
                    user_data['uid'] = doc.id
                    
                    # Update or add to auth_users
                    if doc.id in auth_users:
                        auth_users[doc.id].update(user_data)
                    else:
                        # User exists in Firestore but not in Auth
                        auth_users[doc.id] = user_data
            except Exception as firestore_error:
                print(f"Error getting Firestore users: {str(firestore_error)}")
            
            # Convert dict to list
            users = list(auth_users.values())
                
            return {"success": True, "users": users}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_user(self, uid: str) -> Dict[str, Any]:
        """Delete a user (admin only).
        
        Args:
            uid: User ID to delete
            
        Returns:
            Dict with success status and message
        """
        try:
            # Check if current user is admin
            if self.get_user_role() != UserRole.ADMIN.value:
                return {
                    "success": False, 
                    "error": "Only administrators can delete users"
                }
            
            # Get user from Firestore to check their role
            user_doc_ref = self.db.collection('users').document(uid)
            user_doc = user_doc_ref.get()
            
            if not user_doc.exists:
                return {
                    "success": False,
                    "error": "User not found in database"
                }
            
            user_data = user_doc.to_dict()
            # Prevent deletion of admin users
            if user_data.get('role') == UserRole.ADMIN.value:
                return {
                    "success": False,
                    "error": "Admin users cannot be deleted through this interface"
                }
            
            try:
                # Try to delete from Firebase Authentication
                auth.delete_user(uid)
            except Exception as auth_error:
                # If the user doesn't exist in Authentication but exists in Firestore,
                # we should still remove them from Firestore
                if "USER_NOT_FOUND" in str(auth_error):
                    pass  # Continue to delete from Firestore
                else:
                    raise auth_error  # Re-raise other authentication errors
            
            # Delete from Firestore
            user_doc_ref.delete()
            
            return {"success": True, "message": f"User with ID {uid} deleted successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def has_access_to_level(self, access_level: str) -> bool:
        """Check if the current user has access to the specified level.
        
        Args:
            access_level: Access level to check against
            
        Returns:
            bool: True if user has access, False otherwise
        """
        user_role = self.get_user_role()
        if not user_role:
            return False
            
        # Define role hierarchy
        role_hierarchy = {
            UserRole.JUNIOR.value: [UserRole.JUNIOR.value],
            UserRole.SENIOR.value: [UserRole.JUNIOR.value, UserRole.SENIOR.value],
            UserRole.MANAGER.value: [UserRole.JUNIOR.value, UserRole.SENIOR.value, UserRole.MANAGER.value],
            UserRole.ADMIN.value: [UserRole.JUNIOR.value, UserRole.SENIOR.value, UserRole.MANAGER.value, UserRole.ADMIN.value]
        }
        
        return access_level in role_hierarchy.get(user_role, [])
