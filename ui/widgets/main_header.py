"""
Main Header Widget - Generic application info
Displays: Wallets, Balances, Connection Status, Time
"""
from textual.widgets import Static, Header
from textual.reactive import reactive
from datetime import datetime
from typing import Optional


class MainHeader(Static):



    """
    Main header showing generic info (always visible)
    
    Displays:
    - Funder Wallet (address)
    - Proxy Wallet (address)
    - Funder Balance (USDC)
    - Proxy Balance (USDC)
    - Connection Status (CLOB + WS)
    - Current Time
    - Network (Polygon/Ethereum)
    """
    
    # Reactive attributes (auto-refresh when changed)
    funder_address: reactive[Optional[str]] = reactive(None)
    proxy_address: reactive[Optional[str]] = reactive(None)
    funder_balance: reactive[float] = reactive(0.0)
    proxy_balance: reactive[float] = reactive(0.0)
    clob_connected: reactive[bool] = reactive(False)  # ← Changed from api_connected
    ws_connected: reactive[bool] = reactive(False)
    network: reactive[str] = reactive("Polygon")
    
    DEFAULT_CSS = """
    MainHeader {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
        padding: 0 2;
    }
    
    MainHeader.disconnected {
        background: $error;
    }
    
    MainHeader.connected {
        background: $success-darken-2;
    }
    
    MainHeader.auth-error {
        background: $warning;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.update_timer = None
        self.balance_refresh_timer = None
   
    
    def on_mount(self) -> None:
        """Start display refresh timer and load initial balance from cache"""
        # Refresh display every second (for time updates)
        self.update_timer = self.set_interval(1.0, self.refresh)
        
        # NO automatic balance refresh - only manual refresh via command
        # This prevents constant blockchain calls and annoying notifications
        
        # Load initial balance from cache ONLY (fast, no blockchain call)
        self._load_cached_balance()
    
    def render(self) -> str:
        """Render the header with all info"""
        
        # Format wallet addresses (truncate)
        funder = self._format_address(self.funder_address)
        proxy = self._format_address(self.proxy_address)
        
        # Format balances
        funder_bal = f"${self.funder_balance:,.2f}" if self.funder_balance else "$0.00"
        proxy_bal = f"${self.proxy_balance:,.2f}" if self.proxy_balance else "$0.00"
        
        # Connection status with auth indicator
        clob_status = "[green]●[/green]" if self.clob_connected else "[red]●[/red]"
        ws_status = "[green]●[/green]" if self.ws_connected else "[red]●[/red]"
        
        # Current time
        now = datetime.now().strftime("%H:%M:%S")
        
        # Build header lines
        line1 = (
            f"[bold cyan]QSTerminal[/bold cyan]  "
            f"[dim]|[/dim]  "
            f"{clob_status} CLOB  "  # ← Changed label
            f"{ws_status} WS  "
            f"[dim]|[/dim]  "
            f"[yellow]{self.network}[/yellow]  "
            f"[dim]|[/dim]  "
            f"[dim]{now}[/dim] "

            f"[bold] Funder:[/bold] [cyan]{funder}[/cyan] [{funder_bal}]  "
            f"[dim]|[/dim]  "
            f"[bold]Proxy:[/bold] [magenta]{proxy}[/magenta] [{proxy_bal}]"
        )
        
        return f"{line1}"
    
    def _format_address(self, address: Optional[str]) -> str:
        """Format wallet address (truncate middle)"""
        if not address:
            return "[dim]Not connected[/dim]"
        
        # Always truncate addresses to show first 6 and last 4 characters
        if len(address) >= 10:
            return f"{address[:6]}...{address[-4:]}"
        return address
    
    # ============= Update Methods =============
    
    def update_funder(self, address: str, balance: float) -> None:
        """Update funder wallet info"""
        self.funder_address = address
        self.funder_balance = balance
        # Force immediate refresh to show the updated values
        self.refresh()
    
    def update_proxy(self, address: str, balance: float) -> None:
        """Update proxy wallet info"""
        self.proxy_address = address
        self.proxy_balance = balance
        # Force immediate refresh to show the updated values
        self.refresh()
    
    def update_balances(self, funder_balance: float, proxy_balance: float) -> None:
        """Update both balances"""
        self.funder_balance = funder_balance
        self.proxy_balance = proxy_balance
        # Force immediate refresh to show the updated values
        self.refresh()
    
    def set_clob_status(self, connected: bool) -> None:  # ← Renamed method
        """
        Update CLOB connection/authentication status
        
        Args:
            connected: True if authenticated and connected to CLOB API
        """
        self.clob_connected = connected
        self._update_style()
    
    def set_ws_status(self, connected: bool) -> None:
        """Update WebSocket connection status"""
        self.ws_connected = connected
        self._update_style()
    
    def set_network(self, network: str) -> None:
        """Set network name (Polygon, Ethereum, etc.)"""
        self.network = network
    
    def _update_style(self) -> None:
        """Update header style based on connection status"""
        if self.clob_connected and self.ws_connected:
            # Both connected - green
            self.remove_class("disconnected", "auth-error")
            self.add_class("connected")
        elif not self.clob_connected and not self.ws_connected:
            # Both disconnected - red
            self.remove_class("connected", "auth-error")
            self.add_class("disconnected")
        else:
            # Partial connection (likely auth issue) - yellow/warning
            self.remove_class("connected", "disconnected")
            self.add_class("auth-error")
    
    def _load_cached_balance(self) -> None:
        """
        Load balance directly from JSON cache file and addresses from .env
        
        This is called on mount to immediately show balance.
        Reads data/balance.json and updates header display.
        """
        try:
            import json
            import os
            from pathlib import Path
            from dotenv import load_dotenv
            from web3 import Web3
            
            # Load .env file
            env_path = Path(__file__).parent.parent.parent / "config" / ".env"
            load_dotenv(env_path)
            
            # Get FUNDER address from .env
            funder_address = os.getenv("FUNDER")
            if funder_address:
                self.funder_address = funder_address
            
            # Get derived address from PRIVATE_KEY
            private_key = os.getenv("PRIVATE_KEY")
            if private_key:
                try:
                    account = Web3().eth.account.from_key(private_key)
                    self.proxy_address = account.address
                except Exception as e:
                    if hasattr(self.app, 'logger'):
                        self.app.logger.warning(f"Could not derive address from PRIVATE_KEY: {e}")
            
            # Get path to balance.json
            balance_file = Path(__file__).parent.parent.parent / "data" / "balance.json"
            
            if balance_file.exists():
                with open(balance_file, 'r') as f:
                    data = json.load(f)
                    
                    if data.get('success'):
                        # IMPORTANT: JSON naming is backwards!
                        # - "proxy_balance" in JSON = FUNDER wallet balance
                        # - "derived_balance" in JSON = Proxy/Derived wallet balance
                        funder_bal = data.get('proxy_balance', 0.0)
                        proxy_bal = data.get('derived_balance', 0.0)
                        
                        # Update the reactive attributes
                        self.funder_balance = funder_bal
                        self.proxy_balance = proxy_bal
                        
                        # Force refresh to show updated values
                        self.refresh()
                        
                        if hasattr(self.app, 'logger'):
                            self.app.logger.info(
                                f"Header balance loaded from cache: "
                                f"Funder=${funder_bal:.2f}, Proxy=${proxy_bal:.2f}"
                            )
            else:
                if hasattr(self.app, 'logger'):
                    self.app.logger.warning(f"Balance cache file not found: {balance_file}")
                    
        except Exception as e:
            # Silently fail - header will show default values
            if hasattr(self.app, 'logger'):
                self.app.logger.error(f"Could not load cached balance: {e}", exc_info=True)
    
    async def _request_balance_update(self, use_cache: bool = True) -> None:
        """
        Request balance update via RequestManager
        
        Args:
            use_cache: If True, use cached balance (fast). If False, fetch fresh (slow).
        """
        try:
            app = self.app
            
            # Submit request to RequestManager
            future = await app.request_manager.submit(
                origin="MainHeader",
                request_type="balance_header",
                params={"use_cache": use_cache}
            )
            
            # Wait for response
            response = await future
            
            if response.success:
                # Balance was fetched and header updated by the handler
                if hasattr(app, 'logger'):
                    app.logger.debug(f"MainHeader balance updated: {response.message}")
            else:
                if hasattr(app, 'logger'):
                    app.logger.warning(f"MainHeader balance update failed: {response.message}")
                    
        except Exception as e:
            if hasattr(self.app, 'logger'):
                self.app.logger.error(f"Failed to request balance update: {e}", exc_info=True)
    
    async def _request_proxy_balance_update(self, use_cache: bool = True) -> None:
        """
        Request proxy balance update via RequestManager
        
        Args:
            use_cache: If True, use cached balance (fast). If False, fetch fresh (slow).
        """
        try:
            app = self.app
            
            # Submit request to RequestManager
            future = await app.request_manager.submit(
                origin="MainHeader",
                request_type="proxy_balance_header",
                params={"use_cache": use_cache}
            )
            
            # Wait for response
            response = await future
            
            if response.success:
                # Balance was fetched and header updated by the handler
                if hasattr(app, 'logger'):
                    app.logger.debug(f"MainHeader proxy balance updated: {response.message}")
            else:
                if hasattr(app, 'logger'):
                    app.logger.warning(f"MainHeader proxy balance update failed: {response.message}")
                    
        except Exception as e:
            if hasattr(self.app, 'logger'):
                self.app.logger.error(f"Failed to request proxy balance update: {e}", exc_info=True)
    
    def refresh_balance_from_blockchain(self) -> None:
        """
        Manually refresh balance from blockchain (slow, called by user command)
        
        This should be called when:
        - User runs a 'refresh balance' command
        - After completing a trade
        - When explicitly requested by user
        
        NOT called automatically on timer.
        """
        try:
            app = self.app
            
            # Check if RequestManager is available
            if not hasattr(app, 'request_manager'):
                if hasattr(app, 'notify'):
                    app.notify("⚠️ Balance refresh not available", severity="warning", timeout=3)
                return
            
            # Notify user that we're fetching (since this is manual/slow)
            if hasattr(app, 'notify'):
                app.notify("⛓️ Fetching balances from blockchain...", severity="information", timeout=3)
            
            # Request fresh balances from blockchain (not cache) via RequestManager
            import asyncio
            # Refresh both funder and proxy balances
            asyncio.create_task(self._request_balance_update(use_cache=False))
            asyncio.create_task(self._request_proxy_balance_update(use_cache=False))
            
        except Exception as e:
            if hasattr(self.app, 'logger'):
                self.app.logger.error(f"Manual balance refresh failed: {e}", exc_info=True)
            if hasattr(self.app, 'notify'):
                self.app.notify(f"✗ Balance refresh failed: {str(e)}", severity="error", timeout=5)

