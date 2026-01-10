"""
Football Trade Screen - Main trading interface for football markets
Displays live football events, orderbooks, balance, and command interface
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Header, Footer, Static, RichLog, DataTable, Label
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.reactive import reactive
from rich.text import Text
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add utils path for gamma-api access
utils_path = Path(__file__).parent.parent.parent / "utils" / "gamma-api"
if str(utils_path) not in sys.path:
    sys.path.insert(0, str(utils_path))

from fqs.ui.widgets.football_widget import FootballWidget
from fqs.ui.widgets.orderbook import OrderBookWidget
from fqs.ui.widgets.command_input import CommandInput
from get_events_with_tags import get_events_with_tags


class FootballTradeScreen(Screen):
    """
    Main trading screen for football markets
    
    Layout:
    - Top: Header with Balance info
    - Left: Live Football Events List
    - Center: Match Widget + Orderbooks
    - Right: Command Output Panel
    - Bottom: Command Input
    """
    
    BINDINGS = [
        Binding("escape", "go_back", "Back", priority=True),
        Binding("ctrl+y", "quick_buy_yes", "Buy YES", priority=True),
        Binding("ctrl+n", "quick_buy_no", "Buy NO", priority=True),
        Binding("ctrl+b", "refresh_balance", "Balance", priority=True),
        Binding("ctrl+r", "refresh_events", "Refresh", priority=True),
        Binding("ctrl+s", "update_score", "Update Score", priority=True),
        Binding("ctrl+t", "update_time", "Update Time", priority=True),
    ]
    
    # Reactive balance
    balance = reactive(0.0)
    
    CSS = """
    FootballTradeScreen {
        background: $surface;
    }
    
    #header_info {
        height: 3;
        width: 100%;
        background: $boost;
        border: tall $primary;
        padding: 0 2;
    }
    
    #balance_label {
        color: $success;
        text-style: bold;
    }
    
    #main_container {
        height: 1fr;
        layout: horizontal;
    }
    
    #events_panel {
        width: 25%;
        height: 100%;
        border: solid $primary;
        background: $panel;
    }
    
    #events_table {
        height: 1fr;
    }
    
    #center_panel {
        width: 50%;
        height: 100%;
        layout: vertical;
    }
    
    #orderbooks_container {
        height: 1fr;
        layout: horizontal;
    }
    
    .orderbook-side {
        width: 1fr;
        height: 100%;
        border: solid $secondary;
    }
    
    #output_panel {
        width: 25%;
        height: 100%;
        border: solid $accent;
        background: $surface;
    }
    
    #command_output {
        height: 1fr;
        background: $surface;
    }
    
    #command_container {
        height: 4;
        dock: bottom;
        border: tall $accent;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.yes_token = None
        self.no_token = None
        self.market_slug = None
        self.selected_event_slug = None
        self.football_data = {
            "score": "0-0",
            "time": "0:00",
            "minute": 0,
            "seconds": 0,
            "phase": "Pre-match",
            "time_remaining": 90,
            "is_timer_running": False,
            "match_side": None,
            "goal_difference": 0
        }
    
    def compose(self) -> ComposeResult:
        """Create screen layout"""
        yield Header(show_clock=True)
        
        # Header with balance info
        with Horizontal(id="header_info"):
            yield Label("⚽ Football Trading Terminal", id="title_label")
            yield Label("Balance: Loading...", id="balance_label")
        
        # Main 3-column layout
        with Container(id="main_container"):
            # Left: Events list (25%)
            with Vertical(id="events_panel"):
                yield Static("⚽ Live Football Events", id="events_header")
                yield DataTable(id="events_table")
            
            # Center: Match widget + Orderbooks (50%)
            with Vertical(id="center_panel"):
                yield FootballWidget(id="football_widget")
                
                with Container(id="orderbooks_container"):
                    with Vertical(classes="orderbook-side"):
                        yield Static("📈 YES", id="yes_header")
                        yield OrderBookWidget(id="yes_orderbook")
                    
                    with Vertical(classes="orderbook-side"):
                        yield Static("📉 NO", id="no_header")
                        yield OrderBookWidget(id="no_orderbook")
            
            # Right: Command output (25%)
            with Vertical(id="output_panel"):
                yield Static("📋 Command Output", id="output_header")
                yield RichLog(id="command_output", highlight=True, markup=True, wrap=True)
        
        # Bottom: Command input
        with Container(id="command_container"):
            yield CommandInput(command_handler=self.handle_command, id="command_input")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Initialize screen with data"""
        # Setup events table
        events_table = self.query_one("#events_table", DataTable)
        events_table.add_columns("Match", "Time", "Status")
        events_table.cursor_type = "row"
        
        # Load football events
        await self.load_football_events()
        
        # Subscribe to command responses
        if hasattr(self.app, 'commands_manager'):
            self.app.commands_manager.subscribe(self._on_command_response)
        
        # Start balance refresh timer (every 30 seconds)
        self.set_interval(30.0, self.update_balance)
        
        # Initial balance fetch
        await self.update_balance()
        
        # Get market data from app session if available
        if hasattr(self.app, 'session'):
            self.yes_token = self.app.session.get('yes_token')
            self.no_token = self.app.session.get('no_token')
            self.market_slug = self.app.session.get('market_slug')
            market_question = self.app.session.get('market_question', 'Unknown Market')
            
            if self.yes_token and self.no_token:
                self.log_output(f"[bold cyan]Market:[/bold cyan] {market_question}")
                self.log_output(f"[dim]Slug: {self.market_slug}[/dim]")
                await self.connect_websocket()
    
    async def load_football_events(self) -> None:
        """Load live football events from Gamma API"""
        try:
            self.log_output("[yellow]Fetching live football events...[/yellow]")
            
            # Football tag ID is typically 100381 (or search for "football" in tags)
            # Get active events only (closed=False)
            events_data = get_events_with_tags(
                tag_id=100381,  # Football tag
                limit=20,
                closed=False,
                order="start_date_min",
                ascending=True  # Upcoming matches first
            )
            
            events_table = self.query_one("#events_table", DataTable)
            events_table.clear()
            
            if not events_data or len(events_data) == 0:
                self.log_output("[yellow]No active football events found[/yellow]")
                return
            
            # Process events
            count = 0
            for event in events_data[:15]:  # Limit to 15 most recent
                try:
                    title = event.get('title', 'Unknown')
                    slug = event.get('slug', '')
                    start_date = event.get('start_date_min', '')
                    end_date = event.get('end_date_min', '')
                    
                    # Parse date
                    if start_date:
                        try:
                            dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                            time_str = dt.strftime("%m/%d %H:%M")
                        except:
                            time_str = "TBD"
                    else:
                        time_str = "TBD"
                    
                    # Determine status
                    if end_date:
                        try:
                            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                            if end_dt < datetime.now(end_dt.tzinfo):
                                status = "🔴 Ended"
                            else:
                                status = "🟢 Live"
                        except:
                            status = "🟡 Active"
                    else:
                        status = "🟡 Active"
                    
                    # Extract team names (simplified)
                    match_name = title[:35] + "..." if len(title) > 35 else title
                    
                    events_table.add_row(match_name, time_str, status, key=slug)
                    count += 1
                except Exception as e:
                    continue
            
            self.log_output(f"[green]✓ Loaded {count} football events[/green]")
            
        except Exception as e:
            self.log_output(f"[bold red]Error loading events: {e}[/bold red]")
            self.app.logger.error(f"Failed to load football events: {e}", exc_info=True)
    
    async def update_balance(self) -> None:
        """Fetch and update balance from Flask API"""
        try:
            if not hasattr(self.app, 'api_client'):
                return
            
            response = await self.app.api_client.get("/api/balance")
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                self.balance = float(data.get('balance', 0))
                balance_label = self.query_one("#balance_label", Label)
                balance_label.update(f"💰 Balance: ${self.balance:.2f} USDC")
                self.log_output(f"[dim]Balance updated: ${self.balance:.2f}[/dim]")
            else:
                error = data.get('error', 'Unknown error')
                self.log_output(f"[red]Balance error: {error}[/red]")
                
        except Exception as e:
            self.log_output(f"[dim red]Balance fetch failed: {e}[/dim red]")
    
    def log_output(self, message: str) -> None:
        """Log message to command output panel"""
        try:
            output_log = self.query_one("#command_output", RichLog)
            output_log.write(message)
        except:
            pass
    
    def _on_command_response(self, response) -> None:
        """Log command responses to output panel"""
        if hasattr(response, 'message'):
            if response.success:
                self.log_output(f"[green]✓[/green] {response.message}")
            else:
                self.log_output(f"[red]✗[/red] {response.message}")
    
    async def on_data_table_row_selected(self, event) -> None:
        """Handle event selection from table"""
        events_table = self.query_one("#events_table", DataTable)
        row_key = event.row_key
        
        if row_key:
            self.selected_event_slug = str(row_key.value)
            self.log_output(f"[cyan]Selected event: {self.selected_event_slug}[/cyan]")
            
            # Fetch market data for this event
            await self.handle_command(f"see slug {self.selected_event_slug}")
    
    async def connect_websocket(self) -> None:
        """Connect WebSocket for live orderbook updates"""
        try:
            self.log_output("[bold yellow]Connecting WebSocket...[/bold yellow]")
            
            # Connect to market WebSocket
            if hasattr(self.app.core, 'websocket_manager'):
                self.app.core.websocket_manager.connect_market(
                    token_ids=[self.yes_token, self.no_token],
                    on_orderbook=self._on_orderbook_update,
                    on_price_change=self._on_price_change,
                    on_last_trade=self._on_last_trade
                )
                
                self.log_output("[bold green]✓ WebSocket connected[/bold green]")
                self.notify("WebSocket connected - live updates active", severity="information")
            else:
                self.log_output("[yellow]WebSocket manager not available[/yellow]")
            
        except Exception as e:
            self.app.logger.error(f"WebSocket connection failed: {e}", exc_info=True)
            self.log_output(f"[bold red]✗ WebSocket error: {e}[/bold red]")
            self.notify(f"WebSocket error: {str(e)}", severity="error")
    
    def _on_orderbook_update(self, data: dict) -> None:
        """Handle orderbook updates from WebSocket"""
        try:
            token_id = data.get('token_id')
            
            if token_id == self.yes_token:
                orderbook_widget = self.query_one("#yes_orderbook", OrderBookWidget)
                orderbook_widget.update_from_summary(data)
                self.log_output(f"[dim green]YES orderbook updated[/dim green]")
            elif token_id == self.no_token:
                orderbook_widget = self.query_one("#no_orderbook", OrderBookWidget)
                orderbook_widget.update_from_summary(data)
                self.log_output(f"[dim red]NO orderbook updated[/dim red]")
                
        except Exception as e:
            self.app.logger.error(f"Orderbook update error: {e}", exc_info=True)
    
    def _on_price_change(self, data: dict) -> None:
        """Handle price change events"""
        token_id = data.get('token_id')
        side = "YES" if token_id == self.yes_token else "NO"
        self.log_output(f"[dim]Price change: {side}[/dim]")
    
    def _on_last_trade(self, data: dict) -> None:
        """Handle trade events"""
        token_id = data.get('token_id')
        side = "YES" if token_id == self.yes_token else "NO"
        price = data.get('price', 'N/A')
        size = data.get('size', 'N/A')
        self.log_output(f"[bold]Trade: {side} @ {price} x {size}[/bold]")
    
    async def handle_command(self, command: str) -> None:
        """Handle commands from command input"""
        self.log_output(f"[bold cyan]> {command}[/bold cyan]")
        
        # Submit to commands manager
        try:
            if hasattr(self.app, 'commands_manager'):
                await self.app.commands_manager.submit(
                    origin="FootballTradeScreen",
                    command=command
                )
        except Exception as e:
            self.log_output(f"[bold red]Command error: {e}[/bold red]")
            self.notify(f"Command error: {str(e)}", severity="error")
    
    def update_football_widget(self) -> None:
        """Update football widget with current data"""
        try:
            widget = self.query_one("#football_widget", FootballWidget)
            widget.update_data(self.football_data)
        except:
            pass
    
    # ============= ACTIONS =============
    
    async def action_quick_buy_yes(self) -> None:
        """Quick buy YES at best ask"""
        try:
            yes_orderbook = self.query_one("#yes_orderbook", OrderBookWidget)
            best_ask = yes_orderbook.get_best_ask()
            
            if not best_ask:
                self.notify("No asks available for YES token", severity="warning")
                return
            
            price = best_ask[0]
            size = 10  # Default size
            
            self.log_output(f"[bold green]Quick buy YES @ {price} x {size}[/bold green]")
            await self.handle_command(f"buy YES {price} {size}")
            
        except Exception as e:
            self.log_output(f"[bold red]Quick buy error: {e}[/bold red]")
    
    async def action_quick_buy_no(self) -> None:
        """Quick buy NO at best ask"""
        try:
            no_orderbook = self.query_one("#no_orderbook", OrderBookWidget)
            best_ask = no_orderbook.get_best_ask()
            
            if not best_ask:
                self.notify("No asks available for NO token", severity="warning")
                return
            
            price = best_ask[0]
            size = 10  # Default size
            
            self.log_output(f"[bold red]Quick buy NO @ {price} x {size}[/bold red]")
            await self.handle_command(f"buy NO {price} {size}")
            
        except Exception as e:
            self.log_output(f"[bold red]Quick buy error: {e}[/bold red]")
    
    async def action_refresh_balance(self) -> None:
        """Refresh wallet balance"""
        await self.update_balance()
        self.notify("Balance refreshed", severity="information")
    
    async def action_refresh_events(self) -> None:
        """Refresh football events list"""
        self.log_output("[bold yellow]Refreshing events...[/bold yellow]")
        await self.load_football_events()
        self.notify("Events refreshed", severity="information")
    
    async def action_update_score(self) -> None:
        """Prompt for manual score update"""
        self.notify("Enter score update command: score <home>-<away>", severity="information")
        self.log_output("[dim]Use command: score 2-1[/dim]")
    
    async def action_update_time(self) -> None:
        """Prompt for manual time update"""
        self.notify("Enter time update command: time <mm:ss>", severity="information")
        self.log_output("[dim]Use command: time 67:30[/dim]")
    
    def action_go_back(self) -> None:
        """Go back to home screen"""
        # Disconnect WebSocket
        try:
            if hasattr(self.app.core, 'websocket_manager'):
                self.app.core.websocket_manager.disconnect_all()
        except:
            pass
        
        self.app.pop_screen()
