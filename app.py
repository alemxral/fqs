"""
QuickShoot Terminal - Main Textual Application
Cross-platform TUI for Polymarket trading
"""
import sys
import os

# Add parent directory to path for fqs module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from textual.app import App
from textual.binding import Binding


# Import screens
from fqs.ui.screens.welcome_screen import WelcomeScreen

# Import config
from fqs.config.settings import Settings
from fqs.utils.logger import setup_logger

from fqs.managers.requests_manager import RequestManager
from fqs.managers.commands_manager import CommandsManager
from fqs.managers.navigation_manager import NavigationManager

from fqs.core.core import CoreModule

#Libs
import asyncio
import httpx
from pathlib import Path


class QSTerminal(
    App,
    NavigationManager
):
    # CommandsManager and RequestManager are NOT inherited - they're service instances only
    """
    Main Textual application for QSTerminal
    
    Features:
    - Live order book updates via WebSocket
    - Market/limit order execution
    - Market search and token subscription
    - Session persistence
    - Cross-platform (Windows + Linux)
    """
    
    # ============= Configuration =============
    TITLE = "QSTerminal"
    SUB_TITLE = "Polymarket Trading Terminal"
    
    # Load CSS theme
    CSS_PATH = Path(__file__).parent / "ui" / "styles" / "theme.tcss"
    
    # Global keybindings (work on any screen)
    BINDINGS = [
        Binding("f1", "show_help", "Help", priority=True),
        Binding("ctrl+o", "show_settings", "Settings", priority=True),
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]
    
    # ============= Initialization =============
    def __init__(self,**kwargs):
        """
        Initialize the QSTerminal application
        
        Args:
            clob_url: Polymarket CLOB API URL
            ws_url: WebSocket URL for market data
            chain_id: Blockchain chain ID (137 = Polygon)
        """
        super().__init__(**kwargs)

        # Setup logger first
        self.logger = setup_logger()
        self.logger.info("Initializing QSTerminal")

        # Create CoreModule instance   
        self.core = CoreModule()
        
        # IMPORTANT: Set app reference in core so managers can access it
        self.core.app = self
        
        self.logger.info(f"CoreModule initialized with websocket_manager: {hasattr(self.core, 'websocket_manager')}")

        # Initialize Flask API client
        self.api_client = httpx.AsyncClient(
            base_url="http://127.0.0.1:5000",
            timeout=10.0
        )
        self.logger.info("Flask API client initialized")

        # Initialize service instances (NOT mixins)
        self.commands_manager = CommandsManager(self.core, app=self)
        self.request_manager = RequestManager(self.core, app=self, logger=self.logger)
        
        self.logger.info("Managers initialized successfully")
       

    
    # ============= App Lifecycle =============
    def on_mount(self) -> None:
        """Called when app is mounted (startup)"""
        self.logger.info("App mounted - starting main screen")
        
        # Start commands manager
        asyncio.create_task(self._start_managers())
        
        # Show welcome screen FIRST
        self.push_screen(WelcomeScreen())
        
        # Start background initialization
        asyncio.create_task(self._startup_init())

    async def _start_managers(self):
        """Start all managers that require async initialization"""
        try:
            self.logger.info("Starting CommandsManager...")
            await self.commands_manager.start()
            self.logger.info("CommandsManager started successfully")
            
            self.logger.info("Starting RequestManager...")
            await self.request_manager.start()
            self.logger.info("RequestManager started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start managers: {e}", exc_info=True)

    async def on_unmount(self) -> None:
        """Called when app is shutting down"""
        self.logger.info("App unmounting - saving session and closing connections")
        
        # Stop managers
        try:
            await self.commands_manager.stop()
            await self.request_manager.stop()
        except Exception as e:
            self.logger.error(f"Error stopping managers: {e}")
        
        # Close API client
        try:
            await self.api_client.aclose()
            self.logger.info("Flask API client closed")
        except Exception as e:
            self.logger.error(f"Error closing API client: {e}")
            
        self.logger.info("Shutdown complete")

    
    async def _startup_init(self):
        """
        Initialize app data in background while welcome screen is shown
        """
        try:
            self.logger.info("Starting background initialization")
            
            self.logger.info("Background initialization complete")
            
        except Exception as e:
            self.logger.error(f"Startup initialization failed: {e}", exc_info=True)
    
    def action_show_settings(self) -> None:
        """Show settings screen"""
        from fqs.ui.screens.settings_screen import SettingsScreen
        self.push_screen(SettingsScreen())
    
    def action_show_help(self) -> None:
        """Show help information"""
        self.notify("F1: Help | Ctrl+O: Settings | Ctrl+Q: Quit", title="Quick Help", severity="information")


# ============= Entry Point =============
def run_terminal(**kwargs) -> None:

    """
    Run the QSTerminal application
    
    Args:
        clob_url: Polymarket CLOB API URL
        ws_url: WebSocket URL
        chain_id: Blockchain chain ID
    """
    app = QSTerminal(**kwargs)
    app.run()


if __name__ == "__main__":
    # Can run directly for testing
    run_terminal()