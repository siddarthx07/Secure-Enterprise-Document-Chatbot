#!/usr/bin/env python3
"""
Chat History Manager - Handles storing and retrieving chat conversations from Firebase
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import firebase_admin
from firebase_admin import firestore
from dataclasses import dataclass
import streamlit as st

@dataclass
class ChatMessage:
    """Represents a single chat message"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    message_id: str = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase storage"""
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp,
            'message_id': self.message_id or str(uuid.uuid4())
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create from dictionary from Firebase"""
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=data['timestamp'],
            message_id=data.get('message_id', str(uuid.uuid4()))
        )

@dataclass
class ChatSession:
    """Represents a chat session/conversation"""
    session_id: str
    user_email: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessage]
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase storage"""
        return {
            'session_id': self.session_id,
            'user_email': self.user_email,
            'title': self.title,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'messages': [msg.to_dict() for msg in self.messages],
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatSession':
        """Create from dictionary from Firebase"""
        messages = [ChatMessage.from_dict(msg) for msg in data.get('messages', [])]
        return cls(
            session_id=data['session_id'],
            user_email=data['user_email'],
            title=data['title'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            messages=messages,
            is_active=data.get('is_active', True)
        )

class ChatHistoryManager:
    """Manages chat history storage and retrieval using Firebase Firestore"""
    
    def __init__(self):
        """Initialize the chat history manager"""
        try:
            # Initialize Firebase Admin SDK if not already initialized
            try:
                # Try to get existing app
                firebase_admin.get_app()
            except ValueError:
                # No app exists, initialize default app
                import os
                from firebase_admin import credentials
                service_account_path = os.getenv(
                    "FIREBASE_SERVICE_ACCOUNT", 
                    "./chatbot-c14e4-firebase-adminsdk-fbsvc-1cca11cb3e.json"
                )
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
            
            # Get Firestore client
            self.db = firestore.client()
            self.collection_name = "chat_sessions"
            print("✅ Chat History Manager initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Chat History Manager: {e}")
            self.db = None
    
    def create_new_session(self, user_email: str, initial_message: str = None) -> str:
        """
        Create a new chat session
        
        Args:
            user_email: Email of the user
            initial_message: Optional initial user message
            
        Returns:
            session_id: ID of the new session
        """
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Generate title from initial message or use default
        if initial_message:
            title = self._generate_title(initial_message)
        else:
            title = f"New Chat - {now.strftime('%m/%d %H:%M')}"
        
        # Create initial messages if provided
        messages = []
        if initial_message:
            messages.append(ChatMessage(
                role='user',
                content=initial_message,
                timestamp=now,
                message_id=str(uuid.uuid4())
            ))
        
        # Create session
        session = ChatSession(
            session_id=session_id,
            user_email=user_email,
            title=title,
            created_at=now,
            updated_at=now,
            messages=messages
        )
        
        # Save to Firebase
        try:
            if self.db:
                self.db.collection(self.collection_name).document(session_id).set(session.to_dict())
                print(f"✅ Created new chat session: {session_id}")
            return session_id
        except Exception as e:
            print(f"❌ Failed to create chat session: {e}")
            return session_id  # Return ID even if save fails
    
    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """
        Add a message to an existing chat session
        
        Args:
            session_id: ID of the chat session
            role: 'user' or 'assistant'
            content: Message content
            
        Returns:
            bool: Success status
        """
        try:
            if not self.db:
                return False
            
            now = datetime.now(timezone.utc)
            message = ChatMessage(
                role=role,
                content=content,
                timestamp=now,
                message_id=str(uuid.uuid4())
            )
            
            # Get current session
            doc_ref = self.db.collection(self.collection_name).document(session_id)
            doc = doc_ref.get()
            
            if doc.exists:
                session_data = doc.to_dict()
                session = ChatSession.from_dict(session_data)
                
                # Add new message
                session.messages.append(message)
                session.updated_at = now
                
                # Update title if this is the first user message
                if role == 'user' and len([m for m in session.messages if m.role == 'user']) == 1:
                    session.title = self._generate_title(content)
                
                # Save updated session
                doc_ref.set(session.to_dict())
                print(f"✅ Added message to session {session_id}")
                return True
            else:
                print(f"❌ Session {session_id} not found")
                return False
                
        except Exception as e:
            print(f"❌ Failed to add message: {e}")
            return False
    
    def get_user_sessions(self, user_email: str, limit: int = 50) -> List[ChatSession]:
        """
        Get all chat sessions for a user
        
        Args:
            user_email: Email of the user
            limit: Maximum number of sessions to return
            
        Returns:
            List of ChatSession objects
        """
        try:
            if not self.db:
                return []
            
            # Query sessions for user, ordered by updated_at descending
            # Note: This query requires a composite index in Firestore
            # For now, we'll use a simpler query and filter/sort in Python
            sessions_ref = (self.db.collection(self.collection_name)
                          .where('user_email', '==', user_email)
                          .limit(limit * 2))  # Get more to account for inactive sessions
            
            sessions = []
            for doc in sessions_ref.stream():
                session_data = doc.to_dict()
                # Filter active sessions and sort by updated_at in Python
                if session_data.get('is_active', True):
                    session = ChatSession.from_dict(session_data)
                    sessions.append(session)
            
            # Sort by updated_at descending and limit results
            sessions.sort(key=lambda x: x.updated_at, reverse=True)
            sessions = sessions[:limit]
            
            print(f"✅ Retrieved {len(sessions)} sessions for {user_email}")
            return sessions
            
        except Exception as e:
            print(f"❌ Failed to get user sessions: {e}")
            return []
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Get a specific chat session
        
        Args:
            session_id: ID of the session
            
        Returns:
            ChatSession object or None
        """
        try:
            if not self.db:
                return None
            
            doc_ref = self.db.collection(self.collection_name).document(session_id)
            doc = doc_ref.get()
            
            if doc.exists:
                session_data = doc.to_dict()
                session = ChatSession.from_dict(session_data)
                print(f"✅ Retrieved session {session_id}")
                return session
            else:
                print(f"❌ Session {session_id} not found")
                return None
                
        except Exception as e:
            print(f"❌ Failed to get session: {e}")
            return None
    
    def delete_session(self, session_id: str, user_email: str) -> bool:
        """
        Delete a chat session (soft delete by marking as inactive)
        
        Args:
            session_id: ID of the session
            user_email: Email of the user (for security)
            
        Returns:
            bool: Success status
        """
        try:
            if not self.db:
                return False
            
            doc_ref = self.db.collection(self.collection_name).document(session_id)
            doc = doc_ref.get()
            
            if doc.exists:
                session_data = doc.to_dict()
                
                # Verify user owns this session
                if session_data.get('user_email') != user_email:
                    print(f"❌ User {user_email} not authorized to delete session {session_id}")
                    return False
                
                # Soft delete by marking as inactive
                doc_ref.update({
                    'is_active': False,
                    'updated_at': datetime.now(timezone.utc)
                })
                
                print(f"✅ Deleted session {session_id}")
                return True
            else:
                print(f"❌ Session {session_id} not found")
                return False
                
        except Exception as e:
            print(f"❌ Failed to delete session: {e}")
            return False
    
    def update_session_title(self, session_id: str, new_title: str, user_email: str) -> bool:
        """
        Update the title of a chat session
        
        Args:
            session_id: ID of the session
            new_title: New title for the session
            user_email: Email of the user (for security)
            
        Returns:
            bool: Success status
        """
        try:
            if not self.db:
                return False
            
            doc_ref = self.db.collection(self.collection_name).document(session_id)
            doc = doc_ref.get()
            
            if doc.exists:
                session_data = doc.to_dict()
                
                # Verify user owns this session
                if session_data.get('user_email') != user_email:
                    print(f"❌ User {user_email} not authorized to update session {session_id}")
                    return False
                
                # Update title
                doc_ref.update({
                    'title': new_title,
                    'updated_at': datetime.now(timezone.utc)
                })
                
                print(f"✅ Updated session {session_id} title to: {new_title}")
                return True
            else:
                print(f"❌ Session {session_id} not found")
                return False
                
        except Exception as e:
            print(f"❌ Failed to update session title: {e}")
            return False
    
    def _generate_title(self, message: str, max_length: int = 50) -> str:
        """
        Generate a title from the first message
        
        Args:
            message: The message content
            max_length: Maximum length of the title
            
        Returns:
            Generated title
        """
        # Clean and truncate the message
        title = message.strip()
        
        # Remove common question words and clean up
        title = title.replace("what is", "").replace("how do", "").replace("can you", "")
        title = title.replace("tell me", "").replace("explain", "").strip()
        
        # Capitalize first letter
        if title:
            title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
        
        # Truncate if too long
        if len(title) > max_length:
            title = title[:max_length-3] + "..."
        
        # Fallback if title is empty or too short
        if len(title) < 3:
            title = f"Chat - {datetime.now().strftime('%m/%d %H:%M')}"
        
        return title
    
    def get_stats(self, user_email: str) -> Dict[str, Any]:
        """
        Get chat statistics for a user
        
        Args:
            user_email: Email of the user
            
        Returns:
            Dictionary with statistics
        """
        try:
            sessions = self.get_user_sessions(user_email, limit=1000)  # Get more for stats
            
            total_sessions = len(sessions)
            total_messages = sum(len(session.messages) for session in sessions)
            
            # Calculate average messages per session
            avg_messages = total_messages / total_sessions if total_sessions > 0 else 0
            
            # Find most recent session
            most_recent = sessions[0] if sessions else None
            
            return {
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'avg_messages_per_session': round(avg_messages, 1),
                'most_recent_session': most_recent.updated_at if most_recent else None
            }
            
        except Exception as e:
            print(f"❌ Failed to get stats: {e}")
            return {
                'total_sessions': 0,
                'total_messages': 0,
                'avg_messages_per_session': 0,
                'most_recent_session': None
            } 