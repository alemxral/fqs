"""
Navigation Mixin for QSTerminal
Handles screen navigation and keybinding actions
"""
import pyperclip
# import pyautogui  # Commented out - requires tkinter which isn't needed for TUI
from textual.app import App
import asyncio
from ..ui.widgets.command_input import Input


class NavigationManager():
    """
    Navigation Mixin for QSTerminal
    
    This is a TRUE MIXIN class - provides methods but has no __init__.
    It assumes the following attributes exist on self (the app):
    - self.logger: Logger instance
    - self.screen: Current screen reference
    - self.push_screen(): Method to push new screen
    - self.exit(): Method to exit app
    - self.app: Reference to app (Textual provides this)
    
    Provides action_* methods bound to keyboard shortcuts:
    - action_show_help() - Navigate to help screen (F1)
    - action_show_settings() - Navigate to settings screen (Ctrl+S)
    - action_toggle_markets() - Toggle markets view (F2)
    - action_show_fetch() - Navigate to fetch screen (F3)
    - action_show_unitrade() - Navigate to uni-trade screen (F4)
    - action_show_multitrade() - Navigate to multi-trade screen (F5)
    - action_show_market_analysis() - Navigate to market analysis (F6)
    - action_quit() - Exit application (Ctrl+Q)
    - action_paste_clipboard() - Paste from clipboard (Ctrl+V)
    
    Usage:
        class QSTerminal(App, NavigationManager):
            # action_* methods available on app, bound to keybindings
    """

    def action_paste_clipboard(self) -> None:
        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content:
                # pyautogui.write(clipboard_content)
                input_widget = self.screen.query_one("#command_input", Input)
                input_widget.value += clipboard_content
                self.app.notify("Clipboard pasted!")
            else:
                self.app.notify("Clipboard is empty.")
        except Exception as e:
            self.app.notify(f"Paste failed: {e}")

    def action_show_help(self) -> None:
        """
        Show help screen (F1)
        
        Displays command reference, keyboard shortcuts, and usage guide
        """
        self.logger.debug("Navigating to help screen")
        
        from ..ui.screens.help_screen import HelpScreen
        self.push_screen(HelpScreen())
    
    def action_show_settings(self) -> None:
        """
        Show settings screen (Ctrl+S)
        
        Displays application settings and configuration options
        """
        self.logger.debug("Navigating to settings screen")
        
        from ..ui.screens.settings_screen import SettingsScreen
        self.push_screen(SettingsScreen(self))
    
    def action_toggle_markets(self) -> None:
        """
        Toggle markets view (F2)
        
        If current screen supports market view toggling, triggers it
        """
        self.logger.debug("Toggling markets view")
        
        if hasattr(self.screen, 'toggle_markets_view'):
            self.screen.toggle_markets_view()
        else:
            self.logger.debug("Current screen does not support market view toggle")
    
    def action_show_fetch(self) -> None:
        """
        Show fetch screen (F3)
        
        Displays market data fetching and search interface
        """
        self.logger.debug("Navigating to fetch screen")
        
        from ..ui.screens.fetch_screen import FetchScreen
        self.push_screen(FetchScreen(self))
    
    def action_show_unitrade(self) -> None:
        """
        Show uni-trade screen (F4)
        
        Displays single market trading interface
        """
        self.logger.debug("Navigating to uni-trade screen")
        
        from ..ui.screens.unitrade_screen import UniTradeScreen
        self.push_screen(UniTradeScreen(self))
    
    def action_show_multitrade(self) -> None:
        """
        Show multi-trade screen (F5)
        
        Displays multiple market trading interface
        """
        self.logger.debug("Navigating to multi-trade screen")
        
        from ..ui.screens.multitrade_screen import MultiTradeScreen
        self.push_screen(MultiTradeScreen(self))
    
    def action_show_market_analysis(self) -> None:
        """
        Show market analysis screen (F6)
        
        Displays market analytics, charts, and statistics
        """
        self.logger.debug("Navigating to market analysis screen")
        
        from ..ui.screens.marketanalysis_screen import MarketAnalysisScreen
        self.push_screen(MarketAnalysisScreen(self))
    
    def action_quit(self) -> None:
        """
        Quit application (Ctrl+Q / Ctrl+C)
        
        Exits the terminal application
        """
        self.logger.info("User initiated quit")
        self.exit()
