"""
Home Screen - Football Match Selector
Displays active football markets and allows selection for trading
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Header, Footer, DataTable, Static, LoadingIndicator, Label, Input, Button
from textual.containers import Container, Vertical, Horizontal
from textual.reactive import reactive
from rich.text import Text
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
import httpx


from ..widgets.main_header import MainHeader  # ← the MainHeader being imported (may be the wrong file)
from .backend_logs_screen import BackendLogsScreen
from .commands_reference_screen import CommandsReferenceScreen
from ..widgets.command_input import CommandInput

# Add utils path for direct market access
utils_path = Path(__file__).parent.parent.parent / "fqs" / "utils" / "gamma-api"
if str(utils_path) not in sys.path:
    sys.path.insert(0, str(utils_path))

try:
    from get_events_with_tags import get_events_with_tags
    from get_markets_by_slug import get_markets_by_slug
    from get_sports_metadata import get_all_sports_tags, get_sports_metadata
    GAMMA_API_AVAILABLE = True
except ImportError:
    GAMMA_API_AVAILABLE = False

# Data cache path
DATA_DIR = Path(__file__).parent.parent.parent / "data"
MARKETS_CACHE = DATA_DIR / "all_active_markets.json"
FOOTBALL_CACHE = DATA_DIR / "live_football_matches.json"  # Backend startup cache


class LeagueHeader(Static):
    """Display league/category header with match count"""
    
    def __init__(self, league_name: str, match_count: int = 0, icon: str = "🏆", *args, **kwargs):
        self.league_name = league_name
        self.match_count = match_count
        self.icon = icon
        super().__init__(*args, **kwargs)
        self.add_class("league-header")
    
    def on_mount(self) -> None:
        """Display league header"""
        text = Text()
        text.append(f"{self.icon} {self.league_name}", style="bold cyan")
        text.append(f" ({self.match_count} markets)", style="dim")
        self.update(text)


class MarketCard(Static):
    """Display a single market as a card with enhanced info"""
    
    def __init__(self, market_data: dict, sport_icon: str = "⚽", *args, **kwargs):
        self.market_data = market_data
        self.sport_icon = sport_icon
        super().__init__(*args, **kwargs)
        self.add_class("market-card")
        
    def on_mount(self) -> None:
        """Style and display market data"""
        question = self.market_data.get('question', 'Unknown Market')
        yes_price = self.market_data.get('yes_price', 0.5)
        no_price = self.market_data.get('no_price', 0.5)
        end_date = self.market_data.get('end_date', 'Unknown')
        
        # Check if live or ending soon
        status = ""
        event = self.market_data.get('event', {})
        if event.get('active') and not event.get('closed'):
            status = "[bold red]● LIVE[/] "
        
        # Format display with better structure
        text = Text()
        text.append(f"{self.sport_icon} ", style="bold")
        if status:
            text.append("● LIVE ", style="bold red")
        text.append(f"{question[:75]}\n", style="bold white")
        text.append(f"   YES: ", style="dim")
        text.append(f"{yes_price:.1%}", style="bold green")
        text.append(f"  NO: ", style="dim")
        text.append(f"{no_price:.1%}", style="bold red")
        text.append(f"  │  Ends: {end_date[:16]}", style="dim cyan")
        
        self.update(text)


class FootballMatchItem(Static):
    """Display a single football match item (legacy, kept for compatibility)"""
    
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
        Binding("ctrl+f", "quick_trade", "Quick Trade", priority=True),
        Binding("ctrl+l", "show_logs", "Backend Logs", priority=True),
        Binding("ctrl+h", "show_commands", "Commands Help", priority=True),
        # Removed Enter binding to avoid conflicts with command input and search
        # Use double-click on table row or CTRL+F for quick trade instead
    ]
    
    # Reactive balance
    balance = reactive(0.0)
    
    CSS = """
    HomeScreen {
        background: $surface;
    }
    
    #header_info {
        height: 3;
        width: 100%;
        background: $boost;
        border: tall $primary;
        padding: 0 2;
    }
    
    #filter_bar {
        height: 4;
        width: 100%;
        background: $surface;
        border: solid $accent;
        padding: 1;
    }
    
    .filter-btn {
        margin: 0 1;
        min-width: 12;
        height: 2;
    }
    
    .filter-btn.active {
        background: $accent;
        color: $text;
        text-style: bold;
    }
    
    #balance_label {
        color: $success;
        text-style: bold;
    }
    
    #search_input {
        dock: top;
        height: 3;
        width: 100%;
        border: solid $accent;
        background: $surface;
        padding: 0 1;
    }
    
    #search_input:focus {
        border: tall $success;
    }
    
    #markets_container {
        height: 1fr;
        border: solid $primary;
        background: $panel;
        overflow-y: auto;
        overflow-x: auto;
        scrollbar-size-vertical: 2;
        scrollbar-size-horizontal: 1;
    }
    
    #markets_table {
        background: $panel;
        border: none;
        max-height: 100%;
        width: 100%;
        min-width: 100%;
    }
    
    #status_message {
        dock: bottom;
        height: 3;
        background: $boost;
        color: $text;
        text-align: center;
        padding: 1;
    }
    
    DataTable > .datatable--header {
        background: $boost;
        color: $text;
        text-style: bold;
        height: 3;
    }
    
    DataTable > .datatable--cursor {
        background: $accent;
        color: $text;
    }
    
    DataTable > .datatable--hover {
        background: $accent 50%;
    }
    
    DataTable:focus > .datatable--cursor {
        background: $accent;
        text-style: bold;
    }
    
    /* Make rows appear clickable and properly sized */
    DataTable {
        height: 1fr;
        min-height: 10;
    }
    
    DataTable .datatable--row {
        height: auto;
        min-height: 3;
    }
    
    DataTable .datatable--fixed {
        background: $boost;
    }
    
    #action_buttons {
        height: 4;
        width: 100%;
        align: center middle;
        padding: 1 2;
        background: $surface;
    }
    
    .action-btn {
        margin: 0 2;
        min-width: 20;
        height: 3;
    }
    
    #command_input {
        dock: bottom;
        height: 3;
        width: 100%;
        border: solid $accent;
        background: $surface;
        padding: 0 1;
    }
    
    #command_input:focus {
        border: tall $warning;
    }
    
    Footer {
        dock: bottom;
        height: 1;
        background: $boost;
        layer: overlay;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.markets = []  # List of market dicts with all data
        self.filtered_markets = []  # Filtered markets for display
        self.loading = False
        self.search_tag = "football"  # Default search
        self.sports_tags = {}  # {sport_code: [tag_ids]}
        self.sports_metadata = []  # Full sports metadata from /sports
        self.active_filter = "football"  # Current filter
        self.http_client = None  # httpx async client
    
    async def _init_http_client(self) -> None:
        """Initialize async HTTP client"""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=15.0)
    
    async def _fetch_events_async(self, tag_id: int, limit: int = 50) -> list:
        """Fetch events from Gamma API using async httpx"""
        await self._init_http_client()
        
        try:
            response = await self.http_client.get(
                "https://gamma-api.polymarket.com/events",
                params={
                    'tag_id': tag_id,
                    'limit': limit,
                    'closed': 'false',
                    'order': 'id',
                    'ascending': 'false'
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            self.notify("API timeout, using cached data", severity="warning")
            return []
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                self.notify("Rate limited, please wait", severity="error")
                await asyncio.sleep(5)
            return []
        except Exception as e:
            self.app.logger.error(f"Fetch error: {e}")
            return []
    
    async def _fetch_market_details_async(self, market_slug: str) -> list:
        """Fetch market details using async httpx"""
        await self._init_http_client()
        
        try:
            response = await self.http_client.get(
                f"https://gamma-api.polymarket.com/markets/{market_slug}"
            )
            response.raise_for_status()
            data = response.json()
            return [data] if isinstance(data, dict) else data
        except Exception as e:
            self.app.logger.error(f"Failed to fetch market {market_slug}: {e}")
            return []
    
    def _load_cached_markets(self) -> list:
        """Load markets from cached JSON file"""
        try:
            if MARKETS_CACHE.exists():
                with open(MARKETS_CACHE, 'r') as f:
                    data = json.load(f)
                    markets_list = data.get('markets', [])
                    self.app.logger.info(f"Loaded {len(markets_list)} markets from cache")
                    return markets_list
        except Exception as e:
            self.app.logger.error(f"Failed to load cache: {e}")
        return []
    
    def _load_football_matches_from_cache(self) -> list:
        """Load football matches from backend startup cache"""
        try:
            if FOOTBALL_CACHE.exists():
                with open(FOOTBALL_CACHE, 'r') as f:
                    data = json.load(f)
                    matches = data.get('matches', {})
                    
                    # Convert dict of matches to list format compatible with table
                    markets_list = []
                    for slug, match_data in matches.items():
                        # Extract first market from the event
                        event_markets = match_data.get('markets', [])
                        if not event_markets:
                            continue
                        
                        first_market = event_markets[0]
                        
                        # Extract YES/NO prices from tokens
                        yes_price = 0.5
                        no_price = 0.5
                        clobTokenIds = first_market.get('clobTokenIds', '[]')
                        outcomePrices = first_market.get('outcomePrices', '[]')
                        
                        try:
                            prices = json.loads(outcomePrices) if isinstance(outcomePrices, str) else outcomePrices
                            if len(prices) >= 2:
                                yes_price = float(prices[0])
                                no_price = float(prices[1])
                        except:
                            pass
                        
                        market_entry = {
                            'slug': first_market.get('slug', slug),
                            'event_slug': slug,
                            'question': first_market.get('question', match_data.get('title', 'Unknown')),
                            'start_date': match_data.get('startDate', ''),
                            'end_date': first_market.get('endDate', match_data.get('endDate', '')),
                            'yes_price': yes_price,
                            'no_price': no_price,
                            'event': match_data  # Store full event data
                        }
                        markets_list.append(market_entry)
                    
                    self.app.logger.info(f"Loaded {len(markets_list)} football matches from backend cache")
                    return markets_list
                    
            else:
                self.app.logger.warning(f"Football cache not found: {FOOTBALL_CACHE}")
        except Exception as e:
            self.app.logger.error(f"Failed to load football cache: {e}")
        return []
    
    def _save_markets_cache(self, markets: list) -> None:
        """Save markets to cache file"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            cache_data = {
                "metadata": {
                    "total_markets": len(markets),
                    "extraction_timestamp": datetime.now().isoformat(),
                    "source": "Gamma API (HomeScreen)"
                },
                "markets": markets
            }
            with open(MARKETS_CACHE, 'w') as f:
                json.dump(cache_data, f, indent=2)
            self.app.logger.info(f"Saved {len(markets)} markets to cache")
        except Exception as e:
            self.app.logger.error(f"Failed to save cache: {e}")
    
    def compose(self) -> ComposeResult:
        # Create and store a reference to the header without kwargs
        self.header = MainHeader()  # no id, no expand
        yield self.header

        # Search box - docked to top
        yield Input(placeholder="🔍 Search Match/Slug (partial match, case-insensitive)", id="search_input", value="")
        
        # Markets table - takes remaining space
        with Container(id="markets_container"):
            yield LoadingIndicator(id="loading")
            yield DataTable(id="markets_table", zebra_stripes=True)
        
        # Command input - docked to bottom
        yield CommandInput(
            command_handler=self.handle_command,
            id="command_input",
            placeholder="⌨️ Enter command (type 'help' for available commands)"
        )
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Load markets on mount"""
        self.query_one("#loading", LoadingIndicator).display = False
        
        # Setup markets table with proper columns
        markets_table = self.query_one("#markets_table", DataTable)
        markets_table.add_columns(
            "🔴",  # Status indicator
            "🏆 Match",
            "📅 Date/Time",
            "✅ YES",
            "❌ NO",
            "📊 Volume",
            "🔗 Slug"
        )
        markets_table.cursor_type = "row"
        markets_table.zebra_stripes = True
        
        # Start balance refresh timer (every 30 seconds)
        self.set_interval(30.0, self.update_balance)
        
        # Initial balance fetch
        await self.update_balance()
        
        # Load sports metadata and tags
        if GAMMA_API_AVAILABLE:
            try:
                # Load sports tags asynchronously
                self.sports_tags = await asyncio.get_event_loop().run_in_executor(
                    None, get_all_sports_tags
                )
                self.sports_metadata = await asyncio.get_event_loop().run_in_executor(
                    None, get_sports_metadata
                )
                self.app.logger.info(f"Loaded {len(self.sports_tags)} sports tags")
                
                # Log available tag IDs
                for sport, tags in self.sports_tags.items():
                    self.app.logger.info(f"  {sport}: {tags}")
            except Exception as e:
                self.app.logger.error(f"Failed to load sports tags: {e}")
        
        # PRIORITY 1: Load from backend startup cache (live_football_matches.json)
        football_matches = self._load_football_matches_from_cache()
        if football_matches:
            self.markets = football_matches  # Load all available matches
            self.filtered_markets = self.markets  # Initialize filtered markets
            self._populate_markets_table()
            self.notify(f"Loaded {len(self.markets)} football matches from cache", severity="information")
        else:
            # FALLBACK: Load from old cache or API
            self.app.logger.info("Football cache unavailable, trying fallback")
            cached_markets = self._load_cached_markets()
            if cached_markets:
                # Filter for football only from cache
                self.markets = [
                    m for m in cached_markets
                    if any(x in m.get('question', '').lower() 
                          for x in ['football', 'soccer', 'premier', 'liga', 'serie', 'bundesliga'])
                ]  # Load all available football matches
                self.filtered_markets = self.markets  # Initialize filtered markets
                self._populate_markets_table()
                self.notify(f"Loaded {len(self.markets)} cached markets", severity="information")
            else:
                # Last resort: fetch from API
                await self.load_multiple_leagues()
    
    async def update_balance(self) -> None:
        """Update balance display from Flask API (which fetches from blockchain and caches to JSON)"""
        try:
            # Fetch from Flask API - it uses blockchain utilities and caches to JSON
            if hasattr(self.app, 'api_client'):
                try:
                    response = await self.app.api_client.get("/api/balance")
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            self.balance = data.get('balance', 0.0)
                            derived_balance = data.get('derived_balance', 0.0)
                            proxy_balance = data.get('proxy_balance', 0.0)
                            
                            # Update header if it exists
                            if hasattr(self, 'header'):
                                self.header.update_balances(derived_balance, proxy_balance)
                            
                            cached = " (cached)" if data.get('cached') else ""
                            self.app.logger.info(
                                f"Balance updated{cached}: ${self.balance:.2f} USDC "
                                f"(Derived: ${derived_balance:.2f}, Proxy: ${proxy_balance:.2f})"
                            )
                            return
                        else:
                            self.app.logger.warning(f"Balance API returned error: {data.get('error')}")
                    else:
                        self.app.logger.warning(f"Balance API returned status {response.status_code}")
                        
                except Exception as api_error:
                    self.app.logger.warning(f"Flask API not available: {api_error}")
            
            # If API fails, keep existing balance
            self.app.logger.warning("Could not update balance, keeping cached value")
            
        except Exception as e:
            self.app.logger.error(f"Failed to update balance: {e}", exc_info=True)
    
    def get_sport_icon(self, sport_code: str) -> str:
        """Get emoji icon for sport"""
        icons = {
            'epl': '⚽', 'lal': '⚽', 'bun': '⚽', 'sea': '⚽', 'fl1': '⚽', 'ucl': '🏆', 'uel': '🏆',
            'mls': '⚽', 'nfl': '🏈', 'nba': '🏀', 'ncaab': '🏀', 'nhl': '🏒', 'mlb': '⚾',
            'lol': '🎮', 'dota2': '🎮', 'cs2': '🎮', 'val': '🎮',
            'atp': '🎾', 'wta': '🎾', 'ipl': '🏏', 'mma': '🥊'
        }
        return icons.get(sport_code.lower(), '🏆')
    
    def get_league_name(self, sport_code: str) -> str:
        """Get full league name from code"""
        names = {
            'epl': 'Premier League', 'lal': 'La Liga', 'bun': 'Bundesliga', 
            'sea': 'Serie A', 'fl1': 'Ligue 1', 'ucl': 'Champions League',
            'uel': 'Europa League', 'mls': 'MLS', 'nfl': 'NFL', 'nba': 'NBA',
            'ncaab': 'NCAA Basketball', 'nhl': 'NHL', 'mlb': 'MLB',
            'lol': 'League of Legends', 'dota2': 'Dota 2', 'cs2': 'CS2', 
            'val': 'Valorant', 'atp': 'ATP Tennis', 'wta': 'WTA Tennis',
            'ipl': 'IPL Cricket', 'mma': 'MMA'
        }
        return names.get(sport_code.lower(), sport_code.upper())
    
    def get_sport_type(self, league_code: str) -> str:
        """Get sport category from league code"""
        football = ['epl', 'lal', 'bun', 'sea', 'fl1', 'ucl', 'uel', 'mls']
        basketball = ['nba', 'ncaab', 'wnba']
        nfl = ['nfl', 'cfb']
        hockey = ['nhl', 'khl', 'ahl']
        esports = ['lol', 'dota2', 'cs2', 'val']
        
        league = league_code.lower()
        if league in football:
            return 'football'
        elif league in basketball:
            return 'basketball'
        elif league in nfl:
            return 'nfl'
        elif league in hockey:
            return 'hockey'
        elif league in esports:
            return 'esports'
        return 'other'
    
    async def load_multiple_leagues(self) -> None:
        """Load markets using proper tag IDs with async API calls"""
        if self.loading:
            return
        
        self.loading = True
        loading_widget = self.query_one("#loading", LoadingIndicator)
        loading_widget.display = True
        
        if not GAMMA_API_AVAILABLE:
            self.notify("Gamma API not available", severity="error")
            self.loading = False
            loading_widget.display = False
            return
        
        try:
            # Get football tag IDs from sports metadata
            football_tags = self.sports_tags.get('football', [100350])  # Fallback to 100350
            tag_id = football_tags[0] if football_tags else 100350
            
            self.app.logger.info(f"Fetching events with tag {tag_id}")
            
            # Use async httpx client
            events_data = await self._fetch_events_async(tag_id, limit=50)
            
            if not events_data:
                self.notify("No markets found", severity="warning")
                self.loading = False
                loading_widget.display = False
                return
            
            # Process and deduplicate events
            self.markets = []
            seen_slugs = set()
            
            for event in events_data:
                slug = event.get('slug', '')
                if not slug or slug in seen_slugs:
                    continue  # Skip duplicates
                
                seen_slugs.add(slug)
                
                # Extract market data
                title = event.get('title', 'Unknown')
                start_date = event.get('start_date_min', '')
                end_date = event.get('end_date_min', '')
                
                # Format dates
                start_str = self._format_date(start_date)
                end_str = self._format_date(end_date)
                
                # Get first market for YES/NO prices
                markets = event.get('markets', [])
                yes_price = 0.5
                no_price = 0.5
                market_slug = slug
                
                if markets and len(markets) > 0:
                    first_market = markets[0]
                    market_slug = first_market.get('slug', slug)
                    
                    # Extract token IDs and outcomes
                    tokens = first_market.get('tokens', [])
                    for token in tokens:
                        outcome = token.get('outcome', '').lower()
                        price = token.get('price', 0.5)
                        if 'yes' in outcome:
                            yes_price = price
                        elif 'no' in outcome:
                            no_price = price
                
                market_data = {
                    'slug': market_slug,
                    'event_slug': slug,
                    'question': title,
                    'start_date': start_date,
                    'end_date': end_date,
                    'yes_price': yes_price,
                    'no_price': no_price,
                    'event': event
                }
                self.markets.append(market_data)
            
            # Populate DataTable
            self.filtered_markets = self.markets  # Initialize filtered markets
            self._populate_markets_table()
            
            # Save to cache for next launch
            self._save_markets_cache(self.markets)
            
            self.notify(f"Loaded {len(self.markets)} unique markets", severity="information")
            
        except Exception as e:
            self.app.logger.error(f"Failed to load markets: {e}", exc_info=True)
            self.notify(f"Error loading markets: {str(e)}", severity="error")
        finally:
            self.loading = False
            loading_widget.display = False
    
    def _format_date(self, date_str: str) -> str:
        """Format ISO date to readable string"""
        if not date_str:
            return "TBD"
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%m/%d %H:%M")
        except:
            return date_str[:16]
    
    def _populate_markets_table(self) -> None:
        """Populate DataTable with market data"""
        markets_table = self.query_one("#markets_table", DataTable)
        markets_table.clear()
        
        # Use filtered_markets if available, otherwise use all markets
        markets_to_display = self.filtered_markets if self.filtered_markets else self.markets
        
        # Sort markets by end_date (soonest first)
        try:
            sorted_markets = sorted(
                markets_to_display,
                key=lambda m: m.get('end_date', '9999-12-31'),
                reverse=False  # Ascending order - soonest games first
            )
        except Exception as e:
            self.app.logger.warning(f"Could not sort markets: {e}")
            sorted_markets = markets_to_display
        
        for market in sorted_markets:
            # Extract event data for volume and status
            event = market.get('event', {})
            
            # Status indicator - check if live
            is_live = event.get('active', False) and not event.get('closed', False)
            status_icon = "🔴" if is_live else "⏰"
            
            # Match name - truncate intelligently
            match_name = market.get('question', 'Unknown')
            if len(match_name) > 55:
                match_name = match_name[:52] + "..."
            
            # Date/Time - show end date formatted
            end_date = market.get('end_date', '')
            datetime_str = self._format_date(end_date)
            
            # YES/NO prices with color formatting
            yes_price = market.get('yes_price', 0.5)
            no_price = market.get('no_price', 0.5)
            yes_str = f"[green]{yes_price:.1%}[/green]"
            no_str = f"[red]{no_price:.1%}[/red]"
            
            # Volume - format with K/M suffixes
            volume = event.get('volume', 0)
            if volume >= 1000000:
                volume_str = f"${volume/1000000:.1f}M"
            elif volume >= 1000:
                volume_str = f"${volume/1000:.1f}K"
            else:
                volume_str = f"${volume:.0f}"
            
            # Slug - truncate for display
            slug = market.get('slug', '')
            if len(slug) > 25:
                slug = slug[:22] + "..."
            
            markets_table.add_row(
                status_icon,
                match_name,
                datetime_str,
                yes_str,
                no_str,
                volume_str,
                slug,
                key=market.get('slug', '')
            )
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle filter button presses"""
        button_id = event.button.id
        
        # Check for backend logs button
        if button_id == "btn_show_logs":
            self.action_show_logs()
            return
        
        # Update active button styling
        for btn in self.query(".filter-btn"):
            btn.remove_class("active")
        event.button.add_class("active")
        
        # Apply filter and reload markets
        if button_id == "filter_all":
            self.active_filter = "all"
            await self.load_multiple_leagues()
        elif button_id == "filter_football":
            self.active_filter = "football"
            await self.load_markets_by_tag("football")
        elif button_id == "filter_basketball":
            self.active_filter = "basketball"
            await self.load_markets_by_tag("basketball")
        elif button_id == "filter_nfl":
            self.active_filter = "nfl"
            await self.load_markets_by_tag("nfl")
        elif button_id == "filter_hockey":
            self.active_filter = "hockey"
            await self.load_markets_by_tag("hockey")
        elif button_id == "filter_esports":
            self.active_filter = "esports"
            await self.load_markets_by_tag("esports")
        
        self.notify(f"Filter: {self.active_filter.title()}", severity="information")
    
    async def load_markets_by_tag(self, tag: str = "football") -> None:
        """Load markets by tag using proper tag IDs with async API calls"""
        if self.loading:
            return
        
        self.loading = True
        loading_widget = self.query_one("#loading", LoadingIndicator)
        loading_widget.display = True
        
        try:
            if not GAMMA_API_AVAILABLE:
                self.notify("Gamma API not available", severity="error")
                self.loading = False
                loading_widget.display = False
                return
            
            # Get proper tag IDs from sports metadata
            sport_tags = self.sports_tags.get(tag.lower(), [])
            
            if not sport_tags:
                # Fallback to hardcoded values
                fallback_tags = {
                    'football': [100350],
                    'basketball': [100349],
                    'nfl': [100347],
                    'hockey': [100348],
                    'esports': [100346],
                    'all': [1]
                }
                sport_tags = fallback_tags.get(tag.lower(), [1])
            
            tag_id = sport_tags[0]
            self.app.logger.info(f"Loading {tag} markets with tag {tag_id}")
            
            # Use async httpx client
            events_data = await self._fetch_events_async(tag_id, limit=50)
            
            if not events_data:
                self.notify(f"No markets found for {tag}", severity="warning")
                self.markets = []
                self._populate_markets_table()
                return
            
            # Process events (no manual filtering needed with proper tags)
            self.markets = []
            seen_slugs = set()
            
            for event in events_data:
                slug = event.get('slug', '')
                if not slug or slug in seen_slugs:
                    continue
                
                seen_slugs.add(slug)
                
                # Extract data
                title = event.get('title', 'Unknown')
                start_date = event.get('start_date_min', '')
                end_date = event.get('end_date_min', '')
                
                # Get prices from first market
                markets = event.get('markets', [])
                yes_price = 0.5
                no_price = 0.5
                market_slug = slug
                
                if markets:
                    first_market = markets[0]
                    market_slug = first_market.get('slug', slug)
                    tokens = first_market.get('tokens', [])
                    
                    for token in tokens:
                        outcome = token.get('outcome', '').lower()
                        price = token.get('price', 0.5)
                        if 'yes' in outcome:
                            yes_price = price
                        elif 'no' in outcome:
                            no_price = price
                
                self.markets.append({
                    'slug': market_slug,
                    'event_slug': slug,
                    'question': title,
                    'start_date': start_date,
                    'end_date': end_date,
                    'yes_price': yes_price,
                    'no_price': no_price,
                    'event': event
                })
            
            # Update table
            self.filtered_markets = self.markets  # Initialize filtered markets
            self._populate_markets_table()
            
            # Save to cache
            self._save_markets_cache(self.markets)
            
            self.notify(f"Loaded {len(self.markets)} {tag} markets", severity="information")
            
        except Exception as e:
            self.app.logger.error(f"Failed to load markets: {e}", exc_info=True)
            self.notify(f"Error: {str(e)}", severity="error")
        finally:
            self.loading = False
            loading_widget.display = False
    
    async def action_refresh_markets(self) -> None:
        """Refresh market list"""
        search_input = self.query_one("#search_input", Input)
        tag = search_input.value.strip() or "football"
        self.notify(f"Refreshing {tag} markets...", severity="information")
        await self.load_markets_by_tag(tag)
    
    def action_show_logs(self) -> None:
        """Show backend logs viewer screen"""
        self.app.push_screen(BackendLogsScreen())
    
    def action_show_commands(self) -> None:
        """Show commands reference screen"""
        self.app.push_screen(CommandsReferenceScreen())
    
    async def action_search_markets(self) -> None:
        """Focus search input for new search"""
        search_input = self.query_one("#search_input", Input)
        search_input.focus()
        self.notify("Enter tag and press Enter to search", severity="information")
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission"""
        if event.input.id == "search_input":
            search_text = event.value.strip().lower()
            self._filter_markets(search_text)
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle real-time search filtering as user types"""
        if event.input.id == "search_input":
            search_text = event.value.strip().lower()
            self._filter_markets(search_text)
    
    def _filter_markets(self, search_text: str) -> None:
        """Filter markets by partial match on question or slug (case-insensitive)"""
        if not search_text:
            # Empty search - show all markets
            self.filtered_markets = self.markets
        else:
            # Filter markets where search_text appears in question or slug
            self.filtered_markets = [
                m for m in self.markets
                if search_text in m.get('question', '').lower() or 
                   search_text in m.get('slug', '').lower()
            ]
        
        # Repopulate table with filtered results
        self._populate_markets_table()
        
        # Show count in notification
        count = len(self.filtered_markets)
        if search_text:
            self.notify(f"Found {count} match(es) for '{search_text}'", severity="information")
    
    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (clicking on a row) in DataTable"""
        try:
            # Get the row key from the event
            row_key = event.row_key
            
            if not row_key or not self.markets:
                return
            
            # Find the market by slug (row_key is the slug)
            selected_market = None
            for market in self.markets:
                if market.get('slug') == row_key.value:
                    selected_market = market
                    break
            
            if not selected_market:
                # Fallback: try using cursor row index
                markets_table = self.query_one("#markets_table", DataTable)
                if markets_table.cursor_row is not None and markets_table.cursor_row < len(self.markets):
                    selected_market = self.markets[markets_table.cursor_row]
            
            if selected_market:
                market_slug = selected_market.get('slug')
                if market_slug:
                    # Load and navigate to market
                    await self._load_and_navigate_market(selected_market, market_slug)
                    
        except Exception as e:
            self.app.logger.error(f"Failed to handle row selection: {e}", exc_info=True)
            self.notify(f"Error selecting market: {str(e)}", severity="error")
    
    async def action_select_market(self) -> None:
        """Select highlighted market and navigate to trading screen"""
        markets_table = self.query_one("#markets_table", DataTable)
        
        if markets_table.cursor_row is None or not self.markets:
            self.notify("No market selected", severity="warning")
            return
        
        try:
            # Use cursor row index directly (most reliable)
            if markets_table.cursor_row >= len(self.markets):
                self.notify("Invalid market index", severity="error")
                return
            
            selected_market = self.markets[markets_table.cursor_row]
            market_slug = selected_market.get('slug')
            
            if not market_slug:
                self.notify("Invalid market slug", severity="error")
                return
            
            # Load market using this helper
            await self._load_and_navigate_market(selected_market, market_slug)
                
        except Exception as e:
            self.app.logger.error(f"Failed to select market: {e}", exc_info=True)
            self.notify(f"Error: {str(e)}", severity="error")
    
    async def _load_and_navigate_market(self, selected_market: dict, market_slug: str) -> None:
        """Helper to load market details and navigate to trade screen"""
        self.notify(f"Loading market: {market_slug[:30]}...", severity="information")
        
        # Try to use get_events_by_slug utility first
        market_details = None
        event_slug = selected_market.get('event_slug', market_slug)
        
        if GAMMA_API_AVAILABLE:
            try:
                # Import the utility function
                from get_events_by_slug import get_events_by_slug
                
                # Get event data by slug
                self.app.logger.info(f"Fetching event by slug: {event_slug}")
                event_data = await asyncio.get_event_loop().run_in_executor(
                    None, get_events_by_slug, event_slug
                )
                
                if event_data and len(event_data) > 0:
                    event = event_data[0]
                    markets = event.get('markets', [])
                    
                    # Find the specific market or use first one
                    for mkt in markets:
                        if mkt.get('slug') == market_slug:
                            market_details = [mkt]
                            break
                    
                    if not market_details and markets:
                        market_details = [markets[0]]
                        self.app.logger.info(f"Using first market from event")
                else:
                    self.app.logger.warning(f"No event data from get_events_by_slug")
                    
            except Exception as e:
                self.app.logger.error(f"Error using get_events_by_slug: {e}")
        
        # Fallback: try async httpx client
        if not market_details:
            self.app.logger.info("Trying httpx fallback for market details")
            market_details = await self._fetch_market_details_async(market_slug)
        
        # Extract token IDs if we have market details
        yes_token = None
        no_token = None
        
        if market_details and len(market_details) > 0:
            market_info = market_details[0]
            
            # Extract token IDs
            tokens = market_info.get('tokens', [])
            for token in tokens:
                outcome = token.get('outcome', '').lower()
                if 'yes' in outcome:
                    yes_token = token.get('token_id')
                elif 'no' in outcome:
                    no_token = token.get('token_id')
            
            # Also try clobTokenIds if tokens field is empty
            if not yes_token and not no_token:
                clob_tokens = market_info.get('clobTokenIds', '')
                try:
                    if isinstance(clob_tokens, str):
                        token_ids = json.loads(clob_tokens)
                    else:
                        token_ids = clob_tokens
                    
                    if isinstance(token_ids, list) and len(token_ids) >= 2:
                        yes_token = str(token_ids[0])
                        no_token = str(token_ids[1])
                        self.app.logger.info(f"Extracted tokens from clobTokenIds")
                except Exception as e:
                    self.app.logger.error(f"Error parsing clobTokenIds: {e}")
        
        # Even without full market details, try to navigate with what we have
        # Store in app session
        if not hasattr(self.app, 'session'):
            self.app.session = {}
        
        self.app.session.update({
            'market_slug': market_slug,
            'event_slug': event_slug,
            'market_question': selected_market.get('question', 'Unknown Market'),
            'yes_token': yes_token,
            'no_token': no_token,
            'yes_price': selected_market.get('yes_price', 0.5),
            'no_price': selected_market.get('no_price', 0.5),
        })
        
        if yes_token and no_token:
            self.app.logger.info(f"Navigating to trade screen for {market_slug}")
            self.app.logger.info(f"  YES token: {yes_token}")
            self.app.logger.info(f"  NO token: {no_token}")
        else:
            self.app.logger.warning(f"Missing token IDs, but proceeding to trade screen")
            self.notify("Token IDs not found, limited functionality", severity="warning")
        
        # Navigate to trading screen
        from fqs.ui.screens.football_trade_screen import FootballTradeScreen
        self.app.push_screen(FootballTradeScreen())
    
    async def action_quick_trade(self) -> None:
        """Quick trade: Launch FootballTradeScreen with first live market (bypass selection)"""
        if not self.markets:
            self.notify("No markets loaded. Loading now...", severity="warning")
            await self.load_multiple_leagues()
            
            if not self.markets:
                self.notify("No markets available", severity="error")
                return
        
        # Find first live market (with earliest end date)
        live_markets = [
            m for m in self.markets
            if m.get('end_date') and datetime.fromisoformat(m['end_date'].replace('Z', '+00:00')) > datetime.now(datetime.fromisoformat(m['end_date'].replace('Z', '+00:00')).tzinfo)
        ]
        
        if not live_markets:
            # Fallback to first market
            selected_market = self.markets[0]
        else:
            # Sort by end date (soonest first)
            live_markets.sort(key=lambda m: m.get('end_date', ''))
            selected_market = live_markets[0]
        
        market_slug = selected_market.get('slug')
        self.notify(f"Quick trade: {selected_market.get('question', 'Unknown')[:50]}", severity="information")
        
        await self._load_and_navigate_market(selected_market, market_slug)
    
    async def handle_command(self, command: str) -> None:
        """Handle commands from command input"""
        self.app.logger.info(f"HomeScreen command: {command}")
        
        # Check for LOOK command
        if command.strip().upper().startswith('LOOK '):
            slug = command.strip()[5:].strip()  # Extract slug after "LOOK "
            if slug:
                await self._load_market_by_slug(slug)
                return
            else:
                self.notify("Usage: LOOK <slug>", severity="warning")
                return
        
        # Submit to commands manager if available
        try:
            if hasattr(self.app, 'commands_manager'):
                await self.app.commands_manager.submit(
                    origin="HomeScreen",
                    command=command
                )
                self.notify(f"Command submitted: {command}", severity="information")
            else:
                self.notify("Commands manager not available", severity="warning")
        except Exception as e:
            self.app.logger.error(f"Command error: {e}")
            self.notify(f"Command error: {str(e)}", severity="error")
    
    async def _load_market_by_slug(self, slug: str) -> None:
        """Load a specific market by slug and add to table if not already present"""
        self.notify(f"Looking up: {slug}", severity="information")
        
        # Check if already in markets
        for market in self.markets:
            if market.get('slug') == slug or market.get('event_slug') == slug:
                self.notify(f"Market already loaded: {slug}", severity="information")
                # Navigate to it
                await self._load_and_navigate_market(market, market.get('slug'))
                return
        
        # Try to fetch using get_events_by_slug
        if GAMMA_API_AVAILABLE:
            try:
                from get_events_by_slug import get_events_by_slug
                
                self.app.logger.info(f"Fetching event by slug: {slug}")
                event_data = await asyncio.get_event_loop().run_in_executor(
                    None, get_events_by_slug, slug
                )
                
                if event_data and len(event_data) > 0:
                    event = event_data[0]
                    event_slug = event.get('slug', slug)
                    markets = event.get('markets', [])
                    
                    if not markets:
                        self.notify(f"No markets found for: {slug}", severity="warning")
                        return
                    
                    # Add each market from the event
                    for market in markets:
                        # Extract YES/NO prices
                        yes_price = 0.5
                        no_price = 0.5
                        
                        tokens = market.get('tokens', [])
                        for token in tokens:
                            outcome = token.get('outcome', '').lower()
                            price = token.get('price', 0.5)
                            if 'yes' in outcome:
                                yes_price = price
                            elif 'no' in outcome:
                                no_price = price
                        
                        # Also try clobTokenIds/outcomePrices
                        if yes_price == 0.5 and no_price == 0.5:
                            try:
                                outcomePrices = market.get('outcomePrices', '[]')
                                prices = json.loads(outcomePrices) if isinstance(outcomePrices, str) else outcomePrices
                                if len(prices) >= 2:
                                    yes_price = float(prices[0])
                                    no_price = float(prices[1])
                            except:
                                pass
                        
                        market_entry = {
                            'slug': market.get('slug', slug),
                            'event_slug': event_slug,
                            'question': market.get('question', event.get('title', 'Unknown')),
                            'start_date': event.get('startDate', ''),
                            'end_date': market.get('endDate', event.get('endDate', '')),
                            'yes_price': yes_price,
                            'no_price': no_price,
                            'event': event
                        }
                        
                        # Add to markets list
                        self.markets.append(market_entry)
                    
                    # Refresh table and notify
                    self.filtered_markets = self.markets
                    self._populate_markets_table()
                    self.notify(f"Added {len(markets)} market(s) from {slug}", severity="information")
                    
                    # Navigate to first market
                    if markets:
                        first_market_slug = markets[0].get('slug', slug)
                        await self._load_and_navigate_market(self.markets[-len(markets)], first_market_slug)
                else:
                    self.notify(f"Event not found: {slug}", severity="error")
                    
            except Exception as e:
                self.app.logger.error(f"Error loading market by slug: {e}")
                self.notify(f"Error: {str(e)}", severity="error")
        else:
            self.notify("Gamma API not available", severity="error")
    
    def action_go_back(self) -> None:
        """Go back to previous screen"""
        # Cleanup HTTP client
        if self.http_client:
            asyncio.create_task(self.http_client.aclose())
        self.app.pop_screen()
