"""
OrderBook Widget (Textual DataTable version)

Rewritten to avoid direct Rich usage and use Textual's DataTable for tabular rendering.
Shows:
- Header with market / token info
- A DataTable with Price | Shares | Value rows (asks then bids)
- A summary Static for best bid/ask and spread

API is compatible with the previous widget:
- update_orderbook(bids, asks, market_name=..., market_slug=..., yes_token_id=..., no_token_id=..., outcome_type=...)
- clear_orderbook()
- calculate_spread() -> (best_bid, best_ask, spread, spread_pct)

Note: styling is done via TCSS and simple style strings (no direct Rich imports).
"""
from typing import Optional, List, Tuple

from textual.app import ComposeResult
from textual.widgets import Static, DataTable
from textual.containers import Container
from textual.screen import Screen
from textual.widget import Widget


class OrderBookWidget(Container):
    """
    Order book display using Textual's DataTable.
    """

    DEFAULT_CSS = """
    OrderBookWidget {
        height: auto;
        border: solid $primary;
        padding: 0;
        background: $panel;
    }

    OrderBookWidget .orderbook-title {
        dock: top;
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }

    OrderBookWidget .spread-indicator {
        dock: top;
        height: 2;
        content-align: center middle;
        background: $boost;
        color: $text;
        text-style: bold;
        border: solid $accent;
        margin-bottom: 1;
    }

    OrderBookWidget DataTable {
        height: auto;
        overflow-y: auto;
    }
    """

    def __init__(
        self,
       
        token_id: Optional[str] = None,
        market_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.token_id = token_id
        self.market_id = market_id

        # internal state
        self.bids: List[Tuple[float, float]] = []  # list of (price, shares)
        self.asks: List[Tuple[float, float]] = []  # list of (price, shares)
        self.market_name: str = "Market"
        self.market_slug: str = ""
        self.yes_token_id: str = ""
        self.no_token_id: str = ""
        self.outcome_type: str = ""

        # widget references populated in compose()
        self.header: Optional[Static] = None
        self.spread_indicator: Optional[Static] = None
        self.table: Optional[DataTable] = None

    def compose(self) -> ComposeResult:
        # Header / title area
        self.header = Static("", classes="orderbook-title")
        yield self.header

        # Spread indicator - always visible, shows best bid/ask/spread
        self.spread_indicator = Static("", classes="spread-indicator")
        yield self.spread_indicator

        # DataTable for orderbook rows
        self.table = DataTable(zebra_stripes=False, show_cursor=False)
        # define columns
        self.table.add_column("Price", key="price", width=12)
        self.table.add_column("Shares", key="shares", width=12)
        self.table.add_column("Value", key="value", width=14)
        yield self.table

    def on_mount(self) -> None:
        # initial render
        self.update_display()

    def update_orderbook(
        self,
        bids: List[Tuple[float, float]],
        asks: List[Tuple[float, float]],
        market_name: Optional[str] = None,
        market_slug: Optional[str] = None,
        yes_token_id: Optional[str] = None,
        no_token_id: Optional[str] = None,
        outcome_type: Optional[str] = None,
    ) -> None:
        """
        Update internal data and refresh display.

        bids: list of (price, shares)
        asks: list of (price, shares)
        """
        # Store bids descending (highest first)
        self.bids = sorted(bids or [], key=lambda x: x[0], reverse=True)
        # Store asks ascending (lowest first) so best ask is first
        self.asks = sorted(asks or [], key=lambda x: x[0], reverse=False)

        if market_name:
            self.market_name = market_name
        if market_slug:
            self.market_slug = market_slug
        if yes_token_id:
            self.yes_token_id = yes_token_id
        if no_token_id:
            self.no_token_id = no_token_id
        if outcome_type:
            self.outcome_type = outcome_type

        self.update_display()

    def calculate_spread(self) -> Tuple[float, float, float, float]:
        """
        Calculate best bid, best ask, spread and spread percentage.

        Returns: (best_bid, best_ask, spread_amount, spread_pct)
        """
        if not self.bids or not self.asks:
            return (0.0, 0.0, 0.0, 0.0)

        best_bid = self.bids[0][0] if self.bids else 0.0  # highest bid
        best_ask = self.asks[0][0] if self.asks else 0.0  # lowest ask

        spread = best_ask - best_bid
        spread_pct = (spread / best_bid * 100) if best_bid > 0 else 0.0

        return (best_bid, best_ask, spread, spread_pct)

    def update_display(self) -> None:
        """Re-render header, table rows and summary."""
        # Header text
        title_parts = []
        title_parts.append("📊 ORDER BOOK")
        if self.outcome_type:
            title_parts.append(f"[{self.outcome_type.upper()}]")
        if self.market_name and self.market_name != "Market":
            title_parts.append(f"- {self.market_name}")

        header_text = " ".join(title_parts)
        
        # additional info lines
        if self.market_slug:
            header_text += f"\n🔗 Slug: {self.market_slug}"
        if isinstance(self.market_id, str) and self.market_id:
            mid = (
                f"{self.market_id[:16]}...{self.market_id[-8:]}" 
                if len(self.market_id) > 30 
                else self.market_id
            )
            header_text += f"\n🆔 Market ID: {mid}"
        else:
            header_text += "\n🆔 Market ID: (not available)"
        if self.yes_token_id or self.no_token_id:
            if self.yes_token_id:
                yes_display = (
                    f"{self.yes_token_id[:10]}...{self.yes_token_id[-6:]}"
                    if len(self.yes_token_id) > 20
                    else self.yes_token_id
                )
                header_text += f"\n✅ YES Token: {yes_display}"
            if self.no_token_id:
                no_display = (
                    f"{self.no_token_id[:10]}...{self.no_token_id[-6:]}"
                    if len(self.no_token_id) > 20
                    else self.no_token_id
                )
                header_text += f"\n❌ NO Token: {no_display}"

        if self.header:
            # update header Static (plain text; styling via CSS)
            self.header.update(header_text)

        # Update spread indicator (always visible at top)
        best_bid, best_ask, spread, spread_pct = self.calculate_spread()
        if self.spread_indicator:
            if best_bid > 0 and best_ask > 0:
                # Show market slug at top if available, filter out junk data
                slug_display = ""
                if self.market_slug and self.market_slug not in ["unknown", "", "Market"]:
                    # Filter out CSS/theme artifacts like '-dark-mode'
                    clean_slug = self.market_slug.strip()
                    if not clean_slug.startswith('-') and not clean_slug.startswith('{'):
                        slug_display = f"[{clean_slug}] "
                
                # Compact format to fit in narrow space
                spread_text = (
                    f"{slug_display}"
                    f"ASK ${best_ask:.3f} | "
                    f"SPREAD ${spread:.3f} ({spread_pct:.1f}%) | "
                    f"BID ${best_bid:.3f}"
                )
            else:
                spread_text = "⏳ Loading..."
            self.spread_indicator.update(spread_text)

        # Ensure table exists
        if not self.table:
            return

        # Clear existing rows
        try:
            self.table.clear()
        except Exception:
            # older Textual versions may not have clear(); recreate instead
            # safe fallback: re-add columns by reconstructing the table widget
            # (rare; keep simple and continue)
            pass

        # Show top 5 asks and bids
        ASK_COUNT = min(5, len(self.asks))
        BID_COUNT = min(5, len(self.bids))

        # Show asks (lowest prices, but display in REVERSE order)
        # So the best ask (lowest price) appears closest to the spread line
        asks_to_show = self.asks[:ASK_COUNT]
        # Reverse so highest of the low asks is at top, best ask at bottom (near spread)
        for price, shares in reversed(asks_to_show):
            value = price * shares
            price_cell = f"${price:.4f}"
            shares_cell = f"{shares:,.2f}"
            value_cell = f"${value:,.2f}"
            # style asks with a subtle "red" style for the row
            try:
                self.table.add_row(price_cell, shares_cell, value_cell, style="white on dark_red")
            except TypeError:
                # older DataTable.add_row might not accept style param; fallback without it
                self.table.add_row(price_cell, shares_cell, value_cell)

        # Add a blank/separator row (we can't colspan easily in DataTable)
        # Insert an empty row to visually separate asks and bids
        try:
            self.table.add_row("━━━━━━━━━━", "━━━━━━━━━━", "━━━━━━━━━━", style="bold yellow")
        except TypeError:
            self.table.add_row("━━━━━━━━━━", "━━━━━━━━━━", "━━━━━━━━━━")

        # Show bids (highest prices)
        for i in range(BID_COUNT):
            price, shares = self.bids[i]
            value = price * shares
            price_cell = f"${price:.4f}"
            shares_cell = f"{shares:,.2f}"
            value_cell = f"${value:,.2f}"
            try:
                self.table.add_row(price_cell, shares_cell, value_cell, style="white on dark_green")
            except TypeError:
                self.table.add_row(price_cell, shares_cell, value_cell)

    def clear_orderbook(self) -> None:
        """Clear all stored data and refresh display."""
        self.bids = []
        self.asks = []
        self.update_display()


class OrderBookContainer(Container):
    """
    Simple container that yields a title and an OrderBookWidget.
    """

    DEFAULT_CSS = """
    OrderBookContainer {
        height: 40%;
        border: solid $primary;
        padding: 1;
    }

    OrderBookContainer > .orderbook-header {
        dock: top;
        height: 2;
        content-align: center middle;
        text-style: bold;
        background: $boost;
    }
    """

    def __init__(
        self,
        token_id: Optional[str] = None,
        market_id: Optional[str] = None,
        market_name: Optional[str] = None,
        market_slug: Optional[str] = None,
        yes_token_id: Optional[str] = None,
        no_token_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.token_id = token_id
        self.market_id = market_id
        self.market_name = market_name or "Market"
        self.market_slug = market_slug
        self.yes_token_id = yes_token_id
        self.no_token_id = no_token_id

        self.orderbook: Optional[OrderBookWidget] = None

    def compose(self) -> ComposeResult:
        from textual.widgets import Label

        # Header label for the container
        yield Label(f"📊 {self.market_name}", classes="orderbook-header")

        # Create and yield orderbook widget
        self.orderbook = OrderBookWidget(token_id=self.token_id, market_id=self.market_id)
        yield self.orderbook

    def update_orderbook(
        self,
        bids: List[Tuple[float, float]],
        asks: List[Tuple[float, float]],
        market_name: Optional[str] = None,
        market_slug: Optional[str] = None,
        yes_token_id: Optional[str] = None,
        no_token_id: Optional[str] = None,
        outcome_type: Optional[str] = None,
    ) -> None:
        """Proxy update to contained OrderBookWidget"""
        if self.orderbook:
            self.orderbook.update_orderbook(
                bids=bids,
                asks=asks,
                market_name=market_name or self.market_name,
                market_slug=market_slug or self.market_slug,
                yes_token_id=yes_token_id or self.yes_token_id,
                no_token_id=no_token_id or self.no_token_id,
                outcome_type=outcome_type,
            )

    def clear_orderbook(self) -> None:
        if self.orderbook:
            self.orderbook.clear_orderbook()