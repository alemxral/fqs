"""
TradeHistoryWidget - Display recent trade executions

Shows a scrolling log of recent trades:
- Timestamp
- Side (BUY/SELL)
- Token
- Price
- Size
- Total value
- Color-coded by side
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from textual.app import ComposeResult
from textual.widgets import Static, RichLog
from textual.containers import Container, Vertical
from textual.reactive import reactive


class TradeHistoryWidget(Container):
    """
    Widget to display a scrolling history of trade executions.
    """

    DEFAULT_CSS = """
    TradeHistoryWidget {
        height: auto;
        border: solid $primary;
        padding: 0;
        background: $panel;
    }

    TradeHistoryWidget .trade-header {
        dock: top;
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        background: $boost;
    }

    TradeHistoryWidget RichLog {
        height: auto;
        min-height: 10;
        max-height: 20;
        border: none;
        padding: 1;
        background: $surface;
        overflow-y: auto;
        scrollbar-size-vertical: 1;
    }

    TradeHistoryWidget .trade-summary {
        dock: bottom;
        height: 2;
        content-align: center middle;
        background: $boost;
        color: $text;
        text-style: italic;
    }
    """

    # Reactive property
    trade_count = reactive(0)

    def __init__(self, max_trades: int = 50, **kwargs):
        super().__init__(**kwargs)
        
        self.max_trades = max_trades
        
        # Internal state
        self.trades: List[Dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        with Vertical():
            # Header
            yield Static("📊 TRADE HISTORY", classes="trade-header")

            # RichLog for scrolling trade entries
            yield RichLog(highlight=True, markup=True, wrap=True, classes="trade-log")

            # Summary footer
            yield Static("No trades yet", classes="trade-summary")

    def on_mount(self) -> None:
        """Set up the widget after mounting."""
        try:
            log = self.query_one(".trade-log", RichLog)
            log.can_focus = False
        except:
            pass

    def add_trade(
        self,
        side: str,
        token_name: str,
        price: float,
        size: float,
        timestamp: Optional[Any] = None,
        order_id: Optional[str] = None,
        market_slug: Optional[str] = None,
        fee: Optional[float] = None
    ) -> None:
        """
        Add a new trade to the history.
        
        Args:
            side: 'BUY' or 'SELL'
            token_name: Name or identifier of the token
            price: Execution price
            size: Trade size
            timestamp: Trade timestamp (will use current time if None)
            order_id: Associated order ID
            market_slug: Market identifier
            fee: Trading fee (if available)
        """
        trade = {
            'side': side,
            'token_name': token_name,
            'price': price,
            'size': size,
            'timestamp': timestamp or datetime.now(),
            'order_id': order_id,
            'market_slug': market_slug,
            'fee': fee
        }
        
        # Add to internal list
        self.trades.insert(0, trade)  # Add to front for reverse chronological order
        
        # Limit history size
        if len(self.trades) > self.max_trades:
            self.trades = self.trades[:self.max_trades]
        
        self.trade_count = len(self.trades)
        
        # Add to log display
        self._log_trade(trade)
        
        # Update summary
        self._update_summary()

    def add_trade_from_dict(self, trade_data: Dict[str, Any]) -> None:
        """
        Add a trade from a dictionary (e.g., from WebSocket event).
        
        Expected format:
        {
            'side': 'BUY' or 'SELL',
            'token_id': str,
            'token_name': str (optional),
            'price': float,
            'size': float,
            'timestamp': str or datetime,
            'order_id': str (optional),
            'market_slug': str (optional),
            'fee': float (optional)
        }
        """
        self.add_trade(
            side=trade_data.get('side', 'UNKNOWN'),
            token_name=trade_data.get('token_name') or trade_data.get('token_id', 'Unknown'),
            price=trade_data.get('price', 0.0),
            size=trade_data.get('size', 0.0),
            timestamp=trade_data.get('timestamp'),
            order_id=trade_data.get('order_id'),
            market_slug=trade_data.get('market_slug'),
            fee=trade_data.get('fee')
        )

    def clear_history(self) -> None:
        """Clear all trade history."""
        self.trades = []
        self.trade_count = 0
        try:
            log = self.query_one(".trade-log", RichLog)
            log.clear()
        except:
            pass
        self._update_summary()

    def get_trades(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get trade history, optionally limited to most recent N trades."""
        if limit:
            return self.trades[:limit]
        return self.trades.copy()

    def get_total_volume(self) -> float:
        """Calculate total trading volume."""
        return sum(t['price'] * t['size'] for t in self.trades)

    def get_buy_sell_ratio(self) -> tuple[int, int]:
        """Get count of buy vs sell trades."""
        buy_count = sum(1 for t in self.trades if t['side'] == 'BUY')
        sell_count = sum(1 for t in self.trades if t['side'] == 'SELL')
        return buy_count, sell_count

    def _log_trade(self, trade: Dict[str, Any]) -> None:
        """Add a trade entry to the RichLog."""
        try:
            log = self.query_one(".trade-log", RichLog)
        except:
            return

        # Format timestamp
        time_str = self._format_timestamp(trade['timestamp'])
        
        # Format side with color
        side = trade['side']
        if side == 'BUY':
            side_str = "[green]BUY[/green]"
        elif side == 'SELL':
            side_str = "[red]SELL[/red]"
        else:
            side_str = side

        # Calculate total value
        total = trade['price'] * trade['size']
        
        # Build log entry
        token_name = trade['token_name']
        if len(token_name) > 15:
            token_name = token_name[:12] + "..."
        
        log_entry = (
            f"[bold]{time_str}[/bold] | "
            f"{side_str} | "
            f"[cyan]{token_name}[/cyan] | "
            f"${trade['price']:.4f} × {trade['size']:.2f} = "
            f"[bold]${total:.2f}[/bold]"
        )
        
        # Add fee if available
        if trade.get('fee'):
            log_entry += f" (Fee: ${trade['fee']:.4f})"
        
        # Add order ID if available
        if trade.get('order_id'):
            order_id_short = trade['order_id'][:8] + "..."
            log_entry += f" | Order: {order_id_short}"

        log.write(log_entry)

    def _update_summary(self) -> None:
        """Update the summary footer."""
        try:
            summary = self.query_one(".trade-summary", Static)
        except:
            return

        count = len(self.trades)
        if count == 0:
            summary.update("No trades yet")
        else:
            buy_count, sell_count = self.get_buy_sell_ratio()
            total_volume = self.get_total_volume()
            summary.update(
                f"Total: {count} trades ({buy_count} BUY, {sell_count} SELL) | "
                f"Volume: ${total_volume:,.2f}"
            )

    def _format_timestamp(self, timestamp: Any) -> str:
        """Format timestamp for display."""
        if not timestamp:
            return "N/A"
        
        try:
            # Handle different timestamp formats
            if isinstance(timestamp, datetime):
                dt = timestamp
            elif isinstance(timestamp, str):
                # Try parsing ISO format
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, (int, float)):
                # Unix timestamp
                dt = datetime.fromtimestamp(timestamp)
            else:
                return str(timestamp)
            
            # Return time with seconds
            return dt.strftime("%H:%M:%S")
        except Exception:
            return str(timestamp)[:8]

    def watch_trade_count(self, old_count: int, new_count: int) -> None:
        """React to changes in trade count."""
        try:
            header = self.query_one(".trade-header", Static)
            if new_count > 0:
                header.update(f"📊 TRADE HISTORY ({new_count})")
            else:
                header.update("📊 TRADE HISTORY")
        except:
            pass
