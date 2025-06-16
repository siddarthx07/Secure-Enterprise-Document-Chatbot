"""
TechConsult Inc Knowledge Chatbot

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
    st.title("TechConsult Inc Knowledge Chatbot")
    
    # Add custom CSS for better chat history styling
    st.markdown("""
    <style>
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Chat history buttons */
    .stButton > button {
        width: 100%;
        text-align: left;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        background-color: white;
        padding: 8px 12px;
        margin: 2px 0;
        font-size: 14px;
        color: #333;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background-color: #f0f0f0;
        border-color: #d0d0d0;
    }
    
    /* New chat button styling */
    .stButton > button[title="New Chat"] {
        background-color: #007bff;
        color: white;
        border-color: #007bff;
        font-weight: bold;
    }
    
    .stButton > button[title="New Chat"]:hover {
        background-color: #0056b3;
        border-color: #0056b3;
    }
    
    /* Action buttons (edit, delete) */
    .stButton > button[title="Edit title"],
    .stButton > button[title="Delete chat"] {
        width: auto;
        min-width: 30px;
        padding: 4px 8px;
        font-size: 12px;
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
    
    /* Sidebar sections */
    .sidebar-section {
        margin-bottom: 20px;
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
    prompt = st.chat_input("Ask a question about TechConsult documents")
    
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
                        
                        # Re-run financial content filtering with actual document context
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
                        system_prompt = f"You are a helpful assistant for TechConsult Inc. Answer questions based on the context below. "
                        
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
