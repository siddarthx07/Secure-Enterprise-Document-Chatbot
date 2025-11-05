#!/usr/bin/env python3
"""
Chat Sidebar Component - Displays chat history in a sidebar similar to ChatGPT
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import List, Optional
from ui.chat_history_manager import ChatHistoryManager, ChatSession
import time

class ChatSidebar:
    """Manages the chat history sidebar interface"""
    
    def __init__(self, chat_manager: ChatHistoryManager):
        """Initialize the chat sidebar"""
        self.chat_manager = chat_manager
    
    def render_sidebar(self, user_email: str) -> Optional[str]:
        """
        Render the chat history sidebar
        
        Args:
            user_email: Email of the current user
            
        Returns:
            Selected session ID or None
        """
        with st.sidebar:
            # Fixed header with icon and new chat button
            st.markdown("""
            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                <div style="background: rgba(255,255,255,0.1); border-radius: 8px; padding: 8px; margin-right: 12px;">
                    💬
                </div>
                <h3 style="margin: 0; color: white; font-weight: 600;">Chat History</h3>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("✨ New Chat", help="Start a new conversation", key="new_chat_btn", use_container_width=True):
                return self._create_new_chat(user_email)
            
            st.markdown('<div style="height: 1px; background: rgba(255,255,255,0.2); margin: 1rem 0;"></div>', unsafe_allow_html=True)
            
            # Start scrollable chat history container
            st.markdown('<div class="chat-history-container">', unsafe_allow_html=True)
            
            # Get user's chat sessions
            sessions = self.chat_manager.get_user_sessions(user_email)
            
            if not sessions:
                st.markdown("""
                <div style="text-align: center; padding: 2rem 1rem; color: rgba(255,255,255,0.6);">
                    <div style="font-size: 2rem; margin-bottom: 1rem;">💭</div>
                    <div style="font-size: 14px; margin-bottom: 0.5rem;">No conversations yet</div>
                    <div style="font-size: 12px;">Click "New Chat" to get started!</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Close scrollable chat history container
                st.markdown('</div>', unsafe_allow_html=True)
                
                return None
            
            # Group sessions by time period
            grouped_sessions = self._group_sessions_by_time(sessions)
            
            selected_session_id = None
            
            # Render grouped sessions with modern styling
            for time_group, group_sessions in grouped_sessions.items():
                if group_sessions:  # Only show groups that have sessions
                    # Time group header with modern styling
                    st.markdown(f"""
                    <div style="color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 500; 
                                text-transform: uppercase; letter-spacing: 0.5px; margin: 1rem 0 0.5rem 0;">
                        {time_group}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    for session in group_sessions:
                        selected_session_id = self._render_session_item(session, user_email) or selected_session_id
                    
                    # Add subtle spacing between groups
                    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
            
            # Close scrollable chat history container
            st.markdown('</div>', unsafe_allow_html=True)
            
            return selected_session_id
    
    def _render_session_item(self, session: ChatSession, user_email: str) -> Optional[str]:
        """
        Render a single chat session item
        
        Args:
            session: The chat session to render
            user_email: Current user's email
            
        Returns:
            Session ID if selected, None otherwise
        """
        # Create unique keys for this session
        session_key = f"session_{session.session_id}"
        edit_key = f"edit_{session.session_id}"
        delete_key = f"delete_{session.session_id}"
        
        # Check if this session is currently being edited
        edit_mode_key = f"edit_mode_{session.session_id}"
        is_editing = st.session_state.get(edit_mode_key, False)
        
        if is_editing:
            # Edit mode with modern styling
            st.markdown("""
            <div style="background: rgba(255,255,255,0.1); border-radius: 8px; padding: 8px; margin: 4px 0;">
                <div style="color: rgba(255,255,255,0.8); font-size: 11px; margin-bottom: 4px;">✏️ Editing title</div>
            </div>
            """, unsafe_allow_html=True)
            
            new_title = st.text_input(
                "Edit title",
                value=session.title,
                key=f"title_input_{session.session_id}",
                label_visibility="collapsed",
                placeholder="Enter new title..."
            )
            
            # Save and Cancel buttons with improved styling
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Save", help="Save changes", key=f"save_{session.session_id}", use_container_width=True):
                    if new_title.strip():
                        success = self.chat_manager.update_session_title(
                            session.session_id, new_title.strip(), user_email
                        )
                        if success:
                            st.success("Title updated!")
                            time.sleep(0.5)
                    st.session_state[edit_mode_key] = False
                    st.rerun()
            with col2:
                if st.button("❌ Cancel", help="Cancel editing", key=f"cancel_{session.session_id}", use_container_width=True):
                    st.session_state[edit_mode_key] = False
                    st.rerun()
        
        else:
            # Normal mode: show session title and action buttons with modern design
            # Create a container for the session item
            session_container = st.container()
            
            with session_container:
                # Main session button with enhanced styling
                if st.button(
                    f"💬 {session.title[:35]}{'...' if len(session.title) > 35 else ''}",
                    key=session_key,
                    help=f"Last updated: {self._format_timestamp(session.updated_at)}",
                    use_container_width=True
                ):
                    # Load this session
                    st.session_state.current_session_id = session.session_id
                    st.session_state.messages = [
                        {"role": msg.role, "content": msg.content}
                        for msg in session.messages
                    ]
                    st.rerun()
                    return session.session_id
                
                # Action buttons row with improved layout
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✏️", help="Edit title", key=edit_key, use_container_width=True):
                        st.session_state[edit_mode_key] = True
                        st.rerun()
                with col2:
                    # Delete button with confirmation
                    confirm_key = f"confirm_delete_{session.session_id}"
                    if st.session_state.get(confirm_key, False):
                        if st.button("❌", help="Cancel delete", key=f"cancel_delete_{session.session_id}", use_container_width=True):
                            st.session_state[confirm_key] = False
                            st.rerun()
                    else:
                        if st.button("🗑️", help="Delete chat", key=delete_key, use_container_width=True):
                            st.session_state[confirm_key] = True
                            st.rerun()
                
                # Confirmation dialog
                if st.session_state.get(confirm_key, False):
                    st.markdown("""
                    <div style="background: rgba(255, 193, 7, 0.15); border: 1px solid rgba(255, 193, 7, 0.3); 
                                border-radius: 8px; padding: 8px; margin: 4px 0; text-align: center;">
                        <div style="color: white; font-size: 12px;">Delete this chat?</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Yes", key=f"confirm_yes_{session.session_id}", use_container_width=True):
                            success = self.chat_manager.delete_session(session.session_id, user_email)
                            if success:
                                # Clear the current session if it was the deleted one
                                if st.session_state.get("current_session_id") == session.session_id:
                                    st.session_state.current_session_id = None
                                    st.session_state.messages = []
                                st.session_state[confirm_key] = False
                                st.rerun()
                    with col2:
                        if st.button("❌ No", key=f"confirm_no_{session.session_id}", use_container_width=True):
                            st.session_state[confirm_key] = False
                            st.rerun()
                
                # Add subtle separator between sessions
                st.markdown('<div style="height: 4px;"></div>', unsafe_allow_html=True)
        
        return None
    
    def _create_new_chat(self, user_email: str) -> str:
        """
        Create a new chat session
        
        Args:
            user_email: Email of the current user
            
        Returns:
            New session ID
        """
        # Create new session
        session_id = self.chat_manager.create_new_session(user_email)
        
        # Clear current session state
        st.session_state.current_session_id = session_id
        st.session_state.messages = []
        
        # Force refresh
        st.rerun()
        
        return session_id
    
    def _group_sessions_by_time(self, sessions: List[ChatSession]) -> dict:
        """
        Group sessions by time periods (Today, Yesterday, Last 7 days, etc.)
        
        Args:
            sessions: List of chat sessions
            
        Returns:
            Dictionary with time groups as keys and session lists as values
        """
        now = datetime.now()
        today = now.date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        groups = {
            "Today": [],
            "Yesterday": [],
            "Last 7 days": [],
            "Last 30 days": [],
            "Older": []
        }
        
        for session in sessions:
            # Convert session timestamp to date
            session_date = session.updated_at.date()
            
            if session_date == today:
                groups["Today"].append(session)
            elif session_date == yesterday:
                groups["Yesterday"].append(session)
            elif session_date > week_ago:
                groups["Last 7 days"].append(session)
            elif session_date > month_ago:
                groups["Last 30 days"].append(session)
            else:
                groups["Older"].append(session)
        
        # Remove empty groups
        return {k: v for k, v in groups.items() if v}
    
    def _format_timestamp(self, timestamp: datetime) -> str:
        """
        Format timestamp for display
        
        Args:
            timestamp: The timestamp to format
            
        Returns:
            Formatted timestamp string
        """
        now = datetime.now()
        diff = now - timestamp.replace(tzinfo=None)
        
        if diff.days == 0:
            if diff.seconds < 3600:  # Less than 1 hour
                minutes = diff.seconds // 60
                return f"{minutes} minutes ago" if minutes > 1 else "Just now"
            else:  # Less than 24 hours
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return timestamp.strftime("%m/%d/%Y")
    
    def _confirm_delete(self, session_id: str) -> bool:
        """
        Show delete confirmation dialog (simplified to avoid column nesting)
        
        Args:
            session_id: ID of the session to delete
            
        Returns:
            True if confirmed, False otherwise
        """
        confirm_key = f"confirm_delete_{session_id}"
        
        # Check if already confirmed
        if st.session_state.get(confirm_key, False):
            # Reset confirmation state
            st.session_state[confirm_key] = False
            return True
        
        # Show confirmation without columns
        if st.session_state.get(f"show_confirm_{session_id}", False):
            st.warning("Are you sure you want to delete this chat?")
            
            if st.button("Yes, delete", key=f"confirm_yes_{session_id}", use_container_width=True):
                    st.session_state[confirm_key] = True
                    st.session_state[f"show_confirm_{session_id}"] = False
                    return True
            
            if st.button("Cancel", key=f"confirm_no_{session_id}", use_container_width=True):
                    st.session_state[f"show_confirm_{session_id}"] = False
                    st.rerun()
        else:
            # First click - show confirmation
            st.session_state[f"show_confirm_{session_id}"] = True
            st.rerun()
        
        return False
    
    def initialize_session_state(self, user_email: str):
        """
        Initialize session state for chat history
        
        Args:
            user_email: Email of the current user
        """
        # Initialize current session if not exists
        if "current_session_id" not in st.session_state:
            # Try to load the most recent session
            sessions = self.chat_manager.get_user_sessions(user_email, limit=1)
            if sessions:
                latest_session = sessions[0]
                st.session_state.current_session_id = latest_session.session_id
                st.session_state.messages = [
                    {"role": msg.role, "content": msg.content}
                    for msg in latest_session.messages
                ]
            else:
                # Create a new session if no history exists
                session_id = self.chat_manager.create_new_session(user_email)
                st.session_state.current_session_id = session_id
                st.session_state.messages = []
    
    def save_message_to_current_session(self, role: str, content: str, user_email: str):
        """
        Save a message to the current session
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
            user_email: Email of the current user
        """
        current_session_id = st.session_state.get("current_session_id")
        
        if current_session_id:
            # Add message to existing session
            self.chat_manager.add_message(current_session_id, role, content)
        else:
            # Create new session with this message
            session_id = self.chat_manager.create_new_session(user_email, content if role == 'user' else None)
            st.session_state.current_session_id = session_id
            
            # Add assistant message if this is an assistant response
            if role == 'assistant':
                self.chat_manager.add_message(session_id, role, content) 