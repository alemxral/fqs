#!/usr/bin/env python3
"""
Football Widget Mode - Standalone runner for FQS Football Widget

Displays live football match data in a minimal TUI:
- Match score
- Match time (with auto-incrementing timer)
- Match phase
- Time remaining
- Live orderbook prices for YES/NO tokens

Usage:
    python run_football_widget.py <event_slug>
    python run_football_widget.py epl-tot-ast-2025-10-19
"""
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path
parent_dir = str(Path(__file__).parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, RichLog
from textual.containers import Container, Vertical
from textual.binding import Binding
from rich.text import Text

from fqs.ui.widgets.football_widget import FootballWidget
from fqs.core.fetch import FetchManager
from fqs.utils.logger import setup_logger


class FootballWidgetApp(App):
    """Minimal TUI app for displaying football widget"""
    
    TITLE = "FQS Football Widget"
    SUB_TITLE = "Live Match Tracker"
    
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("s", "update_score", "Score", priority=True),
        Binding("t", "update_time", "Time", priority=True),
        Binding("p", "toggle_timer", "Play/Pause", priority=True),
    ]
    
    CSS = """
    FootballWidgetApp {
        background: $surface;
    }
    
    #main_container {
        height: 100%;
        layout: vertical;
        padding: 1;
    }
    
    #market_info {
        height: auto;
        background: $panel;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }
    
    #log_panel {
        height: 1fr;
        background: $surface;
        border: solid $accent;
        padding: 1;
    }
    
    #debug_log {
        height: 100%;
    }
    """
    
    def __init__(self, event_slug: str, **kwargs):
        super().__init__(**kwargs)
        self.event_slug = event_slug
        self.logger = setup_logger()
        self.fetch_manager = FetchManager(logger=self.logger)
        
        # Football state
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
        
        # Market data
        self.market_data = None
        self.event_data = None
    
    def compose(self) -> ComposeResult:
        """Create app layout"""
        yield Header()
        
        with Container(id="main_container"):
            # Football widget
            yield FootballWidget(id="football_widget")
            
            # Market info
            with Container(id="market_info"):
                yield Static("Loading market data...", id="market_text")
            
            # Debug log
            with Vertical(id="log_panel"):
                yield Static("📋 Debug Log", id="log_header")
                yield RichLog(id="debug_log", highlight=True, markup=True)
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Initialize app"""
        self.log_debug(f"[bold cyan]Loading event:[/bold cyan] {self.event_slug}")
        
        # Fetch event data
        await self.fetch_event_data()
        
        # Start timer
        self.set_interval(1.0, self.update_timer)
    
    async def fetch_event_data(self) -> None:
        """Fetch event and market data from Gamma API"""
        try:
            self.log_debug("[yellow]Fetching event data from Gamma API...[/yellow]")
            
            # Use FetchManager to get event
            event_data = self.fetch_manager.get_event_by_slug(self.event_slug)
            
            if not event_data:
                self.log_debug(f"[bold red]Event not found: {self.event_slug}[/bold red]")
                self.notify("Event not found", severity="error")
                return
            
            self.event_data = event_data
            
            # Extract event title
            event_title = event_data.get('title', 'Unknown Event')
            self.log_debug(f"[green]✓ Event loaded:[/green] {event_title}")
            
            # Extract markets
            markets = event_data.get('markets', [])
            if markets:
                self.log_debug(f"[dim]Found {len(markets)} markets[/dim]")
                
                # Use first market for now
                self.market_data = markets[0]
                market_question = self.market_data.get('question', 'Unknown market')
                
                # Extract token IDs and prices
                outcomes = self.market_data.get('outcomes', '[]')
                token_ids = self.market_data.get('clobTokenIds', '[]')
                prices = self.market_data.get('outcomePrices', '[]')
                
                # Parse JSON strings
                import json
                try:
                    outcomes_list = json.loads(outcomes) if isinstance(outcomes, str) else outcomes
                    tokens_list = json.loads(token_ids) if isinstance(token_ids, str) else token_ids
                    prices_list = json.loads(prices) if isinstance(prices, str) else prices
                    
                    # Display market info
                    market_text = f"[bold]{market_question}[/bold]\n"
                    
                    for i, outcome in enumerate(outcomes_list):
                        token = tokens_list[i] if i < len(tokens_list) else "N/A"
                        price = prices_list[i] if i < len(prices_list) else "N/A"
                        market_text += f"  {outcome}: {price} (Token: {token[:16]}...)\n"
                    
                    # Update market info widget
                    market_widget = self.query_one("#market_text", Static)
                    market_widget.update(market_text)
                    
                except json.JSONDecodeError as e:
                    self.log_debug(f"[red]JSON parse error: {e}[/red]")
            else:
                self.log_debug("[yellow]No markets found in event[/yellow]")
            
        except Exception as e:
            self.logger.error(f"Failed to fetch event: {e}", exc_info=True)
            self.log_debug(f"[bold red]Error: {e}[/bold red]")
            self.notify(f"Error: {str(e)}", severity="error")
    
    def update_timer(self) -> None:
        """Auto-increment timer if running"""
        if not self.football_data.get("is_timer_running"):
            return
        
        # Increment seconds
        self.football_data["seconds"] += 1
        
        if self.football_data["seconds"] >= 60:
            self.football_data["seconds"] = 0
            self.football_data["minute"] += 1
        
        # Update time string
        minute = self.football_data["minute"]
        seconds = self.football_data["seconds"]
        self.football_data["time"] = f"{minute}:{seconds:02d}"
        
        # Update time remaining
        total_seconds = (minute * 60) + seconds
        remaining_seconds = (90 * 60) - total_seconds
        self.football_data["time_remaining"] = max(0, remaining_seconds // 60)
        
        # Update widget
        self.update_football_widget()
    
    def update_football_widget(self) -> None:
        """Update football widget display"""
        try:
            widget = self.query_one("#football_widget", FootballWidget)
            widget.update_data(self.football_data)
        except:
            pass
    
    def log_debug(self, message: str) -> None:
        """Log message to debug panel"""
        try:
            debug_log = self.query_one("#debug_log", RichLog)
            debug_log.write(message)
        except:
            pass
    
    # ============= ACTIONS =============
    
    async def action_refresh(self) -> None:
        """Refresh event data"""
        self.log_debug("[bold yellow]Refreshing...[/bold yellow]")
        await self.fetch_event_data()
    
    async def action_update_score(self) -> None:
        """Manual score update (placeholder)"""
        # Parse score from user input
        # For now, just increment home score
        parts = self.football_data["score"].split("-")
        if len(parts) == 2:
            home = int(parts[0])
            away = int(parts[1])
            home += 1
            self.football_data["score"] = f"{home}-{away}"
            self.football_data["goal_difference"] = home - away
            self.update_football_widget()
            self.log_debug(f"[green]Score updated: {self.football_data['score']}[/green]")
    
    async def action_update_time(self) -> None:
        """Manual time update (placeholder)"""
        # For now, just add 5 minutes
        self.football_data["minute"] += 5
        self.football_data["time"] = f"{self.football_data['minute']}:{self.football_data['seconds']:02d}"
        self.update_football_widget()
        self.log_debug(f"[cyan]Time updated: {self.football_data['time']}[/cyan]")
    
    async def action_toggle_timer(self) -> None:
        """Toggle timer on/off"""
        self.football_data["is_timer_running"] = not self.football_data["is_timer_running"]
        
        if self.football_data["is_timer_running"]:
            self.log_debug("[green]● Timer started[/green]")
            self.football_data["phase"] = "1st Half"
        else:
            self.log_debug("[yellow]○ Timer paused[/yellow]")
        
        self.update_football_widget()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python run_football_widget.py <event_slug>")
        print("Example: python run_football_widget.py epl-tot-ast-2025-10-19")
        sys.exit(1)
    
    event_slug = sys.argv[1]
    
    app = FootballWidgetApp(event_slug=event_slug)
    app.run()


if __name__ == "__main__":
    main()
