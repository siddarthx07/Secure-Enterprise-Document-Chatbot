# Secure Enterprise Knowledge Chatbot

An intelligent enterprise chatbot that provides secure, role-based access to company documents using advanced AI and content filtering.

##  Features

- **Role-Based Access Control**: Junior, Senior, Manager, and Admin roles with hierarchical document access
- **Intelligent Document Processing**: PDF upload, text extraction, and vector embeddings
- **Advanced Security**: Multi-layer content filtering to protect sensitive financial information
- **AI-Powered Responses**: GPT-3.5 integration with context-aware answer generation
- **Source Citations**: All responses include references to source documents
- **Audit Logging**: Comprehensive tracking of sensitive queries for compliance
- **Real-time Chat**: Persistent conversation history with Firebase backend
- **Admin Dashboard**: User and document management interface

##  Architecture

- **Frontend**: Streamlit web application
- **Backend**: Python with LangChain framework
- **Database**: Firebase Firestore + FAISS vector database
- **AI/ML**: OpenAI GPT-3.5-turbo and text-embedding-3-small
- **Authentication**: Firebase Authentication
- **Storage**: Firebase Cloud Storage for documents

##  Prerequisites

- Python 3.9 or higher
- OpenAI API key
- Firebase project with Authentication, Firestore, and Storage enabled
- Git

##  Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd legal-chain/chatbot
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the `config/` directory:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Firebase Web App Configuration
FIREBASE_API_KEY=your_firebase_api_key
FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_STORAGE_BUCKET=your_project.firebasestorage.app
FIREBASE_MESSAGING_SENDER_ID=your_sender_id
FIREBASE_APP_ID=your_app_id
FIREBASE_MEASUREMENT_ID=your_measurement_id
FIREBASE_DATABASE_URL=your_database_url

# Firebase Admin SDK Configuration
FIREBASE_TYPE=service_account
FIREBASE_PRIVATE_KEY_ID=your_private_key_id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nyour_private_key_here\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=your_service_account@your_project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your_client_id
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
FIREBASE_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
FIREBASE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/your_service_account%40your_project.iam.gserviceaccount.com
FIREBASE_UNIVERSE_DOMAIN=googleapis.com

# Vector Database Configuration
VECTOR_DB_PATH=./vector_db

# Application Configuration
AUDIT_LOG_ENABLED=true
USE_LLM_CLASSIFICATION=true
USE_GUARDRAILS=true
USE_UNIFIED_ANALYZER=true
```

**Note**: Copy the `env.example` file to `config/.env` and fill in your actual values.

### 5. Firebase Setup

1. **Create Firebase Project**:
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create a new project
   - Enable Authentication, Firestore Database, and Storage

2. **Generate Service Account Key**:
   - Go to Project Settings > Service Accounts
   - Generate new private key (JSON format)
   - Use the values to fill your `.env` file

3. **Configure Authentication**:
   - Enable Email/Password authentication
   - Add authorized domains if deploying

4. **Set up Firestore Security Rules**:
   ```javascript
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /{document=**} {
         allow read, write: if request.auth != null;
       }
     }
   }
   ```

5. **Configure Storage Rules**:
   ```javascript
   rules_version = '2';
   service firebase.storage {
     match /b/{bucket}/o {
       match /{allPaths=**} {
         allow read, write: if request.auth != null;
       }
     }
   }
   ```

### 6. Initialize Vector Database

```bash
# Create necessary directories
mkdir -p documents vector_db

# Initialize empty vector database (will be created on first document upload)
python -c "from core.database import VectorDatabase; VectorDatabase()"
```

## 🚀 Running the Application

### Development Mode

```bash
# From project root directory
streamlit run run_app.py

# Alternative methods:
streamlit run core/app.py
streamlit run main.py
```

The application will be available at `http://localhost:8501`

### Production Deployment

For production deployment on cloud platforms:

```bash
# Install additional production dependencies
pip install gunicorn

# Set production environment variables
export STREAMLIT_SERVER_PORT=8080
export STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Run with production settings
streamlit run app.py --server.port 8080 --server.address 0.0.0.0
```

## 👥 Initial Setup

### 1. Create Admin User

1. Start the application
2. Click "Sign Up" and create your first user account
3. Manually update the user's role in Firebase Firestore:
   - Go to Firestore Database
   - Find your user in the `users` collection
   - Change the `role` field to `"Admin"`

### 2. Upload Test Documents

1. Log in as Admin
2. Go to the Documents tab
3. Upload sample PDF documents with appropriate access levels:
   - **Junior**: Employee handbook, company policies
   - **Senior**: Department procedures, project guidelines
   - **Manager**: Financial reports, salary information

### 3. Test Role-Based Access

Create test users with different roles:
- **Junior**: Basic employee account
- **Manager**: Access to financial data
- **Admin**: Full system access

## 📖 Usage Guide

### For End Users

1. **Login**: Use your company email and password
2. **Upload Documents**: Use the Documents tab to upload PDFs (role permissions apply)
3. **Ask Questions**: Type questions in the chat interface
4. **View History**: Access previous conversations in the sidebar

### For Administrators

1. **User Management**: Access admin dashboard to manage user roles
2. **Document Management**: Upload, categorize, and manage document access levels
3. **Audit Logs**: Review sensitive query logs for compliance monitoring
4. **System Monitoring**: Monitor system usage and security alerts

## 🔧 Configuration

### User Roles

- **Junior**: Access to basic company documents and policies
- **Senior**: Junior access + department-specific documents
- **Manager**: Senior access + financial reports and salary data
- **Admin**: Full access + user and system management

### Document Access Levels

Documents are tagged with minimum access levels:
- **Junior**: Accessible to all users
- **Senior**: Accessible to Senior, Manager, and Admin users
- **Manager**: Accessible to Manager and Admin users only

### Security Features

- **Financial Content Filtering**: Automatically blocks salary queries between employees
- **Social Engineering Protection**: Detects and blocks authority impersonation attempts
- **Audit Logging**: Tracks all sensitive queries for compliance
- **Response Filtering**: Sanitizes responses to prevent information leakage

## Testing

### Run Basic Tests

```bash
# Test financial filter
python test_financial_filter.py

# Test vector database
python -c "from database import VectorDatabase; db = VectorDatabase(); print('Vector DB initialized successfully')"

# Test Firebase connection
python -c "from firebase_auth import FirebaseAuthManager; auth = FirebaseAuthManager(); print('Firebase connected successfully')"
```

### Test Scenarios

1. **Role-Based Access**:
   - Junior user trying to access financial data (should be blocked)
   - Manager accessing salary information (should be allowed)

2. **Content Filtering**:
   - Query: "What is John Doe's salary?" (should be blocked)
   - Query: "What is our vacation policy?" (should be allowed)

3. **Document Upload**:
   - Upload PDF with different access levels
   - Verify role-based document visibility

## 🐛 Troubleshooting

### Common Issues

1. **"OpenAI API Error"**:
   - Verify your OpenAI API key in `.env`
   - Check API quota and billing status

2. **"Firebase Authentication Failed"**:
   - Verify all Firebase environment variables
   - Check service account permissions
   - Ensure Firebase project is properly configured

3. **"Vector Database Error"**:
   - Ensure `vector_db` directory exists and is writable
   - Check OpenAI embeddings API access

4. **"Document Upload Failed"**:
   - Verify Firebase Storage rules
   - Check file size limits (200MB default)
   - Ensure proper authentication

### Debug Mode

Enable debug logging by setting:

```bash
export STREAMLIT_LOGGER_LEVEL=debug
```

### Performance Issues

- Large documents may take time to process
- Vector database searches improve with more documents
- Consider increasing Streamlit server memory limits for large deployments

## 📊 Monitoring

### Audit Logs

Monitor sensitive queries in Firebase Firestore under the `sensitive_query_logs` collection.

### Performance Metrics

- Response times are logged for each query
- Document processing times tracked
- User activity patterns available in chat history

## 🔐 Security Considerations

### Production Security

1. **Environment Variables**: Never commit `.env` files to version control
2. **API Keys**: Rotate OpenAI and Firebase keys regularly
3. **Database Rules**: Implement strict Firestore security rules
4. **HTTPS**: Always use HTTPS in production
5. **Access Logs**: Monitor and audit all system access

### Data Privacy

- Employee salary information is strictly protected
- All queries are logged for audit purposes
- Document access is role-based and logged
- User sessions are managed securely



