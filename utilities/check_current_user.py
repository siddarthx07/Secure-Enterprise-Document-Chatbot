import os
import firebase_admin
from firebase_admin import credentials, auth, firestore
import json
import streamlit as st

def check_current_user():
    # Check if a streamlit session state file exists
    try:
        # Print the session state from the Streamlit app
        print("Session state information (if available):")
        st_path = os.path.join(os.path.expanduser("~"), ".streamlit/config.toml")
        if os.path.exists(st_path):
            print(f"Streamlit config exists at: {st_path}")
        
        # Check if Firebase Admin SDK is initialized and get all users
        try:
            try:
                app = firebase_admin.get_app()
            except ValueError:
                # Initialize Firebase if not already done
                service_account_path = os.getenv(
                    "FIREBASE_SERVICE_ACCOUNT", 
                    "./chatbot-c14e4-firebase-adminsdk-fbsvc-1cca11cb3e.json"
                )
                cred = credentials.Certificate(service_account_path)
                app = firebase_admin.initialize_app(cred)

            # List all users
            print("\nAttempting to list Firebase users:")
            page = auth.list_users()
            for user in page.users:
                print(f"Found user: {user.uid} ({user.email})")
                
            if not page.users:
                print("No users found in Firebase Authentication.")
        except Exception as e:
            print(f"Error accessing Firebase: {str(e)}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_current_user()
