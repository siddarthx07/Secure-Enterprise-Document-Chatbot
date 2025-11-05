#!/usr/bin/env python3
"""
Main entry point for TechConsult Inc Knowledge Chatbot

This script starts the Streamlit application.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import and run the main app
try:
    from core.app import main
    
    if __name__ == "__main__":
        main()
        
except Exception as e:
    print(f"Error starting application: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    raise 