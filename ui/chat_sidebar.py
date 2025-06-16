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
            # Header with new chat button
            st.markdown("### 💬 Chat History")
            if st.button("➕ New Chat", help="Start a new conversation", key="new_chat_btn", use_container_width=True):
                return self._create_new_chat(user_email)
            
            st.markdown("---")
            
            # Get user's chat sessions
            sessions = self.chat_manager.get_user_sessions(user_email)
            
            if not sessions:
                st.markdown("*No chat history yet*")
                st.markdown("Start a new conversation!")
                return None
            
            # Group sessions by time period
            grouped_sessions = self._group_sessions_by_time(sessions)
            
            selected_session_id = None
            
            # Render grouped sessions
            for time_group, group_sessions in grouped_sessions.items():
                if group_sessions:  # Only show groups that have sessions
                    st.markdown(f"**{time_group}**")
                    
                    for session in group_sessions:
                        selected_session_id = self._render_session_item(session, user_email) or selected_session_id
                    
                    st.markdown("")  # Add spacing between groups
            
            # Footer - removed stats as requested
            
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
            # Edit mode: show text input and save/cancel buttons
            new_title = st.text_input(
                "Edit title",
                value=session.title,
                key=f"title_input_{session.session_id}",
                label_visibility="collapsed"
            )
            
            # Save and Cancel buttons in separate rows to avoid column nesting
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
            
            if st.button("❌ Cancel", help="Cancel editing", key=f"cancel_{session.session_id}", use_container_width=True):
                st.session_state[edit_mode_key] = False
                st.rerun()
        
        else:
            # Normal mode: show session title and action buttons
            # Session button with title
            if st.button(
                session.title,
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
            
            # Action buttons in separate rows to avoid column issues
            if st.button("✏️ Edit", help="Edit title", key=edit_key, use_container_width=True):
                st.session_state[edit_mode_key] = True
                st.rerun()
            
            # Delete button with confirmation
            confirm_key = f"confirm_delete_{session.session_id}"
            if st.session_state.get(confirm_key, False):
                # Show confirmation buttons
                st.warning("⚠️ Delete this chat?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Yes", key=f"confirm_yes_{session.session_id}", use_container_width=True):
                        success = self.chat_manager.delete_session(session.session_id, user_email)
                        if success:
                            st.success("Chat deleted!")
                            # Clear the current session if it was the deleted one
                            if st.session_state.get("current_session_id") == session.session_id:
                                st.session_state.current_session_id = None
                                st.session_state.messages = []
                            st.session_state[confirm_key] = False  # Reset confirmation
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Failed to delete chat")
                        st.session_state[confirm_key] = False
                with col2:
                    if st.button("❌ No", key=f"confirm_no_{session.session_id}", use_container_width=True):
                        st.session_state[confirm_key] = False
                        st.rerun()
            else:
                # Show delete button
                if st.button("🗑️ Delete", help="Delete chat", key=delete_key, use_container_width=True):
                    st.session_state[confirm_key] = True
                    st.rerun()
        
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