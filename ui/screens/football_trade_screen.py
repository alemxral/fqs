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

# Import gamma-api utilities
try:
    from get_events_with_tags import get_events_with_tags
except ImportError:
    get_events_with_tags = None

# Import widgets
from ..widgets.football_widget import FootballWidget
from ..widgets.orderbook import OrderBookWidget
from ..widgets.command_input import CommandInput
from ..widgets.open_orders import OpenOrdersWidget
from ..widgets.price_ticker import PriceTickerWidget
from ..widgets.trade_history import TradeHistoryWidget
from ..widgets.position_summary import PositionSummaryWidget
from ..widgets.main_header import MainHeader
from .backend_logs_screen import BackendLogsScreen
from .commands_reference_screen import CommandsReferenceScreen

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
        Binding("ctrl+l", "show_logs", "Backend Logs", priority=True),
        Binding("ctrl+h", "show_commands", "Commands Help", priority=True),
        Binding("ctrl+s", "update_score", "Update Score", priority=True),
        Binding("ctrl+t", "update_time", "Update Time", priority=True),
    ]
    
    # Reactive balance
    balance = reactive(0.0)
    
    CSS = """
    FootballTradeScreen {
        background: $surface;
    }
    
    /* ========== MAIN LAYOUT ========== */
    #main_container {
        height: 1fr;
        layout: horizontal;
        margin-bottom: 9;
    }
    
    /* ========== LEFT PANEL (Events List) - 25% ========== */
    #events_panel {
        width: 25%;
        height: 100%;
        border-right: thick $primary;
        background: $panel;
        layout: vertical;
    }
    
    #events_header {
        height: 3;
        background: $primary;
        color: $text;
        text-style: bold;
        padding: 1;
        content-align: center middle;
        border-bottom: solid $accent;
    }
    
    #events_table {
        height: 1fr;
        border: none;
        background: $panel;
        scrollbar-size-vertical: 2;
    }
    
    DataTable {
        height: 100%;
    }
    
    DataTable > .datatable--header {
        background: $boost;
        color: $text;
        text-style: bold;
    }
    
    DataTable > .datatable--cursor {
        background: $accent;
        color: $text;
    }
    
    DataTable > .datatable--hover {
        background: $accent 50%;
    }
    
    /* ========== CENTER PANEL (Trading) - 45% ========== */
    #center_panel {
        width: 45%;
        height: 100%;
        layout: vertical;
        border-right: thick $primary;
        background: $surface;
    }
    
    #football_widget {
        height: auto;
        min-height: 12;
        max-height: 20;
        border-bottom: thick $secondary;
        background: $panel;
        padding: 1;
    }
    
    #orderbooks_container {
        height: 1fr;
        layout: horizontal;
        background: $surface;
    }
    
    .orderbook-side {
        width: 1fr;
        height: 100%;
        layout: vertical;
    }
    
    #yes_header {
        height: 3;
        background: $success;
        color: $text;
        text-style: bold;
        padding: 1;
        content-align: center middle;
    }
    
    #no_header {
        height: 3;
        background: $error;
        color: $text;
        text-style: bold;
        padding: 1;
        content-align: center middle;
    }
    
    #yes_orderbook {
        height: 1fr;
        border-right: solid $secondary;
        background: $panel;
        scrollbar-size-vertical: 2;
    }
    
    #no_orderbook {
        height: 1fr;
        background: $panel;
        scrollbar-size-vertical: 2;
    }
    
    /* ========== RIGHT PANEL (Widgets & Output) - 30% ========== */
    #output_panel {
        width: 30%;
        height: 100%;
        layout: vertical;
        background: $surface;
    }
    
    #output_header {
        height: 3;
        background: $accent;
        color: $text;
        text-style: bold;
        padding: 1;
        content-align: center middle;
        border-bottom: thick $primary;
    }
    
    /* Trading Widgets Section */
    #trading_widgets {
        height: 45%;
        layout: vertical;
        border-bottom: thick $primary;
        background: $boost;
        padding: 1;
        scrollbar-size-vertical: 2;
    }
    
    /* Individual Widget Styling */
    #price_ticker {
        height: auto;
        min-height: 6;
        margin-bottom: 1;
        border: solid $success;
        background: $panel;
        padding: 1;
        scrollbar-size-vertical: 1;
    }
    
    #open_orders {
        height: auto;
        min-height: 8;
        margin-bottom: 1;
        border: solid $warning;
        background: $panel;
        padding: 1;
        scrollbar-size-vertical: 1;
    }
    
    #position_summary {
        height: auto;
        min-height: 8;
        margin-bottom: 1;
        border: solid $accent;
        background: $panel;
        padding: 1;
        scrollbar-size-vertical: 1;
    }
    
    #trade_history {
        height: auto;
        min-height: 6;
        border: solid $secondary;
        background: $panel;
        padding: 1;
        scrollbar-size-vertical: 1;
    }
    
    /* Command Output Log */
    #command_output {
        height: 55%;
        background: $surface;
        border-top: solid $accent;
        padding: 1;
        scrollbar-size-vertical: 2;
    }
    
    /* ========== COMMAND INPUT (Bottom Fixed) ========== */
    #command_container {
        dock: bottom;
        height: 8;
        width: 100%;
        border-top: thick $accent;
        background: $boost;
        padding: 1;
        layer: overlay;
    }
    
    /* ========== FOOTER ========== */
    Footer {
        dock: bottom;
        height: 1;
        background: $boost;
        layer: overlay;
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


        
        # Create and store a reference to the header without kwargs
        self.header = MainHeader()  # no id, no expand
        yield self.header

        
        # Main 3-column layout: 30% | 40% | 30%
        with Container(id="main_container"):
            # ===== LEFT PANEL: Events List (30%) =====
            with Vertical(id="events_panel"):
                yield Static("⚽ Live Football Events", id="events_header")
                yield DataTable(id="events_table")
            
            # ===== CENTER PANEL: Trading Interface (40%) =====
            with Vertical(id="center_panel"):
                # Match widget with live data
                yield FootballWidget(id="football_widget")
                
                # Dual orderbook view (YES / NO)
                with Container(id="orderbooks_container"):
                    with Vertical(classes="orderbook-side"):
                        yield Static("📈 YES Orders", id="yes_header")
                        yield OrderBookWidget(id="yes_orderbook")
                    
                    with Vertical(classes="orderbook-side"):
                        yield Static("📉 NO Orders", id="no_header")
                        yield OrderBookWidget(id="no_orderbook")
            
            # ===== RIGHT PANEL: Widgets & Output (30%) =====
            with Vertical(id="output_panel"):
                yield Static("📊 Trading Dashboard", id="output_header")
                
                # Trading widgets section (top 45%)
                with Vertical(id="trading_widgets"):
                    yield PriceTickerWidget(id="price_ticker")
                    yield OpenOrdersWidget(id="open_orders")
                    yield PositionSummaryWidget(id="position_summary")
                    yield TradeHistoryWidget(id="trade_history")
                
                # Command output log (bottom 55%)
                yield RichLog(id="command_output", highlight=True, markup=True)


        
        # Bottom: Command input (fixed height)
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
                
                # Initialize widgets with token data
                try:
                    price_ticker = self.query_one("#price_ticker", PriceTickerWidget)
                    price_ticker.set_token(self.yes_token)
                    
                    open_orders = self.query_one("#open_orders", OpenOrdersWidget)
                    if hasattr(self.app.core, 'orders_manager'):
                        await open_orders.initialize(self.app.core.orders_manager)
                except Exception as e:
                    self.log_output(f"[yellow]Widget init warning: {e}[/yellow]")
                
                await self.connect_websocket()
        
        # Start widget refresh timers
        self.set_interval(5.0, self.refresh_orders_widget)
        self.set_interval(10.0, self.refresh_positions_widget)
    
    async def load_football_events(self) -> None:
        """Load live football events from Gamma API"""
        try:
            self.log_output("[yellow]Fetching live football events...[/yellow]")
            
            if get_events_with_tags is None:
                self.log_output("[red]Gamma API utilities not available[/red]")
                return
            
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
            
            # Update price ticker widget with latest orderbook
            try:
                price_ticker = self.query_one("#price_ticker", PriceTickerWidget)
                price_ticker.update_from_orderbook(data)
            except:
                pass  # Widget not available yet
                
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
        
        # Update trade history widget
        try:
            trade_history = self.query_one("#trade_history", TradeHistoryWidget)
            trade_history.add_trade_from_dict({
                "side": side,
                "price": float(price) if price != 'N/A' else 0,
                "size": float(size) if size != 'N/A' else 0,
                "token_id": token_id
            })
        except:
            pass  # Widget not available yet
    
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
    
    def action_show_logs(self) -> None:
        """Show backend logs viewer screen"""
        self.app.push_screen(BackendLogsScreen())
    
    def action_show_commands(self) -> None:
        """Show commands reference screen"""
        self.app.push_screen(CommandsReferenceScreen())
    
    def action_go_back(self) -> None:
        """Go back to home screen"""
        # Disconnect WebSocket
        try:
            if hasattr(self.app.core, 'websocket_manager'):
                self.app.core.websocket_manager.disconnect_all()
        except:
            pass
        
        self.app.pop_screen()
    
    async def refresh_orders_widget(self) -> None:
        """Refresh open orders widget"""
        try:
            orders_widget = self.query_one("#open_orders", OpenOrdersWidget)
            await orders_widget.refresh_orders()
        except Exception as e:
            pass  # Widget might not be ready
    
    async def refresh_positions_widget(self) -> None:
        """Refresh positions widget"""
        try:
            positions_widget = self.query_one("#position_summary", PositionSummaryWidget)
            await positions_widget.update_positions()
        except Exception as e:
            pass  # Widget might not be ready
