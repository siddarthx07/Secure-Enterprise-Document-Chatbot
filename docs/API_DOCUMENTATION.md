# Enterprise ChatDoc - API Documentation

This document provides comprehensive API documentation for the Enterprise ChatDoc system components.

## 📋 Table of Contents

1. [Core APIs](#core-apis)
2. [Authentication APIs](#authentication-apis)
3. [Document Management APIs](#document-management-apis)
4. [Financial Filter APIs](#financial-filter-apis)
5. [Vector Database APIs](#vector-database-apis)
6. [Chat History APIs](#chat-history-apis)
7. [Admin APIs](#admin-apis)
8. [Error Handling](#error-handling)
9. [Response Formats](#response-formats)

---

## 🔧 Core APIs

### Main Application Interface

#### `core/app.py` - Streamlit Application

**Primary Functions:**

##### `main()`
- **Description**: Main application entry point
- **Parameters**: None
- **Returns**: None (Streamlit app)
- **Usage**: Entry point for the web application

##### `display_chat_interface()`
- **Description**: Renders the chat interface and handles user queries
- **Parameters**: None
- **Returns**: None
- **Flow**:
  1. Displays chat history
  2. Processes user input
  3. Performs document retrieval
  4. Applies security filtering
  5. Generates AI response
  6. Updates chat history

**Key Components Integration:**
```python
# Example chat processing flow
docs = vector_db.search(query=prompt, limit=5, user_role=role_str)
filter_result = financial_filter.process_query(query=prompt, user_email=user_email, user_role=role_str)
response = openai_client.chat.completions.create(...)
```

---

## 🔐 Authentication APIs

### `core/firebase_auth.py` - Firebase Authentication Manager

#### Class: `FirebaseAuthManager`

##### `__init__()`
```python
def __init__(self)
```
- **Description**: Initializes Firebase authentication
- **Parameters**: None
- **Returns**: FirebaseAuthManager instance

##### `login(email: str, password: str)`
```python
def login(self, email: str, password: str) -> Dict[str, Any]
```
- **Description**: Authenticates user with email and password
- **Parameters**:
  - `email` (str): User email address
  - `password` (str): User password
- **Returns**: 
  ```python
  {
      "success": bool,
      "user": {
          "uid": str,
          "email": str,
          "role": str
      },
      "error": str  # if success is False
  }
  ```

##### `register(email: str, password: str, role: str)`
```python
def register(self, email: str, password: str, role: str = "Junior") -> Dict[str, Any]
```
- **Description**: Creates new user account
- **Parameters**:
  - `email` (str): User email address
  - `password` (str): User password
  - `role` (str): User role (Junior, Senior, Manager, Admin)
- **Returns**: Same format as login()

##### `get_user_role() -> str`
```python
def get_user_role(self) -> str
```
- **Description**: Gets current user's role
- **Returns**: User role string

##### `is_authenticated() -> bool`
```python
def is_authenticated(self) -> bool
```
- **Description**: Checks if user is currently authenticated
- **Returns**: Boolean authentication status

#### Enum: `UserRole`
```python
class UserRole(Enum):
    JUNIOR = "Junior"
    SENIOR = "Senior"
    MANAGER = "Manager"
    ADMIN = "Admin"
```

---

## 📄 Document Management APIs

### `document_modules/document_manager.py` - Document Manager

#### Class: `DocumentManager`

##### `upload_document(file, filename, title, description, min_access_level, document_type, user, tags)`
```python
def upload_document(
    self,
    file: BinaryIO,
    filename: str,
    title: str,
    description: str,
    min_access_level: UserRole,
    document_type: DocumentType,
    user: Dict[str, str],
    tags: List[str] = None
) -> Dict[str, Any]
```
- **Description**: Uploads document to Firebase Storage and saves metadata
- **Parameters**:
  - `file`: Binary file object
  - `filename`: Original filename
  - `title`: Document title
  - `description`: Document description
  - `min_access_level`: Minimum role required to access
  - `document_type`: Type of document
  - `user`: User information dict
  - `tags`: Optional list of tags
- **Returns**:
  ```python
  {
      "success": bool,
      "document_id": str,
      "download_url": str,
      "error": str  # if success is False
  }
  ```

##### `get_user_documents(user_role: UserRole)`
```python
def get_user_documents(self, user_role: UserRole) -> List[Dict[str, Any]]
```
- **Description**: Retrieves documents accessible by user role
- **Parameters**:
  - `user_role`: User's role enum
- **Returns**: List of document metadata dictionaries

##### `delete_document(document_id: str, user_role: UserRole)`
```python
def delete_document(self, document_id: str, user_role: UserRole) -> Dict[str, Any]
```
- **Description**: Deletes document and associated vector embeddings
- **Parameters**:
  - `document_id`: Document identifier
  - `user_role`: User's role for permission check
- **Returns**: Deletion status dictionary

#### Enum: `DocumentType`
```python
class DocumentType(Enum):
    POLICY = "Policy"
    PROCEDURE = "Procedure"
    REPORT = "Report"
    HANDBOOK = "Handbook"
    FINANCIAL = "Financial"
    OTHER = "Other"
```

---

## 🛡️ Financial Filter APIs

### `utils/financial_filter.py` - Financial Content Filter

#### Class: `FinancialContentFilter`

##### `__init__(audit_log_enabled, use_llm_classification, use_guardrails, use_unified_analyzer)`
```python
def __init__(
    self,
    audit_log_enabled: bool = True,
    use_llm_classification: bool = True,
    use_guardrails: bool = True,
    use_unified_analyzer: bool = True
)
```
- **Description**: Initializes financial content filter with various protection layers
- **Parameters**: Configuration flags for different filtering components

##### `analyze_query(query: str, user_email: str, user_role: str)`
```python
def analyze_query(self, query: str, user_email: str, user_role: str) -> Dict[str, Any]
```
- **Description**: Analyzes query for financial content and security risks
- **Parameters**:
  - `query`: User's query string
  - `user_email`: User's email for self-data checks
  - `user_role`: User's role for access control
- **Returns**:
  ```python
  {
      "original_query": str,
      "user_email": str,
      "user_role": str,
      "is_financial": bool,
      "is_salary_related": bool,
      "is_about_person": bool,
      "target_person": str,
      "is_self_data_request": bool,
      "is_policy_context": bool,
      "is_person_salary_query": bool,
      "is_aggregate_salary_query": bool,
      "financial_keywords": List[str],
      "llm_classification": Dict,  # if LLM analysis enabled
      "unified_analysis": Dict     # if unified analyzer enabled
  }
  ```

##### `process_query(query: str, user_email: str, user_role: str, document_context: str)`
```python
def process_query(
    self,
    query: str,
    user_email: str,
    user_role: str,
    document_context: Optional[str] = None
) -> Dict[str, Any]
```
- **Description**: Complete query processing pipeline with security analysis
- **Parameters**:
  - `query`: User query
  - `user_email`: User email
  - `user_role`: User role
  - `document_context`: Retrieved document context
- **Returns**:
  ```python
  {
      "query_analysis": Dict,
      "rule_result": {
          "action": FilterAction,
          "reason": str
      },
      "audit_log": Dict  # if audit logging enabled
  }
  ```

##### `filter_response(response: str, query_analysis: Dict, rule_result: Dict)`
```python
def filter_response(
    self,
    response: str,
    query_analysis: Dict[str, Any],
    rule_result: Dict[str, Any]
) -> Tuple[str, bool]
```
- **Description**: Filters LLM response based on security rules
- **Parameters**:
  - `response`: Original LLM response
  - `query_analysis`: Query analysis results
  - `rule_result`: Access control decision
- **Returns**: `(filtered_response: str, was_filtered: bool)`

#### Enum: `FilterAction`
```python
class FilterAction(Enum):
    ALLOW = "allow"
    ALLOW_WITH_REDACTION = "allow_with_redaction"
    ALLOW_WITH_EMAIL_CHECK = "allow_with_email_check"
    ALLOW_WITH_SCREENING = "allow_with_screening"
    DENY = "deny"
```

---

## 🗄️ Vector Database APIs

### `core/database.py` - Vector Database Manager

#### Class: `VectorDatabase`

##### `__init__(db_path: str, embedding_model: str)`
```python
def __init__(self, db_path: str = "./vector_db", embedding_model: str = "text-embedding-3-small")
```
- **Description**: Initializes FAISS vector database with OpenAI embeddings
- **Parameters**:
  - `db_path`: Path to store vector database files
  - `embedding_model`: OpenAI embedding model name

##### `add_documents(documents: List[Document])`
```python
def add_documents(self, documents: List[Document]) -> None
```
- **Description**: Adds document chunks to vector database
- **Parameters**:
  - `documents`: List of LangChain Document objects with embeddings

##### `search(query: str, limit: int, user_role: str)`
```python
def search(
    self,
    query: str,
    limit: int = 5,
    user_role: str = None,
    **kwargs
) -> List[Document]
```
- **Description**: Performs similarity search with role-based filtering
- **Parameters**:
  - `query`: Search query string
  - `limit`: Maximum number of results
  - `user_role`: User role for access filtering
- **Returns**: List of relevant Document objects

##### `similarity_search(query: str, k: int, filter: Dict)`
```python
def similarity_search(
    self,
    query: str,
    k: int = 4,
    filter: Optional[Dict[str, Any]] = None
) -> List[Document]
```
- **Description**: Direct FAISS similarity search
- **Parameters**:
  - `query`: Search query
  - `k`: Number of results
  - `filter`: Metadata filter
- **Returns**: List of Document objects

##### `delete_document_chunks(document_id: str)`
```python
def delete_document_chunks(self, document_id: str) -> Dict[str, Any]
```
- **Description**: Removes all chunks for a specific document
- **Parameters**:
  - `document_id`: Document identifier
- **Returns**: Deletion status and count

---

## 💬 Chat History APIs

### `ui/chat_history_manager.py` - Chat History Manager

#### Class: `ChatHistoryManager`

##### `save_message(user_email: str, session_id: str, role: str, content: str)`
```python
def save_message(
    self,
    user_email: str,
    session_id: str,
    role: str,
    content: str,
    metadata: Dict[str, Any] = None
) -> bool
```
- **Description**: Saves chat message to Firebase Firestore
- **Parameters**:
  - `user_email`: User's email
  - `session_id`: Chat session identifier
  - `role`: Message role (user/assistant)
  - `content`: Message content
  - `metadata`: Optional metadata
- **Returns**: Success boolean

##### `get_chat_sessions(user_email: str, limit: int)`
```python
def get_chat_sessions(self, user_email: str, limit: int = 10) -> List[Dict[str, Any]]
```
- **Description**: Retrieves user's chat sessions
- **Parameters**:
  - `user_email`: User's email
  - `limit`: Maximum sessions to return
- **Returns**: List of session metadata

##### `get_session_messages(session_id: str)`
```python
def get_session_messages(self, session_id: str) -> List[ChatMessage]
```
- **Description**: Gets all messages in a chat session
- **Parameters**:
  - `session_id`: Session identifier
- **Returns**: List of ChatMessage objects

#### Class: `ChatMessage`
```python
@dataclass
class ChatMessage:
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    message_id: str = None
```

---

## 👑 Admin APIs

### `core/admin.py` - Admin Interface

#### `display_admin_interface(auth_manager: FirebaseAuthManager)`
```python
def display_admin_interface(auth_manager: FirebaseAuthManager) -> None
```
- **Description**: Renders admin dashboard for user management
- **Parameters**:
  - `auth_manager`: Firebase authentication manager
- **Functions**:
  - View all users
  - Update user roles
  - Delete users
  - Monitor system activity

#### `get_all_users() -> List[Dict[str, Any]]`
```python
def get_all_users() -> List[Dict[str, Any]]
```
- **Description**: Retrieves all system users
- **Returns**: List of user data dictionaries

#### `update_user_role(user_id: str, new_role: str) -> bool`
```python
def update_user_role(user_id: str, new_role: str) -> bool
```
- **Description**: Updates user's role
- **Parameters**:
  - `user_id`: User identifier
  - `new_role`: New role to assign
- **Returns**: Success boolean

---

## 📊 Audit & Logging APIs

### `audit_logger.py` - Audit Logger

#### Class: `AuditLogger`

##### `log_sensitive_query(audit_data: Dict[str, Any])`
```python
def log_sensitive_query(self, audit_data: Dict[str, Any]) -> bool
```
- **Description**: Logs sensitive queries for compliance
- **Parameters**:
  - `audit_data`: Query audit information
- **Returns**: Success boolean

##### `get_audit_logs(start_date: datetime, end_date: datetime)`
```python
def get_audit_logs(
    self,
    start_date: datetime,
    end_date: datetime,
    user_email: str = None
) -> List[Dict[str, Any]]
```
- **Description**: Retrieves audit logs for specified period
- **Parameters**:
  - `start_date`: Log start date
  - `end_date`: Log end date
  - `user_email`: Optional user filter
- **Returns**: List of audit log entries

---

## ⚠️ Error Handling

### Standard Error Response Format

All APIs return errors in consistent format:

```python
{
    "success": False,
    "error": str,
    "error_code": str,  # Optional error classification
    "details": Dict     # Optional additional error details
}
```

### Common Error Codes

- **AUTH_001**: Authentication failed
- **AUTH_002**: Insufficient permissions
- **DOC_001**: Document not found
- **DOC_002**: Invalid document format
- **VDB_001**: Vector database error
- **FILTER_001**: Content filtering error
- **API_001**: External API error (OpenAI)

### Exception Classes

```python
class ChatbotError(Exception):
    """Base exception for chatbot errors"""
    pass

class AuthenticationError(ChatbotError):
    """Authentication related errors"""
    pass

class DocumentError(ChatbotError):
    """Document processing errors"""
    pass

class SecurityError(ChatbotError):
    """Security and filtering errors"""
    pass
```

---

## 📋 Response Formats

### Successful Query Response
```python
{
    "response": str,              # AI-generated response
    "sources": List[Dict],        # Source documents
    "response_time": float,       # Processing time in seconds
    "filtered": bool,             # Whether response was filtered
    "filter_reason": str,         # Reason for filtering (if applicable)
    "session_id": str,           # Chat session identifier
    "audit_logged": bool         # Whether query was logged for audit
}
```

### Document Upload Response
```python
{
    "success": bool,
    "document_id": str,
    "download_url": str,
    "processing_status": str,     # "pending", "completed", "failed"
    "chunk_count": int,          # Number of text chunks created
    "vector_db_updated": bool    # Whether vector DB was updated
}
```

### User Management Response
```python
{
    "success": bool,
    "user": {
        "uid": str,
        "email": str,
        "role": str,
        "created_date": str,
        "last_login": str,
        "document_count": int,
        "query_count": int
    }
}
```

---

## 🔧 Configuration APIs

### Environment Variables

Required environment variables for API functionality:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Firebase Configuration
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_PRIVATE_KEY=your_private_key
FIREBASE_CLIENT_EMAIL=your_service_account_email

# Application Configuration
DOCUMENT_STORAGE=./documents
VECTOR_DB_PATH=./vector_db
```

### Rate Limiting

- **OpenAI API**: Respects OpenAI rate limits
- **Firebase**: Uses Firebase quotas
- **File Upload**: 200MB max file size
- **Queries**: No artificial rate limiting (controlled by underlying services)

---

## 🧪 Testing APIs

### Test Helper Functions

```python
# Test authentication
def test_auth():
    auth = FirebaseAuthManager()
    result = auth.login("test@example.com", "password")
    assert result["success"] == True

# Test document processing
def test_document_upload():
    manager = DocumentManager()
    with open("test.pdf", "rb") as f:
        result = manager.upload_document(
            file=f,
            filename="test.pdf",
            title="Test Document",
            description="Test",
            min_access_level=UserRole.JUNIOR,
            document_type=DocumentType.POLICY,
            user={"uid": "test", "email": "test@example.com", "role": "Admin"}
        )
    assert result["success"] == True

# Test financial filtering
def test_financial_filter():
    filter = FinancialContentFilter()
    result = filter.process_query(
        query="What is John's salary?",
        user_email="user@example.com",
        user_role="Junior"
    )
    assert result["rule_result"]["action"] == FilterAction.DENY
```

---

## 📚 Usage Examples

### Complete Query Processing Example

```python
# Initialize components
auth_manager = FirebaseAuthManager()
vector_db = VectorDatabase()
financial_filter = FinancialContentFilter()
chat_history = ChatHistoryManager()

# User authentication
login_result = auth_manager.login("user@company.com", "password")
if not login_result["success"]:
    return {"error": "Authentication failed"}

user_role = auth_manager.get_user_role()
user_email = login_result["user"]["email"]

# Process user query
query = "What is our vacation policy?"

# Search documents
docs = vector_db.search(query=query, limit=5, user_role=user_role)

# Apply security filtering
filter_result = financial_filter.process_query(
    query=query,
    user_email=user_email,
    user_role=user_role,
    document_context="\n".join([doc.page_content for doc in docs])
)

# Generate response (if allowed)
if filter_result["rule_result"]["action"] != FilterAction.DENY:
    # Call OpenAI API with context
    response = generate_ai_response(query, docs)
    
    # Filter response
    filtered_response, was_filtered = financial_filter.filter_response(
        response=response,
        query_analysis=filter_result["query_analysis"],
        rule_result=filter_result["rule_result"]
    )
    
    # Save to chat history
    session_id = generate_session_id()
    chat_history.save_message(user_email, session_id, "user", query)
    chat_history.save_message(user_email, session_id, "assistant", filtered_response)
    
    return {
        "response": filtered_response,
        "sources": [{"title": doc.metadata.get("title"), "type": doc.metadata.get("document_type")} for doc in docs],
        "filtered": was_filtered
    }
else:
    return {
        "response": filter_result["rule_result"]["reason"],
        "filtered": True
    }
```

---

This API documentation provides comprehensive coverage of all system components and their interfaces. For additional implementation details, refer to the source code and inline documentation. 