"""
Audit logging utility for Enterprise ChatDoc

Provides functionality to log sensitive queries and access attempts
for compliance and security purposes.
"""

import firebase_admin
from firebase_admin import firestore
from datetime import datetime
from typing import Dict, Any, Optional


class AuditLogger:
    """
    Records audit logs for sensitive operations, particularly financial
    data access attempts.
    """
    
    def __init__(self, collection_name: str = "sensitive_query_logs"):
        """
        Initialize the audit logger
        
        Args:
            collection_name: Firestore collection to store logs in
        """
        self.db = firestore.client()
        self.collection_name = collection_name
    
    def log_sensitive_query(self, log_data: Dict[str, Any]) -> Optional[str]:
        """
        Record a sensitive query to the audit log
        
        Args:
            log_data: Dictionary with audit details
            
        Returns:
            ID of the created log entry, or None if failed
        """
        try:
            # Ensure timestamp exists
            if "timestamp" not in log_data:
                log_data["timestamp"] = datetime.now()
                
            # Add to Firestore
            doc_ref = self.db.collection(self.collection_name).add(log_data)
            return doc_ref[1].id
        except Exception as e:
            print(f"Error logging sensitive query: {str(e)}")
            return None
    
    def get_logs_for_user(self, user_email: str, limit: int = 100) -> list:
        """
        Retrieve audit logs for a specific user
        
        Args:
            user_email: Email of the user to get logs for
            limit: Maximum number of logs to retrieve
            
        Returns:
            List of log entries
        """
        try:
            query = (self.db.collection(self.collection_name)
                    .where("user_email", "==", user_email)
                    .order_by("timestamp", direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            logs = []
            for doc in query.stream():
                log_entry = doc.to_dict()
                log_entry["id"] = doc.id
                logs.append(log_entry)
            
            return logs
        except Exception as e:
            print(f"Error retrieving logs: {str(e)}")
            return []
    
    def get_recent_logs(self, limit: int = 100) -> list:
        """
        Retrieve recent audit logs for all users
        
        Args:
            limit: Maximum number of logs to retrieve
            
        Returns:
            List of log entries ordered by timestamp
        """
        try:
            query = (self.db.collection(self.collection_name)
                    .order_by("timestamp", direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            logs = []
            for doc in query.stream():
                log_entry = doc.to_dict()
                log_entry["id"] = doc.id
                logs.append(log_entry)
            
            return logs
        except Exception as e:
            print(f"Error retrieving logs: {str(e)}")
            return []
