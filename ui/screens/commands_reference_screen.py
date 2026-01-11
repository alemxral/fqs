"""
Commands Reference Screen - Display all available commands
Shows comprehensive list of commands that the system can process
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Footer, Static, DataTable
from textual.containers import Container, Vertical, ScrollableContainer
from rich.text import Text

from ..widgets.main_header import MainHeader


class CommandsReferenceScreen(Screen):
    """
    Screen displaying all available commands and their usage
    """
    
    BINDINGS = [
        Binding("escape", "go_back", "Back", priority=True),
        Binding("ctrl+r", "refresh", "Refresh", priority=True),
    ]
    
    CSS = """
    CommandsReferenceScreen {
        background: $surface;
    }
    
    #title_container {
        height: 5;
        width: 100%;
        background: $boost;
        border: tall $primary;
        padding: 1 2;
        content-align: center middle;
    }
    
    #commands_container {
        height: 1fr;
        width: 100%;
        border: solid $primary;
        background: $panel;
        padding: 1;
        overflow-y: auto;
        scrollbar-size-vertical: 2;
    }
    
    #commands_table {
        background: $panel;
        border: none;
        width: 100%;
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
    
    .command-category {
        height: 3;
        background: $primary;
        color: $text;
        text-style: bold;
        padding: 1;
        border-bottom: solid $accent;
        margin-top: 1;
    }
    
    .command-item {
        height: auto;
        min-height: 4;
        background: $panel;
        border: solid $secondary;
        padding: 1;
        margin: 1 0;
    }
    
    Footer {
        dock: bottom;
        height: 1;
        background: $boost;
        layer: overlay;
    }
    """
    
    # Commands database
    COMMANDS = {
        "Navigation & System": [
            ("help", "", "Show help message"),
            ("exit", "", "Exit the application"),
            ("hello", "", "Test command - returns greeting"),
            ("status", "", "Show system status"),
        ],
        "Market Information": [
            ("see", "<slug|market_name>", "View market details by slug or name"),
            ("markets", "[tag]", "List active markets (optional: filter by tag)"),
            ("refresh", "", "Refresh current market data"),
        ],
        "Trading Operations": [
            ("buy", "<YES|NO> <price> <size>", "Buy shares (e.g., buy YES 0.65 10)"),
            ("sell", "<YES|NO> <price> <size>", "Sell shares (e.g., sell NO 0.45 5)"),
            ("quickbuy", "<YES|NO> [size]", "Quick buy at best available price"),
        ],
        "Portfolio Management": [
            ("balance", "", "Check USDC balance"),
            ("orders", "", "View open orders"),
            ("positions", "", "View current positions"),
            ("trades", "", "View recent trade history"),
        ],
        "WebSocket & Live Data": [
            ("ws", "connect <token_id>", "Connect WebSocket to token"),
            ("ws", "disconnect", "Disconnect WebSocket"),
            ("ws", "status", "Check WebSocket connection status"),
        ],
        "Match Updates (Football)": [
            ("score", "<home>-<away>", "Update match score (e.g., score 2-1)"),
            ("time", "<mm:ss>", "Update match time (e.g., time 67:30)"),
        ],
        "Home Screen Specific": [
            ("LOOK", "<slug>", "Load market by slug and navigate to trade screen"),
        ],
    }
    
    def compose(self) -> ComposeResult:
        """Create the screen layout"""
        yield MainHeader()
        
        # Title
        with Container(id="title_container"):
            yield Static("📖 Commands Reference - All Available Commands", id="title")
        
        # Commands list
        with ScrollableContainer(id="commands_container"):
            yield DataTable(id="commands_table", zebra_stripes=True)
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Populate commands table on mount"""
        table = self.query_one("#commands_table", DataTable)
        table.add_columns("Command", "Arguments", "Description")
        table.cursor_type = "row"
        table.zebra_stripes = True
        
        # Populate table with all commands
        for category, commands in self.COMMANDS.items():
            # Add category header as a row with special styling
            table.add_row(
                f"[bold cyan]{category}[/bold cyan]",
                "",
                "",
                key=f"cat_{category}"
            )
            
            # Add commands in this category
            for cmd, args, description in commands:
                cmd_str = f"[bold green]{cmd}[/bold green]"
                args_str = f"[yellow]{args}[/yellow]" if args else "[dim]-[/dim]"
                desc_str = description
                
                table.add_row(
                    cmd_str,
                    args_str,
                    desc_str,
                    key=f"cmd_{cmd}_{args}"
                )
    
    def action_refresh(self) -> None:
        """Refresh the commands list"""
        table = self.query_one("#commands_table", DataTable)
        table.clear()
        self.on_mount()
        self.notify("Commands list refreshed", severity="information")
    
    def action_go_back(self) -> None:
        """Return to previous screen"""
        self.app.pop_screen()
