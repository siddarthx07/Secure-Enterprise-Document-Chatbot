#!/usr/bin/env python3
"""
Startup script for TechConsult Inc Knowledge Chatbot

Run this script from the project root directory to start the Streamlit application.
Usage: streamlit run run_app.py
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import and run the main app
if __name__ == "__main__":
    # Change to the project root directory
    os.chdir(current_dir)
    
    # Import the main function
    from core.app import main
    
    # Run the main app
    main() 