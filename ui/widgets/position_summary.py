"""
PositionSummaryWidget - Display current positions and P&L

Shows:
- Current positions with token names
- Entry price vs current price
- Unrealized P&L
- Total holdings value
- Color-coded profit/loss
"""
from typing import Optional, List, Dict, Any

from textual.app import ComposeResult
from textual.widgets import Static, DataTable
from textual.containers import Container, Vertical
from textual.reactive import reactive


class PositionSummaryWidget(Container):
    """
    Widget to display current positions and P&L summary.
    """

    DEFAULT_CSS = """
    PositionSummaryWidget {
        height: auto;
        border: solid $primary;
        padding: 0;
        background: $panel;
    }

    PositionSummaryWidget .position-header {
        dock: top;
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        background: $boost;
    }

    PositionSummaryWidget .pnl-summary {
        dock: top;
        height: 5;
        padding: 1;
        background: $surface;
        border-bottom: solid $accent;
    }

    PositionSummaryWidget .pnl-positive {
        color: green;
        text-style: bold;
    }

    PositionSummaryWidget .pnl-negative {
        color: red;
        text-style: bold;
    }

    PositionSummaryWidget .pnl-neutral {
        color: $text;
    }

    PositionSummaryWidget DataTable {
        height: auto;
        min-height: 8;
        max-height: 15;
        overflow-y: auto;
        scrollbar-size-vertical: 1;
    }

    PositionSummaryWidget .position-footer {
        dock: bottom;
        height: 2;
        content-align: center middle;
        background: $boost;
        color: $text;
        text-style: italic;
    }
    """

    # Reactive properties
    total_pnl = reactive(0.0)
    position_count = reactive(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Internal state
        self.positions: List[Dict[str, Any]] = []
        
        # Widget references
        self.header: Optional[Static] = None
        self.pnl_display: Optional[Static] = None
        self.table: Optional[DataTable] = None
        self.footer: Optional[Static] = None

    def compose(self) -> ComposeResult:
        with Vertical():
            # Header
            self.header = Static("💼 POSITIONS", classes="position-header")
            yield self.header

            # P&L Summary section
            self.pnl_display = Static("", classes="pnl-summary")
            yield self.pnl_display

            # DataTable for positions
            self.table = DataTable(zebra_stripes=True, show_cursor=False)
            self.table.add_columns(
                "Token",
                "Size",
                "Entry",
                "Current",
                "P&L",
                "P&L %"
            )
            yield self.table

            # Footer
            self.footer = Static("No positions", classes="position-footer")
            yield self.footer

    def on_mount(self) -> None:
        """Set up the widget after mounting."""
        self._update_pnl_display()

    def update_positions(self, positions: List[Dict[str, Any]]) -> None:
        """
        Update positions with new data.
        
        Expected position format:
        {
            'token_id': str,
            'token_name': str,
            'side': 'YES' or 'NO' or 'BUY' or 'SELL',
            'size': float,
            'entry_price': float,
            'current_price': float,
            'market_slug': str (optional)
        }
        """
        if not self.table:
            return

        self.positions = positions
        self.position_count = len(positions)

        # Clear existing rows
        self.table.clear()

        # Calculate total P&L
        total_pnl_value = 0.0

        # Add rows
        for pos in positions:
            token_name = pos.get('token_name', 'Unknown')
            if len(token_name) > 12:
                token_name = token_name[:10] + "..."
            
            side = pos.get('side', '')
            if side:
                token_name = f"{token_name} ({side})"
            
            size = pos.get('size', 0.0)
            entry_price = pos.get('entry_price', 0.0)
            current_price = pos.get('current_price', 0.0)
            
            # Calculate P&L
            if entry_price > 0:
                pnl_value = (current_price - entry_price) * size
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                pnl_value = 0.0
                pnl_pct = 0.0
            
            total_pnl_value += pnl_value
            
            # Style P&L based on profit/loss
            pnl_str = self._format_pnl(pnl_value)
            pnl_pct_str = self._format_pnl_pct(pnl_pct)

            self.table.add_row(
                token_name,
                f"{size:.2f}",
                f"${entry_price:.4f}",
                f"${current_price:.4f}",
                pnl_str,
                pnl_pct_str
            )

        # Update total P&L
        self.total_pnl = total_pnl_value
        
        # Update displays
        self._update_pnl_display()
        self._update_footer()

    def add_position(self, position: Dict[str, Any]) -> None:
        """Add or update a single position."""
        # Check if position already exists
        token_id = position.get('token_id')
        existing_idx = None
        
        for idx, pos in enumerate(self.positions):
            if pos.get('token_id') == token_id:
                existing_idx = idx
                break
        
        if existing_idx is not None:
            # Update existing position
            self.positions[existing_idx] = position
        else:
            # Add new position
            self.positions.append(position)
        
        self.update_positions(self.positions)

    def remove_position(self, token_id: str) -> None:
        """Remove a position by token ID."""
        self.positions = [p for p in self.positions if p.get('token_id') != token_id]
        self.update_positions(self.positions)

    def update_position_price(self, token_id: str, current_price: float) -> None:
        """Update the current price for a specific position."""
        for pos in self.positions:
            if pos.get('token_id') == token_id:
                pos['current_price'] = current_price
                break
        self.update_positions(self.positions)

    def clear_positions(self) -> None:
        """Clear all positions."""
        self.positions = []
        self.position_count = 0
        self.total_pnl = 0.0
        if self.table:
            self.table.clear()
        self._update_pnl_display()
        self._update_footer()

    def get_total_value(self) -> float:
        """Calculate total portfolio value at current prices."""
        return sum(p.get('current_price', 0.0) * p.get('size', 0.0) for p in self.positions)

    def get_total_cost(self) -> float:
        """Calculate total portfolio cost at entry prices."""
        return sum(p.get('entry_price', 0.0) * p.get('size', 0.0) for p in self.positions)

    def _update_pnl_display(self) -> None:
        """Update the P&L summary display."""
        if not self.pnl_display:
            return

        total_value = self.get_total_value()
        total_cost = self.get_total_cost()
        
        # Calculate total P&L percentage
        if total_cost > 0:
            total_pnl_pct = (self.total_pnl / total_cost) * 100
        else:
            total_pnl_pct = 0.0

        # Build display text
        pnl_class = "pnl-neutral"
        if self.total_pnl > 0:
            pnl_class = "pnl-positive"
            pnl_prefix = "+"
        elif self.total_pnl < 0:
            pnl_class = "pnl-negative"
            pnl_prefix = ""
        else:
            pnl_prefix = ""

        # Remove all P&L classes
        self.pnl_display.remove_class("pnl-positive", "pnl-negative", "pnl-neutral")
        self.pnl_display.add_class(pnl_class)

        display_text = (
            f"Total Value: ${total_value:.2f}\n"
            f"Total Cost: ${total_cost:.2f}\n"
            f"Unrealized P&L: {pnl_prefix}${self.total_pnl:.2f} ({pnl_prefix}{total_pnl_pct:.2f}%)"
        )
        
        self.pnl_display.update(display_text)

    def _update_footer(self) -> None:
        """Update the footer display."""
        if not self.footer:
            return

        count = len(self.positions)
        if count == 0:
            self.footer.update("No positions")
        else:
            total_size = sum(p.get('size', 0.0) for p in self.positions)
            self.footer.update(f"{count} position(s) | Total size: {total_size:.2f}")

    def _format_pnl(self, pnl: float) -> str:
        """Format P&L value with color."""
        if pnl > 0:
            return f"[green]+${pnl:.2f}[/green]"
        elif pnl < 0:
            return f"[red]-${abs(pnl):.2f}[/red]"
        else:
            return "$0.00"

    def _format_pnl_pct(self, pnl_pct: float) -> str:
        """Format P&L percentage with color."""
        if pnl_pct > 0:
            return f"[green]+{pnl_pct:.2f}%[/green]"
        elif pnl_pct < 0:
            return f"[red]{pnl_pct:.2f}%[/red]"
        else:
            return "0.00%"

    def watch_total_pnl(self, old_pnl: float, new_pnl: float) -> None:
        """React to changes in total P&L."""
        self._update_pnl_display()

    def watch_position_count(self, old_count: int, new_count: int) -> None:
        """React to changes in position count."""
        if self.header:
            if new_count > 0:
                self.header.update(f"💼 POSITIONS ({new_count})")
            else:
                self.header.update("💼 POSITIONS")
