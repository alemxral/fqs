"""
FQS Flask Server - Application Factory
"""
import sys
import os
import logging

# Add parent directory to path for fqs module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from flask import Flask
from flask_cors import CORS
from .api import api_bp
from .command_routes import command_bp, set_command_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask app"""
    app = Flask(__name__)
    
    # Enable CORS for all routes
    CORS(app)
    
    # Register API blueprint
    app.register_blueprint(api_bp, url_prefix="/api")
    
    # Register command execution blueprint
    app.register_blueprint(command_bp)
    
    # Initialize command manager for standalone Flask backend
    try:
        from fqs.managers.commands_manager import CommandsManager
        import threading
        
        # Create minimal core instance for command execution
        logger.info("Initializing command manager for Flask backend...")
        
        # Create a simple namespace object to hold core managers
        class CoreContainer:
            def __init__(self):
                from fqs.core.orders import OrdersCore
                from fqs.core.wallet import WalletCore
                self.orders_manager = OrdersCore()
                self.wallet_manager = WalletCore()
        
        core = CoreContainer()
        
        # Create command manager with core
        command_manager = CommandsManager(core=core)
        
        # Container for the event loop (mutable so thread can set it)
        loop_container = {'loop': None}
        
        def run_manager_loop():
            """Run the command manager in its own event loop"""
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop_container['loop'] = loop
            
            # Start the command manager
            loop.run_until_complete(command_manager.start())
            
            # Keep loop running
            loop.run_forever()
        
        # Start manager thread
        manager_thread = threading.Thread(target=run_manager_loop, daemon=True)
        manager_thread.start()
        
        # Wait for the loop to be created
        import time
        max_wait = 2.0
        waited = 0
        while loop_container['loop'] is None and waited < max_wait:
            time.sleep(0.1)
            waited += 0.1
        
        if loop_container['loop']:
            # Set it in the command routes module with the loop
            set_command_manager(command_manager, loop_container['loop'])
            logger.info("✓ Command manager initialized and started in background thread")
        else:
            logger.error("Failed to initialize command manager event loop")
        
    except Exception as e:
        logger.exception(f"Could not initialize command manager: {e}")
        logger.warning("Command execution endpoints will not be available")
    
    return app
