"""
Settings Screen - Configure application parameters and trading settings
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Header, Footer, Static, Input, Button
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from rich.text import Text


class SettingItem(Horizontal):
    """A single setting item with label and input"""
    
    def __init__(self, label: str, value: str, setting_key: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_text = label
        self.value = value
        self.setting_key = setting_key
    
    def compose(self) -> ComposeResult:
        yield Static(f"{self.label_text}:", classes="setting-label")
        yield Input(value=str(self.value), id=f"input_{self.setting_key}", classes="setting-input")


class SettingsScreen(Screen):
    """
    Settings screen for configuring application parameters
    
    Configurable settings:
    - Trading parameters (default size, max position, slippage)
    - Display settings (refresh interval, theme)
    - API configuration (view only)
    """
    
    BINDINGS = [
        Binding("escape", "go_back", "Back", priority=True),
        Binding("ctrl+s", "save_settings", "Save", priority=True),
    ]
    
    CSS = """
    SettingsScreen {
        background: $surface;
    }
    
    #settings_container {
        height: 100%;
        background: $panel;
        border: solid $primary;
        padding: 2;
    }
    
    #settings_content {
        height: 1fr;
        overflow-y: auto;
        padding: 1;
    }
    
    .settings_section {
        margin: 1 0;
        padding: 1;
        background: $surface;
        border: solid $accent;
    }
    
    .section_title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    SettingItem {
        height: 3;
        margin: 0 0 1 0;
    }
    
    .setting-label {
        width: 30%;
        padding: 1;
        color: $text;
    }
    
    .setting-input {
        width: 70%;
    }
    
    #button_container {
        height: auto;
        layout: horizontal;
        align: center middle;
        padding: 1;
    }
    
    Button {
        margin: 0 1;
        min-width: 16;
    }
    
    #status_bar {
        dock: bottom;
        height: 3;
        background: $boost;
        padding: 1;
        text-align: center;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = self.load_default_settings()
    
    def load_default_settings(self) -> dict:
        """Load default settings"""
        return {
            # Trading Parameters
            "default_size": 10,
            "max_position": 1000,
            "slippage": 0.01,
            "auto_sell": False,
            
            # Display Settings
            "refresh_interval": 5,
            "theme": "dark",
            "show_debug": True,
            
            # API Settings (read-only for display)
            "flask_url": "http://127.0.0.1:5000",
            "ws_enabled": True,
        }
    
    def compose(self) -> ComposeResult:
        """Create settings layout"""
        yield Header()
        
        with Container(id="settings_container"):
            yield Static("⚙️  Settings & Configuration", classes="section_title")
            
            with ScrollableContainer(id="settings_content"):
                # Trading Parameters Section
                with Vertical(classes="settings_section"):
                    yield Static("Trading Parameters", classes="section_title")
                    yield SettingItem("Default Trade Size", self.settings["default_size"], "default_size")
                    yield SettingItem("Max Position Size", self.settings["max_position"], "max_position")
                    yield SettingItem("Slippage Tolerance", self.settings["slippage"], "slippage")
                    yield SettingItem("Auto-Sell (true/false)", self.settings["auto_sell"], "auto_sell")
                
                # Display Settings Section
                with Vertical(classes="settings_section"):
                    yield Static("Display Settings", classes="section_title")
                    yield SettingItem("Refresh Interval (sec)", self.settings["refresh_interval"], "refresh_interval")
                    yield SettingItem("Theme (dark/light)", self.settings["theme"], "theme")
                    yield SettingItem("Show Debug Panel", self.settings["show_debug"], "show_debug")
                
                # API Settings Section (Read-Only)
                with Vertical(classes="settings_section"):
                    yield Static("API Configuration (Read-Only)", classes="section_title")
                    yield Static(f"Flask Backend: {self.settings['flask_url']}")
                    yield Static(f"WebSocket: {'Enabled' if self.settings['ws_enabled'] else 'Disabled'}")
                    yield Static(f"CLOB API: Configured via .env")
            
            # Action Buttons
            with Horizontal(id="button_container"):
                yield Button("Save Settings", id="btn_save", variant="primary")
                yield Button("Reset to Defaults", id="btn_reset", variant="warning")
                yield Button("Cancel", id="btn_cancel")
            
            yield Static("Press Ctrl+S to save | Esc to cancel", id="status_bar")
        
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        if event.button.id == "btn_save":
            self.action_save_settings()
        elif event.button.id == "btn_reset":
            self.reset_to_defaults()
        elif event.button.id == "btn_cancel":
            self.action_go_back()
    
    async def action_save_settings(self) -> None:
        """Save settings from input fields"""
        try:
            # Collect values from inputs
            new_settings = {}
            
            # Trading parameters
            new_settings["default_size"] = int(self.query_one("#input_default_size", Input).value)
            new_settings["max_position"] = int(self.query_one("#input_max_position", Input).value)
            new_settings["slippage"] = float(self.query_one("#input_slippage", Input).value)
            auto_sell_val = self.query_one("#input_auto_sell", Input).value.lower()
            new_settings["auto_sell"] = auto_sell_val in ["true", "1", "yes"]
            
            # Display settings
            new_settings["refresh_interval"] = int(self.query_one("#input_refresh_interval", Input).value)
            new_settings["theme"] = self.query_one("#input_theme", Input).value
            show_debug_val = self.query_one("#input_show_debug", Input).value.lower()
            new_settings["show_debug"] = show_debug_val in ["true", "1", "yes"]
            
            # Validate settings
            if new_settings["default_size"] < 1:
                self.notify("Default size must be >= 1", severity="error")
                return
            
            if new_settings["max_position"] < new_settings["default_size"]:
                self.notify("Max position must be >= default size", severity="error")
                return
            
            if not (0 < new_settings["slippage"] < 1):
                self.notify("Slippage must be between 0 and 1", severity="error")
                return
            
            # Update settings
            self.settings.update(new_settings)
            
            # Store in app session
            if not hasattr(self.app, 'session'):
                self.app.session = {}
            self.app.session['settings'] = self.settings
            
            self.notify("✓ Settings saved successfully", severity="information")
            self.app.logger.info(f"Settings updated: {new_settings}")
            
        except ValueError as e:
            self.notify(f"Invalid value: {e}", severity="error")
        except Exception as e:
            self.notify(f"Error saving settings: {e}", severity="error")
            self.app.logger.error(f"Settings save error: {e}", exc_info=True)
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to default values"""
        self.settings = self.load_default_settings()
        
        # Update input fields
        try:
            self.query_one("#input_default_size", Input).value = str(self.settings["default_size"])
            self.query_one("#input_max_position", Input).value = str(self.settings["max_position"])
            self.query_one("#input_slippage", Input).value = str(self.settings["slippage"])
            self.query_one("#input_auto_sell", Input).value = str(self.settings["auto_sell"])
            self.query_one("#input_refresh_interval", Input).value = str(self.settings["refresh_interval"])
            self.query_one("#input_theme", Input).value = str(self.settings["theme"])
            self.query_one("#input_show_debug", Input).value = str(self.settings["show_debug"])
            
            self.notify("Settings reset to defaults", severity="information")
        except Exception as e:
            self.notify(f"Error resetting: {e}", severity="error")
    
    def action_go_back(self) -> None:
        """Go back to previous screen"""
        self.app.pop_screen()
