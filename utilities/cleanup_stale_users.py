import os
import firebase_admin
from firebase_admin import credentials, auth, firestore
import json

# Initialize Firebase Admin SDK
def initialize_firebase():
    try:
        service_account_path = os.getenv(
            "FIREBASE_SERVICE_ACCOUNT", 
            "./chatbot-c14e4-firebase-adminsdk-fbsvc-1cca11cb3e.json"
        )
        cred = credentials.Certificate(service_account_path)
        
        # Check if any Firebase app is already initialized
        try:
            return firebase_admin.get_app()
        except ValueError:
            # No app exists, initialize default app
            return firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Failed to initialize Firebase Admin SDK: {str(e)}")
        return None

# Clean up stale user records that exist in Firestore but not in Firebase Auth
def cleanup_stale_users():
    app = initialize_firebase()
    if not app:
        return "Failed to initialize Firebase"
    
    db = firestore.client()
    
    # Get all users from Firestore
    firestore_users = db.collection('users').stream()
    
    cleaned_count = 0
    stale_users = []
    
    for user_doc in firestore_users:
        user_id = user_doc.id
        user_data = user_doc.to_dict()
        email = user_data.get('email')
        
        try:
            # Check if user exists in Firebase Auth
            auth.get_user(user_id)
            # If the above doesn't throw an error, the user exists in Auth
        except firebase_admin.exceptions.NotFoundError:
            # User doesn't exist in Auth but exists in Firestore - stale record
            print(f"Found stale user: {email} ({user_id}) - removing from Firestore")
            stale_users.append(f"{email} ({user_id})")
            
            # Delete from Firestore
            db.collection('users').document(user_id).delete()
            cleaned_count += 1
    
    if cleaned_count > 0:
        print(f"\nCleaned up {cleaned_count} stale user records:")
        for user in stale_users:
            print(f"- {user}")
        return f"Cleaned up {cleaned_count} stale user records"
    else:
        print("No stale user records found")
        return "No stale user records found"

if __name__ == "__main__":
    result = cleanup_stale_users()
    print(f"\nResult: {result}")
