"""
TechConsult Inc Knowledge Chatbot

Streamlit application for document upload and chatbot interface.
"""

import os
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, Any

from document_processor import DocumentProcessor
from database import VectorDatabase
from firebase_auth import FirebaseAuthManager, UserRole
from admin import display_admin_interface
from document_manager import DocumentManager
from document_ui import display_document_upload, display_document_list, display_admin_document_management
from financial_filter import FinancialContentFilter, FilterAction
from audit_logger import AuditLogger

# Load environment variables
load_dotenv()

# Constants
DOCUMENT_STORAGE = os.environ.get("DOCUMENT_STORAGE", "./documents")
VECTOR_DB_PATH = os.environ.get("VECTOR_DB_PATH", "./vector_db")

# Initialize components
document_processor = DocumentProcessor(document_dir=DOCUMENT_STORAGE)
vector_db = VectorDatabase(db_path=VECTOR_DB_PATH)
auth_manager = FirebaseAuthManager()
doc_manager = DocumentManager()
financial_filter = FinancialContentFilter(audit_log_enabled=True)
audit_logger = AuditLogger(collection_name="sensitive_query_logs")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "documents" not in st.session_state:
    st.session_state.documents = []
    
if "user_info" not in st.session_state:
    st.session_state.user_info = {
        "authenticated": False
    }

def main():
    """Main application."""
    st.title("TechConsult Inc Knowledge Chatbot")
    
    # Sidebar for authentication
    with st.sidebar:
        handle_authentication()
        
        # Admin panel link (only for Admin users)
        if auth_manager.is_authenticated() and auth_manager.get_user_role() == UserRole.ADMIN.value:
            st.divider()
            st.header("Admin Panel")
            if st.button("Open Admin Dashboard"):
                st.session_state.show_admin = True
    
    # Show admin interface if requested and user is admin
    if auth_manager.is_authenticated() and \
       auth_manager.get_user_role() == UserRole.ADMIN.value and \
       st.session_state.get("show_admin", False):
        # Add a button to return to the main chatbot interface
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("← Return to Chatbot"):
                st.session_state.show_admin = False
                st.rerun()
                
        tab1, tab2 = st.tabs(["User Management", "Document Management"])
        with tab1:
            display_admin_interface(auth_manager)
        with tab2:
            display_admin_document_management(auth_manager, doc_manager)
    # Main chat interface if authenticated    
    elif auth_manager.is_authenticated():
        tab1, tab2 = st.tabs(["Chat", "Documents"])
        with tab1:
            display_chat_interface()
        with tab2:
            st.subheader("Document Management")
            display_document_upload(auth_manager, doc_manager)
            st.divider()
            display_document_list(auth_manager, doc_manager)
    else:
        st.info("Please login to use the chatbot.")

def handle_authentication():
    """Handle Firebase user authentication."""
    st.header("Authentication")
    
    # If user is logged in, show logout button
    if auth_manager.is_authenticated():
        user_role = auth_manager.get_user_role()
        st.success(f"Logged in as {st.session_state.user_info.get('email')} ({user_role})")
        
        if st.button("Logout"):
            auth_manager.logout()
            st.session_state.messages = []
            st.session_state.show_admin = False
            st.rerun()
    else:
        # Login/Register tabs
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        # Login tab
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login")
                
                if submitted:
                    result = auth_manager.login(email, password)
                    if result.get("success"):
                        st.rerun()
                    else:
                        st.error(f"Login failed: {result.get('error')}")
        
        # Register tab
        with tab2:
            with st.form("register_form"):
                st.write("New user registration (default role: Junior)")
                new_email = st.text_input("Email")
                new_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button("Register")
                
                if submitted:
                    if new_password != confirm_password:
                        st.error("Passwords do not match")
                    elif not new_email or not new_password:
                        st.error("Email and password are required")
                    else:
                        result = auth_manager.register_user(new_email, new_password)
                        if result.get("success"):
                            st.success("Registration successful! Please login.")
                        else:
                            st.error(f"Registration failed: {result.get('error')}")

def display_chat_interface():
    """Display the chat interface."""
    st.header("Chat")
    
    # Use CSS to make sure chat input stays at the bottom
    st.markdown("""
    <style>
    .stChatFloatingInputContainer {
        position: fixed;
        bottom: 20px;
        z-index: 999;
        width: calc(100% - 80px);
    }
    .main > div:last-child {
        padding-bottom: 100px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input (will be positioned at the bottom via CSS)
    prompt = st.chat_input("Ask a question about TechConsult documents")
    
    # Handle prompt if entered
    if prompt:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # If the user greets, respond with their email and skip further processing
        greetings = ["hi", "hello", "hey", "hi there", "hello there"]
        if prompt.strip().lower() in greetings:
            user_email = st.session_state.user_info.get("email", "there")
            assistant_response = f"Hello, {user_email}! How can I help you today?"
            # Store assistant response
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            with st.chat_message("assistant"):
                st.markdown(assistant_response)
            return
        
        # Get user role for access control
        user_role = auth_manager.get_user_role()
        
        # Display assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            # Implement RAG pipeline
            with st.spinner("Searching for information..."):
                try:
                    # Convert user_role to string if it's an enum
                    role_str = user_role.value if hasattr(user_role, 'value') else str(user_role)
                    
                    # Retrieve relevant document chunks based on query
                    docs = vector_db.search(
                        query=prompt,
                        limit=5,  # Number of relevant chunks to retrieve
                        user_role=role_str  # For access control
                    )
                    
                    if not docs:
                        response = "I don't have information about that in my knowledge base. Please try a different question or consider uploading relevant documents."
                        # Add additional guidance based on query content
                        if "financial" in prompt.lower() or "revenue" in prompt.lower() or "salary" in prompt.lower():
                            response += "\n\nNote: If you're looking for financial information, please be aware that specific financial figures may be restricted based on your access level and company policy."
                    else:
                        # Analyze query intent to assess context relevance
                        # Simple relevance scoring for demonstration
                        query_tokens = set(prompt.lower().split())
                        
                        # Count how many docs seem highly relevant to the query
                        highly_relevant_docs = 0
                        doc_relevance_scores = []
                        
                        for doc in docs:
                            content_tokens = set(doc.page_content.lower().split())
                            # Calculate overlap between query and document content
                            token_overlap = len(query_tokens.intersection(content_tokens))
                            relevance_score = token_overlap / len(query_tokens) if query_tokens else 0
                            doc_relevance_scores.append(relevance_score)
                            
                            if relevance_score > 0.3:  # Threshold for high relevance
                                highly_relevant_docs += 1
                        
                        # Get the average relevance score
                        avg_relevance = sum(doc_relevance_scores) / len(doc_relevance_scores) if doc_relevance_scores else 0
                        
                        # Prepare context from retrieved documents
                        context = "\n\n".join([f"Document: {doc.metadata.get('title', 'Untitled')}\n{doc.page_content}" for doc in docs])
                        
                        # Extract document titles and metadata for citation
                        # Use document ID as key to avoid duplicates
                        unique_sources = {}
                        for doc in docs:
                            doc_id = doc.metadata.get('document_id', '')
                            title = doc.metadata.get('title', 'Untitled')
                            doc_type = doc.metadata.get('document_type', 'Document')
                            
                            # Skip documents without title or ID to avoid empty citations
                            if not title or title == 'Untitled':
                                continue
                                
                            # If document already in sources, just ensure it's only added once
                            if doc_id and doc_id not in unique_sources:
                                unique_sources[doc_id] = {
                                    "title": title,
                                    "document_type": doc_type,
                                    "relevance": 1  # Start with base relevance
                                }
                            elif doc_id in unique_sources:
                                # If we see it again, increase relevance score
                                unique_sources[doc_id]["relevance"] += 1
                        
                        # Prepare citations based on retrieved documents
                        # (Financial filtering removed)
                        is_restricted_query = False
                        
                        # Get user email and role for content filtering
                        user_email = st.session_state.user_info.get("email", "")
                        
                        # Apply financial content filtering
                        filter_result = financial_filter.process_query(
                            query=prompt,
                            user_email=user_email,
                            user_role=role_str,
                            document_context=context
                        )
                        
                        query_analysis = filter_result.get("query_analysis", {})
                        rule_result = filter_result.get("rule_result", {})
                        audit_log = filter_result.get("audit_log")
                        
                        # Log sensitive financial queries if enabled
                        if audit_log:
                            audit_logger.log_sensitive_query(audit_log)
                        
                        # Determine if this is a restricted query
                        is_restricted_query = rule_result.get("action") == FilterAction.DENY
                        
                        # Debug logging for financial filtering
                        print(f"Financial Filter Decision: Action={rule_result.get('action')}, Reason={rule_result.get('reason')}")
                        print(f"Is about person: {query_analysis.get('is_about_person')}, Target: {query_analysis.get('target_person')}")
                        
                        # Filter the context based on rules
                        filtered_context, context_filtered = financial_filter.filter_context(
                            context=context,
                            query_analysis=query_analysis,
                            rule_result=rule_result
                        )
                        
                        # Convert to list and sort by relevance
                        doc_sources = sorted(
                            [source for source in unique_sources.values()], 
                            key=lambda x: x.get('relevance', 0), 
                            reverse=True
                        )
                        
                        # Create a formatted citation string
                        # Only show sources if not a sensitive/financial query
                        if doc_sources and not is_restricted_query:
                            citations = "\n\n**Sources:**\n"
                            # Only show the most relevant source (limit to 1)
                            source = doc_sources[0]
                            citations += f"1. {source['title']} ({source['document_type'] if source['document_type'] else 'Document'})\n"
                        else:
                            citations = ""
                        
                        # Generate a response using OpenAI
                        from langchain_openai import ChatOpenAI
                        from langchain.schema import SystemMessage, HumanMessage
                        
                        llm = ChatOpenAI(model_name="gpt-3.5-turbo")
                        
                        # Customize system prompt based on context relevance analysis
                        system_prompt = f"You are a helpful assistant for TechConsult Inc. Answer questions based on the context below. "
                        
                        # Add confidence guidance based on relevance analysis
                        if avg_relevance < 0.2:
                            system_prompt += "The provided context may not be highly relevant to the user's query. "
                            system_prompt += "Be cautious in your response and acknowledge uncertainty when appropriate. "
                            system_prompt += "If you cannot confidently answer the question with the available information, say \"I don't have enough information about that in my knowledge base.\" "
                        else:
                            system_prompt += "If the question can't be answered using the context, say \"I don't have information about that in my knowledge base.\" "
                        
                        # Add instruction for self-data handling
                        if query_analysis.get("is_self_data_request") and query_analysis.get("is_salary_related"):
                            system_prompt += "\n\nThe user is asking about their own salary information. "
                            system_prompt += f"Their email is {user_email}. "
                            system_prompt += "ONLY provide salary information if it's specifically associated with this email. "
                        
                        # Add citation guidance
                        system_prompt += "\n\nDO NOT include citations or mention sources in your response. "
                        system_prompt += "The system will automatically add citations after your response."
                        
                        # Add context
                        system_prompt += f"\n\nContext: {filtered_context}"
                        
                        messages = [
                            SystemMessage(content=system_prompt),
                            HumanMessage(content=prompt)
                        ]
                        
                        # Get raw response from LLM
                        raw_response = llm.invoke(messages).content
                        
                        # Apply financial content filtering to response if needed
                        filtered_response, response_filtered = financial_filter.filter_response(
                            response=raw_response,
                            query_analysis=query_analysis,
                            # Add explanation if this is a self-data request that couldn't be fulfilled
                            if query_analysis.get("is_self_data_request") and query_analysis.get("is_salary_related"):
                                response = "I couldn't find salary information associated with your email address."
                            elif query_analysis.get("is_about_person") and query_analysis.get("is_salary_related"): 
