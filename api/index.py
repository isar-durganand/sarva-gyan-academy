"""
Vercel Serverless Function Entry Point
"""
import sys
import os

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

# Create the Flask application
app = create_app()

# Vercel expects 'app' to be the WSGI application
