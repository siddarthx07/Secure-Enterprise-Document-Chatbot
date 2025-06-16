import streamlit as st
from typing import Dict, Any, Optional, List
import tempfile
import os
from firebase_admin import firestore

from document_modules.document_manager import DocumentManager, DocumentType
from core.firebase_auth import FirebaseAuthManager, UserRole
from document_modules.document_processing import DocumentProcessor
from core.database import VectorDatabase

def display_document_upload(auth_manager: FirebaseAuthManager, doc_manager: DocumentManager) -> None:
    """Display document upload interface with access level selection.
    
    Args:
        auth_manager: FirebaseAuthManager instance
        doc_manager: DocumentManager instance
    """
    st.header("Upload Document")
    
    # Check if user is authenticated
    if not auth_manager.is_authenticated():
        st.error("You must be logged in to upload documents.")
        return
        
    # Get user information from session state
    user_data = st.session_state.user_info
    if not user_data or not user_data.get('uid'):
        st.error("User session error. Please log out and log back in.")
        return
    
    # Create upload form
    with st.form(key="document_upload_form"):
        uploaded_file = st.file_uploader("Choose a PDF document", type="pdf", key="doc_upload")
        title = st.text_input("Document Title", key="doc_title")
        description = st.text_area("Description", key="doc_description")
        
        col1, col2 = st.columns(2)
        with col1:
            doc_type = st.selectbox(
                "Document Type",
                options=[t.value for t in DocumentType],
                key="doc_type"
            )
        
        with col2:
            # Only show access levels up to the user's own level
            user_role = auth_manager.get_user_role()
            available_levels = []
            
            if user_role in [UserRole.JUNIOR.value, UserRole.SENIOR.value, UserRole.MANAGER.value, UserRole.ADMIN.value]:
                available_levels.append(UserRole.JUNIOR.value)
            
            if user_role in [UserRole.SENIOR.value, UserRole.MANAGER.value, UserRole.ADMIN.value]:
                available_levels.append(UserRole.SENIOR.value)
            
            if user_role in [UserRole.MANAGER.value, UserRole.ADMIN.value]:
                available_levels.append(UserRole.MANAGER.value)
            
            access_level = st.selectbox(
                "Minimum Access Level Required",
                options=available_levels,
                help="Sets who can access this document. Junior (all users), Senior (only Senior+), Manager (only Manager+)",
                key="doc_access_level"
            )
        
        tags = st.text_input("Tags (comma-separated)", key="doc_tags")
        
        submit_button = st.form_submit_button("Upload Document")
        
        if submit_button:
            if not uploaded_file:
                st.error("Please select a file to upload.")
                return
                
            if not title:
                st.error("Please provide a document title.")
                return
                
            # Process tags
            tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
            
            # Save uploaded file to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name
            
            try:
                # Reopen the file for reading
                with open(tmp_path, 'rb') as file:
                    # Map string to enum
                    access_level_enum = UserRole(access_level)
                    doc_type_enum = DocumentType(doc_type)
                    
                    # Upload document
                    result = doc_manager.upload_document(
                        file=file,
                        filename=uploaded_file.name,
                        title=title,
                        description=description,
                        min_access_level=access_level_enum,
                        document_type=doc_type_enum,
                        user={
                            "uid": user_data.get("uid", ""),
                            "email": user_data.get("email", ""),
                            "role": user_role
                        },
                        tags=tag_list
                    )
                    
                    if result.get("success", False):
                        st.success(f"Document '{title}' uploaded successfully!")
                        
                        # Process document to vector database
                        with st.spinner("Processing document for chatbot..."): 
                            try:
                                # Initialize vector database and document processor
                                vector_db = VectorDatabase()
                                doc_processor = DocumentProcessor(vector_db=vector_db)
                                
                                # Process the newly uploaded document
                                document_id = result.get("document_id")
                                if document_id:
                                    process_result = doc_processor.process_firebase_document(
                                        document_id=document_id,
                                        user_role=UserRole(user_role)
                                    )
                                    
                                    if process_result.get("success", False):
                                        st.success("Document processed successfully for chatbot! You can now ask questions about it.")
                                    else:
                                        st.warning(f"Document uploaded but processing failed: {process_result.get('error')}")
                                else:
                                    st.warning("Document uploaded but couldn't be processed (missing document ID).")
                            except Exception as e:
                                st.warning(f"Document uploaded but processing error occurred: {str(e)}")
                                
                        st.session_state.documents = []
                    else:
                        st.error(f"Error uploading document: {result.get('error', 'Unknown error')}")
            finally:
                # Delete temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

def display_document_list(auth_manager: FirebaseAuthManager, doc_manager: DocumentManager) -> None:
    """Display list of documents accessible to the current user.
    
    Args:
        auth_manager: FirebaseAuthManager instance
        doc_manager: DocumentManager instance
    """
    st.header("Available Documents")
    
    # Get current user role
    user_role = auth_manager.get_user_role()
    if not user_role:
        st.error("You must be logged in to view documents.")
        return
    
    # Get user info from session state
    user_data = st.session_state.get("user_info", {})
    
    # Check if user is admin for delete functionality
    is_admin = user_role == UserRole.ADMIN.value
    
    user_role_enum = UserRole(user_role)
    
    # Check if a document was deleted and show confirmation
    if st.session_state.get('document_deleted'):
        st.success("Document deleted successfully!")
        st.session_state.pop('document_deleted', None)
    
    # Handle document deletion if action triggered from previous render
    doc_id_to_delete = st.session_state.get('doc_id_to_delete')
    if doc_id_to_delete and is_admin:
        result = doc_manager.delete_document(
            document_id=doc_id_to_delete,
            user={
                "uid": user_data.get("uid", ""),
                "role": user_role
            }
        )
        print(f"Delete result for {doc_id_to_delete}: {result}")
        
        # Clear deletion state
        st.session_state.pop('doc_id_to_delete', None)
        
        # Display deletion logs
        if "logs" in result:
            with st.expander("Deletion Process Logs", expanded=True):
                for log in result["logs"]:
                    st.text(log)
        
        if result.get("success"):
            st.session_state['document_deleted'] = True
            st.success(result.get("message", "Document deleted successfully"))
        else:
            st.error(result.get("error", "Error deleting document"))
    
    # Get accessible documents
    documents = doc_manager.get_accessible_documents(user_role_enum)
    
    if not documents:
        st.info("No documents available for your access level.")
        return
    
    # Create a filter/search input
    search = st.text_input("Search documents by title or type", "")
    search_lower = search.lower() if search else ""
    
    # Display documents
    doc_count = 0
    for doc in documents:
        # Apply search filter if provided
        if search and search_lower not in doc['title'].lower() and search_lower not in doc.get('document_type', '').lower():
            continue
            
        doc_count += 1
        doc_id = doc['id']  # Store ID in a separate variable to avoid issues
        
        with st.expander(f"{doc['title']} ({doc['document_type']})"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Description:** {doc.get('description', 'No description')}")
                st.write(f"**Type:** {doc.get('document_type')}")
                st.write(f"**Tags:** {', '.join(doc.get('tags', []))}")
                st.write(f"**Uploaded by:** {doc.get('uploader_email')}")
                st.write(f"**Access Level:** {doc.get('min_access_level')}")
                st.write(f"**Document ID:** {doc_id}")
            
            # Action buttons - create layout based on user role
            if is_admin:
                # For admins, create two columns for View/Delete actions
                button_col1, button_col2 = st.columns(2)
            else:
                # For non-admins, only create a single column for the View action
                button_col1 = st.columns(1)[0]
                
            with button_col1:
                if st.button("View Document", key=f"view_{doc_id}"):
                    # Get document content with access check
                    doc_content = doc_manager.get_document_content(doc_id, user_role_enum)
                    
                    if doc_content.get('success'):
                        document = doc_content.get("document", {})
                        download_url = document.get("download_url")
                        
                        if download_url:
                            st.markdown(f"[Download Document]({download_url})")
                            st.markdown(f"<iframe src='{download_url}' width='100%' height='500px'></iframe>", unsafe_allow_html=True)
                        else:
                            st.error("Document URL not available.")
                    else:
                        st.error(doc_content.get("error", "Failed to retrieve document."))
            
            # Delete button (Admin only)
            if is_admin:
                with button_col2:
                    # Check if this document is in confirmation mode
                    confirm_key = f"confirm_delete_{doc_id}"
                    
                    if st.session_state.get(confirm_key, False):
                        # Show confirmation buttons
                        st.warning(f"Delete '{doc['title']}'?")
                        col_confirm, col_cancel = st.columns(2)
                        
                        with col_confirm:
                            if st.button("✓ Yes", key=f"yes_{doc_id}"):
                                # Set document ID to delete and clear confirmation
                                st.session_state['doc_id_to_delete'] = doc_id
                                st.session_state[confirm_key] = False
                                st.rerun()
                        
                        with col_cancel:
                            if st.button("✗ No", key=f"no_{doc_id}"):
                                # Clear confirmation mode
                                st.session_state[confirm_key] = False
                                st.rerun()
                    else:
                        # Show delete button
                        if st.button("🗑️ Delete", key=f"delete_{doc_id}"):
                            # Enter confirmation mode
                            st.session_state[confirm_key] = True
                            st.rerun()
    
    if doc_count == 0:
        if search:
            st.info("No documents match your search.")
        else:
            st.info("No documents available for your access level.")

def display_admin_document_management(auth_manager: FirebaseAuthManager, doc_manager: DocumentManager) -> None:
    """Display admin document management interface.
    
    Args:
        auth_manager: FirebaseAuthManager instance
        doc_manager: DocumentManager instance
    """
    st.header("Document Management")
    
    # Check if user is admin
    if auth_manager.get_user_role() != UserRole.ADMIN.value:
        st.error("You need admin privileges to access this page.")
        return
    
    # Get user information from session state for delete operations
    user_data = st.session_state.user_info
    if not user_data or not user_data.get('uid'):
        st.error("User session error. Please log out and log back in.")
        return
    
    # Check if a document was deleted and show confirmation
    if st.session_state.get('admin_document_deleted'):
        st.success("Document deleted successfully!")
        st.session_state.pop('admin_document_deleted', None)
    
    # Handle document deletion if action triggered from previous render
    admin_doc_id_to_delete = st.session_state.get('admin_doc_id_to_delete')
    if admin_doc_id_to_delete:
        result = doc_manager.delete_document(
            document_id=admin_doc_id_to_delete,
            user={
                "uid": user_data.get("uid", ""),
                "role": auth_manager.get_user_role()
            }
        )
        print(f"Admin delete result for {admin_doc_id_to_delete}: {result}")
        
        # Clear deletion state
        st.session_state.pop('admin_doc_id_to_delete', None)
        
        # Display detailed deletion logs
        if "logs" in result:
            with st.expander("Deletion Process Logs", expanded=True):
                for log in result["logs"]:
                    st.text(log)
        
        if result.get("success"):
            st.session_state['admin_document_deleted'] = True
            st.success(result.get("message", "Document deleted successfully"))
        else:
            st.error(result.get("error", "Error deleting document"))
    
    # Get all documents from Firestore (admin sees all)
    docs = doc_manager.db.collection('documents').order_by("upload_timestamp", direction=firestore.Query.DESCENDING).stream()
    
    st.subheader("All Documents")
    
    # Create a search input
    search = st.text_input("Search documents by title or description", "")
    search_lower = search.lower() if search else ""
    
    # Display documents with search filtering
    doc_count = 0
    for doc in docs:
        doc_data = doc.to_dict()
        doc_data['id'] = doc.id
        
        # Apply search filter if search term provided
        if search_lower and search_lower not in doc_data.get('title', '').lower() and search_lower not in doc_data.get('description', '').lower():
            continue
        
        doc_count += 1
        
        with st.expander(f"{doc_data['title']} ({doc_data['document_type']})"):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**Description:** {doc_data.get('description', 'No description')}")
                st.write(f"**Type:** {doc_data.get('document_type')}")
                st.write(f"**Tags:** {', '.join(doc_data.get('tags', []))}")
                st.write(f"**Document ID:** {doc_data['id']}")
            
            with col2:
                st.write(f"**Access Level:** {doc_data.get('min_access_level')}")
                st.write(f"**Uploaded by:** {doc_data.get('uploader_email')}")
                upload_time = doc_data.get('upload_timestamp')
                if upload_time:
                    st.write(f"**Upload Date:** {upload_time.strftime('%Y-%m-%d %H:%M')}")
            
            with col3:
                # Check if this document is in confirmation mode
                admin_confirm_key = f"admin_confirm_delete_{doc_data['id']}"
                
                if st.session_state.get(admin_confirm_key, False):
                    # Show confirmation buttons
                    st.warning(f"Delete '{doc_data['title']}'?")
                    action_col1, action_col2 = st.columns(2)
                    
                    with action_col1:
                        if st.button("✓ Yes", key=f"admin_yes_{doc_data['id']}"):
                            # Set document ID to delete and clear confirmation
                            st.session_state['admin_doc_id_to_delete'] = doc_data['id']
                            st.session_state[admin_confirm_key] = False
                            st.rerun()
                    
                    with action_col2:
                        if st.button("✗ No", key=f"admin_no_{doc_data['id']}"):
                            # Clear confirmation mode
                            st.session_state[admin_confirm_key] = False
                            st.rerun()
                else:
                    # Show delete button
                    if st.button("🗑️ Delete", key=f"admin_delete_{doc_data['id']}"):
                        # Enter confirmation mode
                        st.session_state[admin_confirm_key] = True
                        st.rerun()
    
    if doc_count == 0:
        if search:
            st.info("No documents match your search.")
        else:
            st.info("No documents have been uploaded yet.")
