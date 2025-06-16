import os
import time
from typing import Dict, List, Any, BinaryIO, Optional
from enum import Enum
import firebase_admin
from firebase_admin import storage, firestore
from werkzeug.utils import secure_filename
from core.firebase_auth import UserRole

class DocumentType(str, Enum):
    POLICY = "Policy"
    FINANCIAL = "Financial"
    HR = "HR"
    PROJECT = "Project"
    GENERAL = "General"
    OTHER = "Other"

class DocumentManager:
    def __init__(self):
        """Initialize document manager with Firebase storage and Firestore."""
        # Initialize Firestore client
        self.db = firestore.client()
        
        # Initialize Firebase Storage
        try:
            # For TechConsult Inc project, we use the storage bucket name from config
            # Bucket name should match what's shown in Firebase console
            self.bucket = storage.bucket("chatbot-c14e4.firebasestorage.app")
            
        except Exception as e:
            print(f"Error initializing storage bucket with explicit name: {e}")
            # Try with default bucket
            try:
                self.bucket = storage.bucket()
                print("Initialized default storage bucket")
            except Exception as e2:
                print(f"Could not initialize default storage bucket either: {e2}")
                self.bucket = None
    
    def upload_document(self, 
                       file: BinaryIO, 
                       filename: str,
                       title: str,
                       description: str,
                       min_access_level: UserRole,
                       document_type: DocumentType,
                       user: Dict[str, Any],
                       tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Upload document to Firebase Storage and store metadata in Firestore.
        
        Args:
            file: File-like object containing document data
            filename: Original filename
            title: Document title
            description: Document description
            min_access_level: Minimum user role required to access (Junior, Senior, Manager)
            document_type: Type of document (Policy, Financial, etc.)
            user: Current user data (must contain uid and email)
            tags: Optional list of tags
            
        Returns:
            Dict with success status and document ID
        """
        try:
            # Create a secure filename with timestamp to avoid collisions
            secure_name = f"{int(time.time())}_{secure_filename(filename)}"
            file_path = f"documents/{user['uid']}/{secure_name}"
            
            # Upload to Firebase Storage
            blob = self.bucket.blob(file_path)
            
            # Set metadata on storage object
            metadata = {
                "min_access_level": min_access_level.value,
                "document_type": document_type.value,
                "uploaded_by": user['uid'],
                "uploader_email": user['email'],
                "title": title
            }
            blob.metadata = metadata
            blob.upload_from_file(file)
            
            # Create document metadata in Firestore
            doc_ref = self.db.collection('documents').document()
            doc_data = {
                "title": title,
                "min_access_level": min_access_level.value,
                "document_type": document_type.value,
                "description": description,
                "uploaded_by": user['uid'],
                "uploader_email": user['email'],
                "upload_timestamp": firestore.SERVER_TIMESTAMP,
                "tags": tags or [],
                "file_path": file_path,
                "storage_url": f"gs://{self.bucket.name}/{file_path}"
            }
            doc_ref.set(doc_data)
            
            return {"success": True, "document_id": doc_ref.id}
        
        except Exception as e:
            print(f"Error uploading document: {e}")
            return {"success": False, "error": str(e)}
    
    def get_accessible_documents(self, user_role: UserRole) -> List[Dict[str, Any]]:
        """Get documents accessible to the user based on their role.
        
        Args:
            user_role: User's role (Junior, Senior, Manager, Admin)
            
        Returns:
            List of document metadata accessible to the user
        """
        try:
            # Determine which access levels this role can access
            accessible_levels = []
            if user_role == UserRole.JUNIOR:
                accessible_levels = [UserRole.JUNIOR.value]
            elif user_role == UserRole.SENIOR:
                accessible_levels = [UserRole.JUNIOR.value, UserRole.SENIOR.value]
            elif user_role in [UserRole.MANAGER, UserRole.ADMIN]:
                accessible_levels = [UserRole.JUNIOR.value, UserRole.SENIOR.value, UserRole.MANAGER.value]
            
            # Query documents with appropriate access level
            docs = self.db.collection('documents').where("min_access_level", "in", accessible_levels).stream()
            
            # Convert to list of dictionaries
            result = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                result.append(data)
            
            return result
            
        except Exception as e:
            print(f"Error getting accessible documents: {e}")
            return []
    
    def get_document_content(self, document_id: str, user_role: UserRole) -> Dict[str, Any]:
        """Get document content if user has access.
        
        Args:
            document_id: Firestore document ID
            user_role: User's role
            
        Returns:
            Dict with success flag and document data or error
        """
        try:
            # Get document metadata
            doc_ref = self.db.collection('documents').document(document_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return {"success": False, "error": "Document not found"}
            
            doc_data = doc.to_dict()
            
            # Check access permissions
            min_level = doc_data.get("min_access_level")
            has_access = False
            
            if min_level == UserRole.JUNIOR.value:
                has_access = True
            elif min_level == UserRole.SENIOR.value:
                has_access = user_role in [UserRole.SENIOR, UserRole.MANAGER, UserRole.ADMIN]
            elif min_level == UserRole.MANAGER.value:
                has_access = user_role in [UserRole.MANAGER, UserRole.ADMIN]
            
            if not has_access:
                return {"success": False, "error": "Access denied. Insufficient permissions."}
            
            # Get file from Storage
            file_path = doc_data.get("file_path")
            if not file_path:
                return {"success": False, "error": "File path not found in document metadata"}
            
            blob = self.bucket.blob(file_path)
            if not blob.exists():
                return {"success": False, "error": "File not found in storage"}
            
            # For PDF, we might return a download URL or the binary content
            download_url = blob.generate_signed_url(
                version="v4",
                expiration=3600,  # 1 hour
                method="GET"
            )
            
            doc_data["download_url"] = download_url
            return {"success": True, "document": doc_data}
            
        except Exception as e:
            print(f"Error retrieving document: {e}")
            return {"success": False, "error": str(e)}
    
    def delete_document(self, document_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a document if user has permission.
        
        Args:
            document_id: Firestore document ID
            user: Current user data
            
        Returns:
            Dict with success status
        """
        deletion_logs = []
        deletion_logs.append(f"Starting deletion of document {document_id}")
        
        try:
            # Check if document exists
            doc_ref = self.db.collection('documents').document(document_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                deletion_logs.append(f"Document {document_id} not found in Firestore")
                return {"success": False, "error": "Document not found", "logs": deletion_logs}
            
            doc_data = doc.to_dict()
            deletion_logs.append(f"Found document: {doc_data.get('title')} (ID: {document_id})")
            
            # Check permission (only uploader or admin can delete)
            if user.get('uid') != doc_data.get('uploaded_by') and user.get('role') != UserRole.ADMIN.value:
                deletion_logs.append(f"Permission denied for user {user.get('uid')} with role {user.get('role')}")
                return {"success": False, "error": "Permission denied. Only uploader or admin can delete documents.", "logs": deletion_logs}
            
            # Delete from Vector Database first
            deletion_logs.append("Attempting to delete document chunks from vector database...")
            try:
                from database import VectorDatabase
                vector_db = VectorDatabase()
                
                # Check how many chunks exist for this document
                chunk_count = vector_db.get_document_chunk_count(document_id)
                deletion_logs.append(f"Found {chunk_count} chunks in vector database for document {document_id}")
                
                if chunk_count > 0:
                    # Delete the chunks
                    vector_result = vector_db.delete_document_chunks(document_id)
                    if vector_result.get("success"):
                        deletion_logs.append(f"✅ Vector database cleanup: {vector_result.get('message')}")
                    else:
                        deletion_logs.append(f"⚠️ Vector database cleanup failed: {vector_result.get('error')}")
                        # Continue with deletion even if vector cleanup fails
                else:
                    deletion_logs.append("No chunks found in vector database - skipping vector cleanup")
                    
            except Exception as vector_error:
                deletion_logs.append(f"⚠️ Vector database cleanup error: {str(vector_error)}")
                # Continue with deletion even if vector cleanup fails
            
            # Delete from Storage - two-phase attempt for different storage formats
            storage_success = False
            storage_error_details = []
            
            try:
                # 1. Try direct path from Firestore
                file_path = doc_data.get('file_path')
                if file_path:
                    deletion_logs.append(f"Attempting to delete blob at original path: {file_path}")
                    blob = self.bucket.blob(file_path)
                    try:
                        blob.delete()
                        deletion_logs.append("Blob deleted successfully with original path")
                        storage_success = True
                    except Exception as e:
                        storage_error_details.append(f"Original path deletion failed: {str(e)}")
                        deletion_logs.append(f"First attempt failed: {str(e)}")
                else:
                    deletion_logs.append("No file path found in document data")
                    
                # 2. If first attempt failed, try nested folder structure based on document ID
                if not storage_success:
                    # Handle folder structure seen in Firebase console (document ID as folder)
                    try:
                        # Get file name from original path
                        file_name = file_path.split('/')[-1] if file_path else None
                        if file_name:
                            folder_paths = [f"documents/{document_id}/{file_name}"]
                            # Also try with just the folder
                            if '/' in file_path:
                                folder_parts = file_path.split('/')
                                if len(folder_parts) > 2:
                                    # Try the actual user ID in path if available
                                    user_id = folder_parts[1]
                                    folder_paths.append(f"documents/{document_id}/{user_id}/{file_name}")
                                    
                            # Try all possible paths
                            for try_path in folder_paths:
                                deletion_logs.append(f"Trying alternative path: {try_path}")
                                try:
                                    alt_blob = self.bucket.blob(try_path)
                                    alt_blob.delete(not_found_ok=True)
                                    deletion_logs.append(f"Alternative path deletion succeeded: {try_path}")
                                    storage_success = True
                                    break
                                except Exception as e:
                                    storage_error_details.append(f"Alternative path deletion failed: {str(e)}")
                    except Exception as e:
                        storage_error_details.append(f"Alternative path construction failed: {str(e)}")
            except Exception as storage_error:
                storage_error_details.append(f"Overall storage deletion failed: {str(storage_error)}")
                deletion_logs.append(f"Error in storage deletion process: {str(storage_error)}")
            
            if not storage_success:
                deletion_logs.append("WARNING: Failed to delete file from Storage but proceeding with metadata deletion")
                deletion_logs.append(f"Storage errors: {', '.join(storage_error_details)}")
            
            # Delete from Firestore - always do this regardless of Storage result
            doc_ref.delete()
            deletion_logs.append("Firestore document deleted successfully")
            
            return {
                "success": True, 
                "message": "Document deleted" + (" (metadata only, file may remain in storage)" if not storage_success else ""), 
                "logs": deletion_logs
            }
            
        except Exception as e:
            deletion_logs.append(f"Unexpected error: {str(e)}")
            return {"success": False, "error": str(e), "logs": deletion_logs}
