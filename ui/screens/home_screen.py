"""
Home Screen - Football Match Selector
Displays active football markets and allows selection for trading
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Header, Footer, ListView, ListItem, Static, LoadingIndicator
from textual.containers import Container, Vertical
from rich.text import Text
import asyncio


class FootballMatchItem(Static):
    """Display a single football match item"""
    
    def __init__(self, market_data: dict, *args, **kwargs):
        self.market_data = market_data
        super().__init__(*args, **kwargs)
        
    def on_mount(self) -> None:
        """Style and display market data"""
        question = self.market_data.get('question', 'Unknown Market')
        yes_price = self.market_data.get('yes_price', 0.5)
        no_price = self.market_data.get('no_price', 0.5)
        end_date = self.market_data.get('end_date', 'Unknown')
        
        # Format display
        text = Text()
        text.append(f"⚽ {question[:80]}\n", style="bold cyan")
        text.append(f"   YES: ", style="dim")
        text.append(f"{yes_price:.2%}", style="bold green")
        text.append(f" | NO: ", style="dim")
        text.append(f"{no_price:.2%}", style="bold red")
        text.append(f" | Ends: {end_date[:16]}", style="dim yellow")
        
        self.update(text)


class HomeScreen(Screen):
    """
    Home screen for selecting football matches to trade
    """
    
    BINDINGS = [
        Binding("escape", "go_back", "Back", priority=True),
        Binding("ctrl+r", "refresh_markets", "Refresh", priority=True),
        Binding("enter", "select_market", "Trade", priority=True),
    ]
    
    CSS = """
    HomeScreen {
        background: $surface;
    }
    
    #markets_container {
        height: 100%;
        border: solid $primary;
        background: $panel;
        padding: 1;
    }
    
    #markets_list {
        height: 100%;
        background: $panel;
    }
    
    #status_message {
        dock: bottom;
        height: 3;
        background: $boost;
        color: $text;
        text-align: center;
        padding: 1;
    }
    
    FootballMatchItem {
        height: 3;
        padding: 0 1;
        background: $panel;
        border: none;
    }
    
    FootballMatchItem:hover {
        background: $primary-darken-1;
    }
    
    ListView {
        background: $panel;
    }
    
    ListItem {
        background: $panel;
        height: auto;
    }
    
    ListItem:hover {
        background: $primary-darken-2;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.markets = []
        self.loading = False
    
    def compose(self) -> ComposeResult:
        """Create screen layout"""
        yield Header()
        
        with Container(id="markets_container"):
            yield Static("🏟️  Football Markets - Select a match to trade", id="title")
            yield ListView(id="markets_list")
            yield LoadingIndicator(id="loading")
        
        yield Static("Press ENTER to trade | CTRL+R to refresh | ESC to go back", id="status_message")
        yield Footer()
    
    async def on_mount(self) -> None:
        """Load markets on mount"""
        self.query_one("#loading", LoadingIndicator).display = False
        await self.load_markets()
    
    async def load_markets(self) -> None:
        """Fetch football markets from Flask API"""
        if self.loading:
            return
        
        self.loading = True
        loading_widget = self.query_one("#loading", LoadingIndicator)
        loading_widget.display = True
        
        markets_list = self.query_one("#markets_list", ListView)
        markets_list.clear()
        
        try:
            # Fetch from Flask API
            response = await self.app.api_client.get("/api/markets/football")
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                self.markets = data.get('markets', [])
                
                if not self.markets:
                    # Show message if no markets found
                    markets_list.append(ListItem(
                        Static("No active football markets found. Try refreshing later.")
                    ))
                else:
                    # Add each market to list
                    for market in self.markets:
                        markets_list.append(ListItem(
                            FootballMatchItem(market)
                        ))
                    
                    self.notify(f"Loaded {len(self.markets)} football markets", severity="information")
            else:
                error_msg = data.get('error', 'Unknown error')
                self.notify(f"Failed to load markets: {error_msg}", severity="error")
                markets_list.append(ListItem(
                    Static(f"Error: {error_msg}")
                ))
                
        except Exception as e:
            self.app.logger.error(f"Failed to load markets: {e}", exc_info=True)
            self.notify(f"Error loading markets: {str(e)}", severity="error")
            markets_list.append(ListItem(
                Static(f"Error loading markets: {str(e)}")
            ))
        finally:
            self.loading = False
            loading_widget.display = False
    
    async def action_refresh_markets(self) -> None:
        """Refresh market list"""
        self.notify("Refreshing markets...", severity="information")
        await self.load_markets()
    
    async def action_select_market(self) -> None:
        """Select highlighted market and navigate to trading screen"""
        markets_list = self.query_one("#markets_list", ListView)
        
        if markets_list.index is None or not self.markets:
            self.notify("No market selected", severity="warning")
            return
        
        try:
            selected_market = self.markets[markets_list.index]
            market_slug = selected_market.get('slug')
            
            if not market_slug:
                self.notify("Invalid market selected", severity="error")
                return
            
            # Fetch market details including token IDs
            self.notify(f"Loading market: {market_slug}", severity="information")
            
            response = await self.app.api_client.get(f"/api/market/{market_slug}")
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                market_details = data.get('market', {})
                
                # Store market data in app session for trading screen
                if not hasattr(self.app, 'session'):
                    self.app.session = {}
                
                self.app.session.update({
                    'market_slug': market_slug,
                    'market_question': market_details.get('question'),
                    'yes_token': market_details.get('tokens', {}).get('yes'),
                    'no_token': market_details.get('tokens', {}).get('no'),
                    'yes_price': market_details.get('prices', {}).get('yes'),
                    'no_price': market_details.get('prices', {}).get('no'),
                })
                
                # Navigate to trading screen
                from fqs.ui.screens.football_trade_screen import FootballTradeScreen
                self.app.push_screen(FootballTradeScreen())
                
            else:
                error_msg = data.get('error', 'Unknown error')
                self.notify(f"Failed to load market details: {error_msg}", severity="error")
                
        except Exception as e:
            self.app.logger.error(f"Failed to select market: {e}", exc_info=True)
            self.notify(f"Error: {str(e)}", severity="error")
    
    def action_go_back(self) -> None:
        """Go back to previous screen"""
        self.app.pop_screen()
