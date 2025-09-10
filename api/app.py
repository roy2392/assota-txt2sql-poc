import sys
import os

# Add parent directory to path so we can import the main app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the main app
from app import app as application

# Vercel expects 'app' to be the Flask application
app = application