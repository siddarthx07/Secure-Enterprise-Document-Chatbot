"""
SecureKnowledge AI

Streamlit application for document upload and chatbot interface.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to Python path for module imports
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from dotenv import load_dotenv
from typing import Dict, Any

from document_modules.document_processor import DocumentProcessor
from core.database import VectorDatabase
from core.firebase_auth import FirebaseAuthManager, UserRole
from core.admin import display_admin_interface
from document_modules.document_manager import DocumentManager
from document_modules.document_ui import display_document_upload, display_document_list, display_admin_document_management
from utils.financial_filter import FinancialContentFilter, FilterAction
from utils.audit_logger import AuditLogger
from ui.chat_history_manager import ChatHistoryManager
from ui.chat_sidebar import ChatSidebar

# Load environment variables
load_dotenv(project_root / "config" / ".env")

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
chat_history_manager = ChatHistoryManager()
chat_sidebar = ChatSidebar(chat_history_manager)

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
    # Create centered header section
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1 style="font-size: 3.5rem; font-weight: 700; margin: 0; padding: 0; line-height: 1.1;
                       color: white;">
                SecureKnowledge AI
            </h1>
            <p style="font-size: 1.2rem; color: rgba(255,255,255,0.8); font-weight: 400; 
                      margin: 0.5rem 0 0 0; padding: 0; line-height: 1.4;">
                Enterprise Internal Knowledge Management System
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Add modern CSS for enhanced chat history styling
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global sidebar styling */
    .css-1d391kg, .css-1cypcdb, .css-17eq0hr {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        overflow: hidden !important;
        position: relative !important;
    }
    
    /* Sidebar content container */
    .css-1d391kg .block-container {
        padding-top: 1rem !important;
        padding-bottom: 80px !important;
        height: 100vh !important;
        display: flex !important;
        flex-direction: column !important;
    }
    
    /* Chat history scrollable container */
    .chat-history-container {
        flex: 1 !important;
        overflow-y: auto !important;
        padding-right: 8px !important;
        margin-bottom: 1rem !important;
    }
    
    
    
    /* Chat history header */
    .sidebar h3 {
        color: white !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        margin-bottom: 1rem !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    /* New Chat button - Primary CTA */
    .stButton > button[data-testid*="new_chat"] {
        width: 100% !important;
        background: rgba(255,255,255,0.15) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        backdrop-filter: blur(10px) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
        margin-bottom: 1rem !important;
    }
    
    .stButton > button[data-testid*="new_chat"]:hover {
        background: rgba(255,255,255,0.25) !important;
        border-color: rgba(255,255,255,0.3) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    }
    
    /* Time group headers */
    .sidebar .markdown-text-container p strong {
        color: rgba(255,255,255,0.8) !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        margin-bottom: 8px !important;
        display: block !important;
    }
    
    /* Chat session buttons */
    .stButton > button[data-testid*="session_"] {
        width: 100% !important;
        background: rgba(255,255,255,0.08) !important;
        color: rgba(255,255,255,0.9) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 8px !important;
        padding: 10px 12px !important;
        margin: 2px 0 !important;
        font-size: 13px !important;
        font-weight: 400 !important;
        text-align: left !important;
        transition: all 0.2s ease !important;
        backdrop-filter: blur(5px) !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
    }
    
    .stButton > button[data-testid*="session_"]:hover {
        background: rgba(255,255,255,0.15) !important;
        border-color: rgba(255,255,255,0.2) !important;
        transform: translateX(2px) !important;
    }
    
    /* Action buttons (edit, delete) */
    .stButton > button[data-testid*="edit_"],
    .stButton > button[data-testid*="delete_"] {
        width: 100% !important;
        background: rgba(255,255,255,0.05) !important;
        color: rgba(255,255,255,0.7) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 6px !important;
        padding: 6px 10px !important;
        margin: 1px 0 !important;
        font-size: 11px !important;
        font-weight: 400 !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button[data-testid*="edit_"]:hover {
        background: rgba(52, 152, 219, 0.2) !important;
        border-color: rgba(52, 152, 219, 0.3) !important;
        color: white !important;
    }
    
    .stButton > button[data-testid*="delete_"]:hover {
        background: rgba(231, 76, 60, 0.2) !important;
        border-color: rgba(231, 76, 60, 0.3) !important;
        color: white !important;
    }
    
    /* Confirmation buttons */
    .stButton > button[data-testid*="confirm_yes_"] {
        background: rgba(46, 204, 113, 0.2) !important;
        color: white !important;
        border: 1px solid rgba(46, 204, 113, 0.3) !important;
    }
    
    .stButton > button[data-testid*="confirm_no_"] {
        background: rgba(231, 76, 60, 0.2) !important;
        color: white !important;
        border: 1px solid rgba(231, 76, 60, 0.3) !important;
    }
    
    /* Text input in edit mode */
    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.1) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 6px !important;
        font-size: 13px !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: rgba(255,255,255,0.4) !important;
        box-shadow: 0 0 0 2px rgba(255,255,255,0.1) !important;
    }
    
    /* Warning messages */
    .stAlert > div {
        background: rgba(255, 193, 7, 0.15) !important;
        border: 1px solid rgba(255, 193, 7, 0.3) !important;
        color: white !important;
        border-radius: 8px !important;
    }
    
    /* Success messages */
    .stSuccess > div {
        background: rgba(46, 204, 113, 0.15) !important;
        border: 1px solid rgba(46, 204, 113, 0.3) !important;
        color: white !important;
        border-radius: 8px !important;
    }
    
    /* Dividers */
    .sidebar hr {
        border-color: rgba(255,255,255,0.2) !important;
        margin: 1rem 0 !important;
    }
    
    /* Scrollbar styling for chat history container */
    .chat-history-container::-webkit-scrollbar {
        width: 6px;
    }
    
    .chat-history-container::-webkit-scrollbar-track {
        background: rgba(255,255,255,0.1);
        border-radius: 3px;
    }
    
    .chat-history-container::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,0.3);
        border-radius: 3px;
    }
    
    .chat-history-container::-webkit-scrollbar-thumb:hover {
        background: rgba(255,255,255,0.5);
    }
    
    /* Chat input styling */
    .stChatFloatingInputContainer {
        position: fixed;
        bottom: 20px;
        z-index: 999;
        width: calc(100% - 80px);
    }
    
    .main > div:last-child {
        padding-bottom: 100px;
    }
    
    /* Main app background */
    .main .block-container {
        background-color: #0e1117 !important;
    }
    
    /* Authentication form styling */
    .stTextInput > div > div > input[type="password"] {
        padding-right: 50px !important;
        background-color: #0e1117 !important;
        border: 1px solid #464853 !important;
        border-radius: 8px !important;
        color: white !important;
    }
    
    .stTextInput > div > div > input[type="password"]:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2) !important;
    }
    
    /* Fix password input container */
    .stTextInput > div > div {
        position: relative !important;
    }
    
    /* Style the eye icon button */
    .stTextInput button[title="Show password"] {
        position: absolute !important;
        right: 8px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        background: transparent !important;
        border: none !important;
        color: #888 !important;
        padding: 4px !important;
        z-index: 10 !important;
    }
    
    .stTextInput button[title="Show password"]:hover {
        color: #667eea !important;
        background: rgba(102, 126, 234, 0.1) !important;
        border-radius: 4px !important;
    }
    
    /* Authentication header styling */
    .stTabs [data-baseweb="tab-list"] {
        background: #1a1d23 !important;
        border-radius: 8px !important;
        padding: 4px !important;
        border: 1px solid #464853 !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: rgba(255,255,255,0.7) !important;
        border-radius: 6px !important;
        padding: 8px 16px !important;
        margin: 0 2px !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: rgba(255,255,255,0.1) !important;
        color: white !important;
    }
    
    /* Form styling */
    .stForm {
        background: #1a1d23 !important;
        border: 1px solid #464853 !important;
        border-radius: 12px !important;
        padding: 20px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
    }
    
    /* Form button styling */
    .stForm button[type="submit"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    .stForm button[type="submit"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3) !important;
    }
    
    /* Text input styling for auth forms */
    .stTextInput > div > div > input {
        background-color: #0e1117 !important;
        border: 1px solid #464853 !important;
        border-radius: 8px !important;
        color: white !important;
        padding: 12px 16px !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2) !important;
        background-color: #1a1d29 !important;
    }
    
    /* Label styling */
    .stTextInput > label {
        color: rgba(255,255,255,0.9) !important;
        font-weight: 500 !important;
        margin-bottom: 8px !important;
    }
    
    /* Remove default margins from Streamlit columns */
    .stColumn {
        padding: 0 !important;
    }
    
    /* Ensure centered content stays centered */
    [data-testid="column"] > div {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    
    /* Hide header anchor links and remove their space */
    .main h1 a,
    .main h2 a,
    .main h3 a,
    .main h4 a,
    .main h5 a,
    .main h6 a {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Hide all anchor link icons */
    a[href^="#"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Remove space from header containers */
    .main h1,
    .main h2,
    .main h3 {
        line-height: 1.2 !important;
    }
    
    /* Alternative - hide the link icon specifically */
    .css-1v0mbdj,
    .css-10trblm,
    [data-testid="StyledLinkIconContainer"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
    }
    
    /* Ensure main container is centered */
    .main .block-container {
        max-width: 100% !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    
    /* Info message styling */
    .stAlert[data-baseweb="notification"] p {
        font-size: 1.4rem !important;
        font-weight: 500 !important;
        text-align: center !important;
        color: rgba(255,255,255,0.9) !important;
        margin: 0 !important;
    }
    
    .stAlert[data-baseweb="notification"] {
        background: rgba(102, 126, 234, 0.1) !important;
        border: 1px solid rgba(102, 126, 234, 0.3) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        margin: 2rem 0 !important;
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
        .css-1d391kg {
            width: 100% !important;
        }
        
        .stChatFloatingInputContainer {
            width: calc(100% - 40px) !important;
        }
        
        .main h1 {
            font-size: 2.5rem !important;
        }
        
        .stAlert[data-baseweb="notification"] p {
            font-size: 1.2rem !important;
        }
    }
    </style>
    
    """, unsafe_allow_html=True)
    
    # Handle authentication and chat history in sidebar
    if auth_manager.is_authenticated():
        user_email = st.session_state.user_info.get("email", "")
        
        # Initialize chat history session state
        chat_sidebar.initialize_session_state(user_email)
        
        # Render chat history sidebar
        selected_session = chat_sidebar.render_sidebar(user_email)
        
        # Handle session selection
        if selected_session:
            st.session_state.current_session_id = selected_session
        
        # Authentication info at bottom of sidebar
        with st.sidebar:
            st.markdown("---")
            handle_authentication()
            
            # Admin panel link (only for Admin users)
            if auth_manager.get_user_role() == UserRole.ADMIN.value:
                st.divider()
                st.header("Admin Panel")
                if st.button("Open Admin Dashboard"):
                    st.session_state.show_admin = True
    else:
        # Sidebar for authentication only when not logged in
        with st.sidebar:
            handle_authentication()
    
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
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input (will be positioned at the bottom via CSS)
    prompt = st.chat_input("Ask a question about your documents")
    
    # Handle prompt if entered
    if prompt:
        # Get user email for chat history
        user_email = st.session_state.user_info.get("email", "")
        
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Save user message to chat history
        chat_sidebar.save_message_to_current_session("user", prompt, user_email)
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # If the user greets, respond with their email and skip further processing
        greetings = ["hi", "hello", "hey", "hi there", "hello there"]
        if prompt.strip().lower() in greetings:
            assistant_response = f"Hello, {user_email}! How can I help you today?"
            # Store assistant response
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            
            # Save assistant response to chat history
            chat_sidebar.save_message_to_current_session("assistant", assistant_response, user_email)
            
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
                    
                    # Get user email for filtering and search enhancement
                    user_email = st.session_state.user_info.get("email", "")
                    
                    # Simple document retrieval - no complex logic
                    docs = vector_db.search(
                        query=prompt,
                        limit=5,
                        user_role=role_str
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
                        
                        # run financial content filtering with actual document context
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
                        
                        # Generate a response using OpenAI
                        from langchain_openai import ChatOpenAI
                        from langchain.schema import SystemMessage, HumanMessage
                        
                        llm = ChatOpenAI(model_name="gpt-3.5-turbo")
                        
                        # Customize system prompt based on context relevance analysis
                        system_prompt = f"You are a helpful assistant for SecureKnowledge AI. Answer questions based on the context below. "
                        
                        # Add confidence guidance based on relevance analysis
                        if avg_relevance < 0.25:
                            system_prompt += "The provided context may not be highly relevant to the user's query. "
                            system_prompt += "Be cautious in your response and acknowledge uncertainty when appropriate. "
                            system_prompt += "If you cannot confidently answer the question with the available information, say \"I don't have enough information about that in my knowledge base.\" "
                            system_prompt += "Only use information from the context if it directly relates to the question. "
                        else:
                            system_prompt += "If the question can't be answered using the context, say \"I don't have information about that in my knowledge base.\" "
                            system_prompt += "Only reference information that is directly relevant to the user's question. "
                        
                        # Add citation guidance
                        system_prompt += "\n\nDO NOT include citations or mention sources in your response. "
                        system_prompt += "The system will automatically add citations after your response."
                        
                        # Add the full context
                        system_prompt += f"\n\nFULL CONTEXT: {filtered_context}"
                        
                        messages = [
                            SystemMessage(content=system_prompt),
                            HumanMessage(content=prompt)
                        ]
                        
                        # Get raw response from LLM
                        raw_response = llm.invoke(messages).content
                        
                        # Now check if the response actually uses the retrieved context (SIMPLIFIED)
                        citations = ""
                        
                        # 🔧 SIMPLIFIED CITATION LOGIC: Show citation if we have sources and query isn't restricted
                        if doc_sources and not is_restricted_query:
                            # Check if response contains meaningful content (not just generic failure messages)
                            generic_failure_responses = [
                                "i don't have information about that in my knowledge base",
                                "i don't have enough information about that in my knowledge base",
                                "i encountered an error"
                            ]
                            
                            is_failure_response = any(phrase in raw_response.lower() for phrase in generic_failure_responses)
                            
                            # If it's not a failure response and we have sources, show citation
                            if not is_failure_response and len(raw_response.strip()) > 50:  # Meaningful response length
                                # Show only 1 source (most relevant) as requested
                                top_source = doc_sources[0]
                                citations = f"\n\n**Source:** {top_source['title']}"
                                if top_source.get('document_type') and top_source['document_type'] != 'Document':
                                    citations += f" ({top_source['document_type']})"
                        
                        # Apply financial content filtering to response if needed
                        filtered_response, response_filtered = financial_filter.filter_response(
                            response=raw_response,
                            query_analysis=query_analysis,
                            rule_result=rule_result
                        )
                        
                        # Determine the appropriate response based on filter rules
                        if rule_result.get("action") == FilterAction.DENY:
                            # For denied queries, enforce restriction message
                            response = rule_result.get("reason", "I'm sorry, but you don't have permission to access this information based on your role.")
                        else:
                            # For allowed queries, use the filtered response
                            response = filtered_response
                            
                            # Add warning if content was redacted
                            if response_filtered:
                                response += "\n\nNote: Some specific financial figures have been redacted based on your access level."
                            
                            # Add citations to the response if we have sources and not restricted
                            if citations and not is_restricted_query:
                                response += citations
                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")
                    response = f"I encountered an error while processing your question. Error: {str(e)}"
                
            # Display the response
            message_placeholder.markdown(response)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Save assistant response to chat history
        chat_sidebar.save_message_to_current_session("assistant", response, user_email)

if __name__ == "__main__":
    # Initialize "show_admin" flag in session state
    if "show_admin" not in st.session_state:
        st.session_state.show_admin = False
        
    main()
