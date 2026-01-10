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
        Binding("enter", "select_market", "Trade", priority=True),
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
        height: 5;
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
    
    #search_container {
        height: 7;
        border: solid $accent;
        padding: 1;
    }
    
    #search_input {
        width: 100%;
    }
    
    #markets_container {
        height: 1fr;
        border: solid $primary;
        background: $panel;
        overflow-y: auto;
        scrollbar-size-vertical: 2;
    }
    
    #markets_table {
        background: $panel;
        border: none;
        max-height: 100%;
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
    }
    
    DataTable > .datatable--cursor {
        background: $accent;
        color: $text;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.markets = []  # List of market dicts with all data
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
        """Create screen layout"""
        yield Header(show_clock=True)
        
        # Header with balance info
        with Horizontal(id="header_info"):
            yield Label("🏆 Sports Markets - Select to Trade", id="title_label")
            yield Label("Balance: Loading...", id="balance_label")
        
        # Filter buttons row
        with Horizontal(id="filter_bar"):
            yield Button("⚽ Football", id="filter_football", classes="filter-btn")
            yield Button("🏀 Basketball", id="filter_basketball", classes="filter-btn")
            yield Button("🏈 NFL", id="filter_nfl", classes="filter-btn")
            yield Button("🏒 Hockey", id="filter_hockey", classes="filter-btn")
            yield Button("🎮 Esports", id="filter_esports", classes="filter-btn")
            yield Button("📊 All", id="filter_all", classes="filter-btn active")
        
        # Search box
        with Container(id="search_container"):
            yield Static("🔍 Search (Ctrl+Enter): epl, lal, nba, nfl, football, basketball | Or tag ID")
            yield Input(placeholder="League code or tag ID...", id="search_input", value="")
        
        # Markets table
        with Container(id="markets_container"):
            yield LoadingIndicator(id="loading")
            yield DataTable(id="markets_table", zebra_stripes=True)
        
        yield Static("ENTER: Trade | CTRL+F: Quick Trade | CTRL+Enter: Search | CTRL+R: Refresh | ESC: Back", id="status_message")
        yield Footer()
    
    async def on_mount(self) -> None:
        """Load markets on mount"""
        self.query_one("#loading", LoadingIndicator).display = False
        
        # Setup markets table
        markets_table = self.query_one("#markets_table", DataTable)
        markets_table.add_columns("Sport", "Match", "Start", "End", "YES", "NO", "Slug")
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
        
        # Load from cache first for instant display
        cached_markets = self._load_cached_markets()
        if cached_markets:
            # Filter for football only from cache
            self.markets = [
                m for m in cached_markets
                if any(x in m.get('question', '').lower() 
                      for x in ['football', 'soccer', 'premier', 'liga', 'serie', 'bundesliga'])
            ][:30]  # Limit to 30 most recent
            self._populate_markets_table()
            self.notify(f"Loaded {len(self.markets)} cached markets", severity="information")
        
        # Background refresh from API
        await self.load_multiple_leagues()
    
    async def update_balance(self) -> None:
        """Update balance display"""
        try:
            if hasattr(self.app, 'api_client'):
                response = await self.app.api_client.get("/api/balance")
                data = response.json()
                if data.get('success'):
                    self.balance = data.get('balance', 0.0)
                    balance_label = self.query_one("#balance_label", Label)
                    balance_label.update(f"Balance: ${self.balance:.2f} USDC")
        except Exception as e:
            self.app.logger.error(f"Failed to update balance: {e}")
    
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
        
        for market in self.markets:
            sport_icon = "⚽"  # Football emoji
            match_name = market.get('question', 'Unknown')[:60]
            start_time = self._format_date(market.get('start_date', ''))
            end_time = self._format_date(market.get('end_date', ''))
            yes_price = f"{market.get('yes_price', 0.5):.1%}"
            no_price = f"{market.get('no_price', 0.5):.1%}"
            slug = market.get('slug', '')[:30]
            
            markets_table.add_row(
                sport_icon,
                match_name,
                start_time,
                end_time,
                yes_price,
                no_price,
                slug,
                key=market.get('slug', '')
            )
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle filter button presses"""
        button_id = event.button.id
        
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
    
    async def action_search_markets(self) -> None:
        """Focus search input for new search"""
        search_input = self.query_one("#search_input", Input)
        search_input.focus()
        self.notify("Enter tag and press Enter to search", severity="information")
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission"""
        if event.input.id == "search_input":
            tag = event.value.strip() or "football"
            await self.load_markets_by_tag(tag)
    
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
        
        # Use async httpx client to get market details
        market_details = await self._fetch_market_details_async(market_slug)
        
        if market_details and len(market_details) > 0:
            market_info = market_details[0]
            
            # Extract token IDs
            tokens = market_info.get('tokens', [])
            yes_token = None
            no_token = None
            
            for token in tokens:
                outcome = token.get('outcome', '').lower()
                if 'yes' in outcome:
                    yes_token = token.get('token_id')
                elif 'no' in outcome:
                    no_token = token.get('token_id')
            
            # Validate we have required data
            if not yes_token or not no_token:
                self.notify("Missing token IDs for market", severity="error")
                self.app.logger.error(f"Market {market_slug} missing tokens: {tokens}")
                return
            
            # Store in app session
            if not hasattr(self.app, 'session'):
                self.app.session = {}
            
            self.app.session.update({
                'market_slug': market_slug,
                'event_slug': selected_market.get('event_slug', market_slug),
                'market_question': market_info.get('question', selected_market.get('question')),
                'yes_token': yes_token,
                'no_token': no_token,
                'yes_price': selected_market.get('yes_price', 0.5),
                'no_price': selected_market.get('no_price', 0.5),
            })
            
            self.app.logger.info(f"Navigating to trade screen for {market_slug}")
            self.app.logger.info(f"  YES token: {yes_token}")
            self.app.logger.info(f"  NO token: {no_token}")
            
            # Navigate to trading screen
            from fqs.ui.screens.football_trade_screen import FootballTradeScreen
            self.app.push_screen(FootballTradeScreen())
        else:
            self.notify(f"Could not load market details", severity="error")
    
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
    
    def action_go_back(self) -> None:
        """Go back to previous screen"""
        # Cleanup HTTP client
        if self.http_client:
            asyncio.create_task(self.http_client.aclose())
        self.app.pop_screen()
