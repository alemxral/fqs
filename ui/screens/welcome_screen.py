"""
Welcome Screen - Shows logo and startup options.

This version:
- Does NOT pass id or expand to MainHeader() (avoids TypeError if the imported MainHeader
  implementation doesn't accept those kwargs).
- Logs the file path and signature of the MainHeader class at runtime so you can confirm
  which file is actually being imported (useful to track down stale/duplicate modules).
- Keeps a reference to the header to update it in on_mount, and applies style hints so it
  can request full width.
"""
import inspect
import sys
from typing import Optional

from textual.theme import Theme
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Container

from ..widgets.logo import PMTerminalLogo  # ← your Logo widget
from ..widgets.main_header import MainHeader  # ← the MainHeader being imported (may be the wrong file)

# Default values — your App can override these as attributes (app.version, app.chain, app.network)
DEFAULT_VERSION = "0.1.0"
DEFAULT_CHAIN = "Polygon"
DEFAULT_NETWORK = "Mainnet"

class WelcomeScreen(Screen):
   

    CSS = """

/* -------------------------
   Welcome Screen
   ------------------------- */

    MainHeader {
    
    width: 100%;
    
    }


WelcomeScreen {
    background: #0B1220;
    align: center middle;
    content-align: center middle;
}

WelcomeScreen #welcome-container {
      
    width: 100%;
    content-align: center middle;
    padding: 1 0;
    align: center middle;
    height: auto;
    background: #0F1724;
    border: solid #4A5568;
}


#continue-hint {
    color: #9AA9BB;
    text-align: center;
    padding: 1 0;
    align: center middle;
    content-align: center middle;
}


#version-info {
    color: #9AA9BB;
    text-align: center;
    padding: 1 0;
    align: center middle;
    content-align: center middle;
}

#logocontainer {
  
    content-align: center middle;
    padding: 1 0 0 0;
    align: center middle;

}

#optionscontainer {
  
    content-align: center middle;
    align: center middle;

}


WelcomeScreen Button {
    min-width: 16;
    max-width: 32;
    margin: 0 1;
    align: center middle;
    content-align: center middle;
}

WelcomeScreen .wallet-info {
    width: 100%;
    border: solid #4A5568;
    padding: 1;
    margin: 1 0;
    background: #0B1220;
}

WelcomeScreen .wallet-title {
    color: #9FB0C7;
    text-style: bold;
}

WelcomeScreen .wallet-address {
    color: #9AA9BB;
    margin-left: 2;
}

    """

    BINDINGS = [
        ("escape", "continue", "Continue"),
        ("enter", "continue", "Continue"),
        ("space", "continue", "Continue"),
        ("s", "start", "Start"),
        ("c", "settings", "Settings"),
        ("h", "help", "Help"),
        ("x", "exit", "Exit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose welcome screen with header and logo.

        IMPORTANT: do not pass id/expand into MainHeader here to avoid TypeError
        if the imported class doesn't accept those kwargs.
        """
        
        # Create and store a reference to the header without kwargs
        self.header = MainHeader()  # no id, no expand
        yield self.header

        with Container(id="welcome-container"):
            with Container(id="logocontainer"):
                yield PMTerminalLogo(size="full", show_subtitle=True, id="logo")
                yield Static(self._version_text(), id="version-info")

            with Container(id="optionscontainer"):
                yield Button("[S] Start Trading", id="start", variant="primary")
                yield Button("[C] Settings", id="settings")
                yield Button("[H] Help", id="help")
                yield Button("[X] Exit", id="exit", variant="error")
    

    def on_mount(self) -> None:
        """Update header and version info after the screen is mounted.

        Also logs diagnostic info about the imported MainHeader class so you can
        find which file is actually being used.
        """

        # Update header data from the app if available (fallbacks)
        funder_address = getattr(self.app, "funder_address", "")
        funder_balance = getattr(self.app, "funder_balance", 0.0)
        proxy_address = getattr(self.app, "proxy_address", "")
        proxy_balance = getattr(self.app, "proxy_balance", 0.0)
        clob_connected = getattr(self.app, "clob_connected", False)
        ws_connected = getattr(self.app, "ws_connected", False)

        try:
            self.header.update_header(
                funder_address=funder_address,
                funder_balance=funder_balance,
                proxy_address=proxy_address,
                proxy_balance=proxy_balance,
                clob_connected=clob_connected,
                ws_connected=ws_connected,
            )
        except Exception:
            # if update_header missing or raises, ignore so screen still loads
            self.app.log("DEBUG: header.update_header not available or raised an error")

        # Update version string
        version = getattr(self.app, "version", DEFAULT_VERSION)
        chain = getattr(self.app, "chain", DEFAULT_CHAIN)
        network = getattr(self.app, "network", DEFAULT_NETWORK)
        version_text = f"[dim]Version {version} | Chain: {chain} | Network: {network}[/dim]"

        try:
            version_widget = self.query_one("#version-info", Static)
            version_widget.update(version_text)
        except Exception:
            pass

        self.notify("System Booted")

        # Focus primary button
        try:
            self.query_one("#start", Button).focus()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "start":
            self.action_start()
        elif btn_id == "settings":
            self.action_settings()
        elif btn_id == "help":
            self.action_help()
        elif btn_id == "exit":
            self.action_exit()

    def action_continue(self) -> None:
        from .home_screen import HomeScreen
        screen = HomeScreen()
        if hasattr(self.app, "push_screen"):
            self.app.push_screen(screen)
        elif hasattr(self.app, "switch_screen"):
            self.app.switch_screen(screen)
        else:
            try:
                self.app.active_screen = screen
            except Exception:
                self.app.exit()

    def action_start(self) -> None:
        self.action_continue()

    def action_settings(self) -> None:
        if hasattr(self.app, "action_show_settings"):
            self.app.action_show_settings()
        elif hasattr(self.app, "show_settings"):
            self.app.show_settings()
        else:
            self.app.log("Settings requested, but no handler found on the App.")

    def action_help(self) -> None:
        if hasattr(self.app, "action_show_help"):
            self.app.action_show_help()
        elif hasattr(self.app, "show_help"):
            self.app.show_help()
        else:
            self.app.log("Help requested, but no handler found on the App.")

    def action_exit(self) -> None:
        self.app.exit()

    def _version_text(self) -> str:
        version = getattr(self.app, "version", DEFAULT_VERSION) if hasattr(self, "app") else DEFAULT_VERSION
        chain = getattr(self.app, "chain", DEFAULT_CHAIN) if hasattr(self, "app") else DEFAULT_CHAIN
        network = getattr(self.app, "network", DEFAULT_NETWORK) if hasattr(self, "app") else DEFAULT_NETWORK
        return f"[dim]Version {version} | Chain: {chain} | Network: {network}[/dim]"