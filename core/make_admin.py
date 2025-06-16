import os
import firebase_admin
from firebase_admin import credentials, auth, firestore
import json

# Initialize Firebase Admin SDK
def initialize_firebase():
    try:
        service_account_path = os.getenv(
            "FIREBASE_SERVICE_ACCOUNT", 
            ""
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

# Make a user admin by email
def make_user_admin(email):
    app = initialize_firebase()
    if not app:
        return False, "Failed to initialize Firebase"
    
    db = firestore.client()
    
    try:
        # Get user by email
        user = auth.get_user_by_email(email)
        user_id = user.uid
        
        # Set custom claims (this is what determines the role in Firebase Auth)
        auth.set_custom_user_claims(user_id, {"role": "Admin"})
        
        # Update user document in Firestore
        db.collection('users').document(user_id).set({
            "email": email,
            "role": "Admin"
        }, merge=True)
        
        print(f"Successfully updated user {email} to Admin role!")
        return True, f"User {email} is now an Admin"
    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return False, str(e)

if __name__ == "__main__":
    email = input("Enter the email address to promote to Admin: ")
    success, message = make_user_admin(email)
    print(message)
