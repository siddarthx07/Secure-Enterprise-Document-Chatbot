# SecureKnowledge AI - Startup Guide

## 🚀 How to Run the Application

After the recent directory reorganization, there are multiple ways to start the application:

### ✅ **Recommended Method (From Project Root)**
```bash
# Navigate to the project root directory
cd /path/to/chatbot

# Run the application
streamlit run run_app.py
```

### 🔧 **Alternative Methods**

#### Method 1: Using the main entry point
```bash
streamlit run main.py
```

#### Method 2: Direct core app execution
```bash
streamlit run core/app.py
```

## 📁 **Updated Directory Structure**

The project has been reorganized for better maintainability:

```
chatbot/
├── config/              # Configuration files
│   ├── .env
│   ├── firebase_config.json
│   └── firebase-adminsdk.json
├── core/                # Core application modules
│   ├── app.py          # Main Streamlit application
│   ├── database.py     # Vector database management
│   ├── firebase_auth.py # Authentication
│   └── admin.py        # Admin interface
├── document_modules/    # Document processing
├── llm_modules/        # LLM integration
├── ui/                 # User interface components
├── utils/              # Utilities and filters
├── vector_db/          # Vector database storage
├── docs/               # Documentation
├── tests/              # Test results
├── requirements/       # Dependencies
├── run_app.py          # Recommended startup script
└── main.py            # Alternative entry point
```

## 🔧 **Import Resolution**

The application now includes proper Python path setup to resolve module imports regardless of how it's started. This ensures compatibility with:

- Direct Streamlit execution
- IDE debugging
- Docker deployments
- Production hosting

## 📝 **Environment Setup**

### **Option 1: Environment Variables (Recommended)**

Configure your environment variables in `config/.env`:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

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

### **Option 2: JSON Files (Legacy)**

If you prefer using JSON files, place them in the `config/` directory:
- `firebase-adminsdk.json` (service account key)
- `firebase_config.json` (web app config)

## 🎯 **Quick Start**

1. **Install dependencies:**
   ```bash
   pip install -r requirements/requirements.txt
   ```

2. **Configure environment:**
   - Copy `env.example` to `config/.env` and fill in your values
   - OR place Firebase JSON files in `config/` directory

3. **Run the application:**
   ```bash
   streamlit run run_app.py
   ```

## 🐛 **Troubleshooting**

### Module Import Errors
If you encounter `ModuleNotFoundError`, ensure you're running from the project root directory and using one of the recommended startup methods.

### Environment File Not Found
Make sure your `.env` file is located in the `config/` directory, not the project root. Copy `env.example` to `config/.env` and fill in your values.

### Firebase Configuration Issues
The application now supports both environment variables and JSON files:
- **Recommended**: Use environment variables in `config/.env`
- **Legacy**: Place JSON files in `config/` directory:
  - `firebase-adminsdk.json` (service account key)
  - `firebase_config.json` (web app config) 