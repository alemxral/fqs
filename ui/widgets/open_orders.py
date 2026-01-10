"""
OpenOrdersWidget - Display and manage open orders

Shows a live table of open orders with:
- Order ID, Side (BUY/SELL), Token, Price, Size, Filled, Status
- Cancel button for each order
- Real-time updates via WebSocket user feed
- Manual refresh capability
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from textual.app import ComposeResult
from textual.widgets import Static, DataTable, Button
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive


class OpenOrdersWidget(Container):
    """
    Widget to display open orders in a DataTable with cancel functionality.
    """

    DEFAULT_CSS = """
    OpenOrdersWidget {
        height: auto;
        border: solid $primary;
        padding: 0;
        background: $panel;
    }

    OpenOrdersWidget .orders-header {
        dock: top;
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        background: $boost;
    }

    OpenOrdersWidget .orders-controls {
        dock: top;
        height: 3;
        padding: 0 1;
    }

    OpenOrdersWidget .orders-controls Button {
        margin: 0 1;
    }

    OpenOrdersWidget DataTable {
        height: auto;
        min-height: 10;
        max-height: 25;
        overflow-y: auto;
        scrollbar-size-vertical: 1;
    }

    OpenOrdersWidget .orders-summary {
        dock: bottom;
        height: 2;
        content-align: center middle;
        background: $boost;
        color: $text;
        text-style: italic;
    }
    """

    # Reactive property to track order count
    order_count = reactive(0)

    class OrderCancelled(Message):
        """Message sent when user requests to cancel an order."""
        def __init__(self, order_id: str):
            self.order_id = order_id
            super().__init__()

    class RefreshRequested(Message):
        """Message sent when user requests to refresh orders."""
        pass

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Internal state
        self.orders: List[Dict[str, Any]] = []
        
        # Widget references
        self.header: Optional[Static] = None
        self.table: Optional[DataTable] = None
        self.summary: Optional[Static] = None
        self.refresh_btn: Optional[Button] = None
        self.cancel_all_btn: Optional[Button] = None

    def compose(self) -> ComposeResult:
        # Header
        self.header = Static("📋 OPEN ORDERS", classes="orders-header")
        yield self.header

        # Controls
        with Horizontal(classes="orders-controls"):
            self.refresh_btn = Button("🔄 Refresh", variant="primary", id="refresh-orders")
            self.cancel_all_btn = Button("❌ Cancel All", variant="error", id="cancel-all-orders")
            yield self.refresh_btn
            yield self.cancel_all_btn

        # DataTable for orders
        self.table = DataTable(zebra_stripes=True, show_cursor=True, cursor_type="row")
        self.table.add_columns(
            "Order ID",
            "Side",
            "Token",
            "Price",
            "Size",
            "Filled",
            "Status",
            "Time",
            "Action"
        )
        yield self.table

        # Summary footer
        self.summary = Static("No open orders", classes="orders-summary")
        yield self.summary

    def on_mount(self) -> None:
        """Set up the widget after mounting."""
        # Initial styling for columns
        if self.table:
            self.table.cursor_type = "row"
            self.table.zebra_stripes = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh-orders":
            self.post_message(self.RefreshRequested())
        elif event.button.id == "cancel-all-orders":
            self.cancel_all_orders()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (for future expansion)."""
        pass

    def update_orders(self, orders: List[Dict[str, Any]]) -> None:
        """
        Update the orders table with new data.
        
        Expected order format:
        {
            'order_id': str,
            'side': 'BUY' or 'SELL',
            'token_id': str,
            'token_name': str (optional, will truncate token_id if missing),
            'price': float,
            'size': float,
            'filled': float,
            'status': str ('LIVE', 'PARTIAL', etc.),
            'created_at': str or timestamp,
            'market_slug': str (optional)
        }
        """
        if not self.table:
            return

        self.orders = orders
        self.order_count = len(orders)

        # Clear existing rows
        self.table.clear()

        # Add rows
        for order in orders:
            order_id = order.get('order_id', 'N/A')
            side = order.get('side', 'N/A')
            token_name = order.get('token_name') or self._truncate_token(order.get('token_id', 'N/A'))
            price = order.get('price', 0.0)
            size = order.get('size', 0.0)
            filled = order.get('filled', 0.0)
            status = order.get('status', 'UNKNOWN')
            created_at = self._format_time(order.get('created_at'))

            # Style based on side
            side_styled = self._style_side(side)
            status_styled = self._style_status(status)
            
            # Truncate order ID for display
            order_id_short = order_id[:8] + "..." if len(order_id) > 8 else order_id

            self.table.add_row(
                order_id_short,
                side_styled,
                token_name,
                f"{price:.4f}",
                f"{size:.2f}",
                f"{filled:.2f}",
                status_styled,
                created_at,
                "🗑️",  # Cancel icon
                key=order_id  # Use full order_id as row key
            )

        # Update summary
        self._update_summary()

    def add_order(self, order: Dict[str, Any]) -> None:
        """Add a single new order to the table."""
        if order not in self.orders:
            self.orders.append(order)
            self.update_orders(self.orders)

    def remove_order(self, order_id: str) -> None:
        """Remove an order from the table by ID."""
        self.orders = [o for o in self.orders if o.get('order_id') != order_id]
        self.update_orders(self.orders)

    def update_order_status(self, order_id: str, status: str, filled: Optional[float] = None) -> None:
        """Update the status of a specific order."""
        for order in self.orders:
            if order.get('order_id') == order_id:
                order['status'] = status
                if filled is not None:
                    order['filled'] = filled
                break
        self.update_orders(self.orders)

    def cancel_order(self, order_id: str) -> None:
        """Request to cancel a specific order."""
        self.post_message(self.OrderCancelled(order_id))

    def cancel_all_orders(self) -> None:
        """Request to cancel all open orders."""
        for order in self.orders:
            order_id = order.get('order_id')
            if order_id:
                self.post_message(self.OrderCancelled(order_id))

    def clear_orders(self) -> None:
        """Clear all orders from the display."""
        self.orders = []
        if self.table:
            self.table.clear()
        self._update_summary()

    def _update_summary(self) -> None:
        """Update the summary footer."""
        if not self.summary:
            return

        count = len(self.orders)
        if count == 0:
            self.summary.update("No open orders")
        else:
            buy_count = sum(1 for o in self.orders if o.get('side') == 'BUY')
            sell_count = sum(1 for o in self.orders if o.get('side') == 'SELL')
            total_size = sum(o.get('size', 0.0) for o in self.orders)
            self.summary.update(
                f"Total: {count} orders ({buy_count} BUY, {sell_count} SELL) | "
                f"Total Size: {total_size:.2f}"
            )

    def _style_side(self, side: str) -> str:
        """Apply color styling to side."""
        if side == 'BUY':
            return f"[green]{side}[/green]"
        elif side == 'SELL':
            return f"[red]{side}[/red]"
        return side

    def _style_status(self, status: str) -> str:
        """Apply color styling to status."""
        if status == 'LIVE':
            return f"[cyan]{status}[/cyan]"
        elif status == 'PARTIAL':
            return f"[yellow]{status}[/yellow]"
        elif status == 'FILLED':
            return f"[green]{status}[/green]"
        elif status == 'CANCELLED':
            return f"[red]{status}[/red]"
        return status

    def _truncate_token(self, token_id: str, length: int = 10) -> str:
        """Truncate token ID for display."""
        if len(token_id) <= length:
            return token_id
        return token_id[:length] + "..."

    def _format_time(self, timestamp: Any) -> str:
        """Format timestamp for display."""
        if not timestamp:
            return "N/A"
        
        try:
            # Handle different timestamp formats
            if isinstance(timestamp, str):
                # Try parsing ISO format
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, (int, float)):
                # Unix timestamp
                dt = datetime.fromtimestamp(timestamp)
            else:
                return str(timestamp)
            
            # Return time only (HH:MM:SS)
            return dt.strftime("%H:%M:%S")
        except Exception:
            return str(timestamp)[:8]

    def watch_order_count(self, old_count: int, new_count: int) -> None:
        """React to changes in order count."""
        if self.header:
            if new_count > 0:
                self.header.update(f"📋 OPEN ORDERS ({new_count})")
            else:
                self.header.update("📋 OPEN ORDERS")
