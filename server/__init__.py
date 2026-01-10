"""
FQS Flask Server - Application Factory
"""
import sys
import os

# Add parent directory to path for fqs module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from flask import Flask
from flask_cors import CORS
from .api import api_bp

def create_app():
    """Create and configure Flask app"""
    app = Flask(__name__)
    
    # Enable CORS for all routes
    CORS(app)
    
    # Register API blueprint
    app.register_blueprint(api_bp, url_prefix="/api")
    
    return app
