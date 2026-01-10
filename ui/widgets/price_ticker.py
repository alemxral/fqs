"""
PriceTickerWidget - Display live token price and shares

Shows real-time price updates via WebSocket:
- Current token price with trend indicator
- Total shares/liquidity available
- Price change percentage
- Last trade price
- Color-coded price movements
"""
from typing import Optional, Dict, Any
from decimal import Decimal

from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Container, Vertical
from textual.reactive import reactive


class PriceTickerWidget(Container):
    """
    Widget to display live token price and market data.
    """

    DEFAULT_CSS = """
    PriceTickerWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
        background: $panel;
    }

    PriceTickerWidget .ticker-header {
        height: 1;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    PriceTickerWidget .price-display {
        height: 3;
        content-align: center middle;
        text-style: bold;
        border: solid $success;
        margin-bottom: 1;
        background: $surface;
    }

    PriceTickerWidget .price-up {
        border: solid green;
        color: green;
    }

    PriceTickerWidget .price-down {
        border: solid red;
        color: red;
    }

    PriceTickerWidget .price-neutral {
        border: solid $primary;
        color: $text;
    }

    PriceTickerWidget .ticker-info {
        height: 1;
        content-align: center middle;
        color: $text-muted;
        margin: 0;
    }

    PriceTickerWidget .ticker-stats {
        height: auto;
        margin-top: 1;
        padding: 1;
        background: $boost;
        border: solid $accent;
    }
    """

    # Reactive properties
    current_price = reactive(0.0)
    price_change = reactive(0.0)
    
    def __init__(
        self,
        token_id: Optional[str] = None,
        token_name: Optional[str] = None,
        outcome_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        self.token_id = token_id or "N/A"
        self.token_name = token_name or "Unknown Token"
        self.outcome_type = outcome_type or ""
        
        # Internal state
        self.previous_price: float = 0.0
        self.best_bid: float = 0.0
        self.best_ask: float = 0.0
        self.total_shares: float = 0.0
        self.last_trade_price: float = 0.0
        self.volume_24h: float = 0.0
        
        # Widget references
        self.header: Optional[Static] = None
        self.price_display: Optional[Static] = None
        self.change_display: Optional[Static] = None
        self.shares_display: Optional[Static] = None
        self.spread_display: Optional[Static] = None
        self.volume_display: Optional[Static] = None

    def compose(self) -> ComposeResult:
        with Vertical():
            # Header
            header_text = f"💹 {self.token_name}"
            if self.outcome_type:
                header_text += f" ({self.outcome_type})"
            self.header = Static(header_text, classes="ticker-header")
            yield self.header

            # Price display (large)
            self.price_display = Static("$0.0000", classes="price-display price-neutral")
            yield self.price_display

            # Price change
            self.change_display = Static("Change: --", classes="ticker-info")
            yield self.change_display

            # Stats container
            with Container(classes="ticker-stats"):
                # Shares available
                self.shares_display = Static("Shares: --", classes="ticker-info")
                yield self.shares_display

                # Spread
                self.spread_display = Static("Spread: --", classes="ticker-info")
                yield self.spread_display

                # Volume (if available)
                self.volume_display = Static("Volume 24h: --", classes="ticker-info")
                yield self.volume_display

    def update_price(
        self,
        price: float,
        best_bid: Optional[float] = None,
        best_ask: Optional[float] = None,
        shares: Optional[float] = None,
        last_trade: Optional[float] = None
    ) -> None:
        """Update the price display with new data."""
        # Store previous price for trend calculation
        if self.current_price > 0:
            self.previous_price = self.current_price
        
        # Update current price
        self.current_price = price
        
        # Update optional fields
        if best_bid is not None:
            self.best_bid = best_bid
        if best_ask is not None:
            self.best_ask = best_ask
        if shares is not None:
            self.total_shares = shares
        if last_trade is not None:
            self.last_trade_price = last_trade

        # Calculate price change
        if self.previous_price > 0:
            self.price_change = ((self.current_price - self.previous_price) / self.previous_price) * 100
        
        # Update display
        self._refresh_display()

    def update_from_orderbook(self, orderbook_data: Dict[str, Any]) -> None:
        """
        Update from orderbook data structure.
        
        Expected format from WebSocket:
        {
            'best_bid': float,
            'best_ask': float,
            'bids': [(price, shares), ...],
            'asks': [(price, shares), ...]
        }
        """
        best_bid = orderbook_data.get('best_bid', 0.0)
        best_ask = orderbook_data.get('best_ask', 0.0)
        
        # Calculate mid price
        if best_bid and best_ask:
            mid_price = (best_bid + best_ask) / 2
        elif best_bid:
            mid_price = best_bid
        elif best_ask:
            mid_price = best_ask
        else:
            mid_price = 0.0

        # Calculate total shares from bids and asks
        bids = orderbook_data.get('bids', [])
        asks = orderbook_data.get('asks', [])
        total_shares = sum(shares for _, shares in bids) + sum(shares for _, shares in asks)

        self.update_price(
            price=mid_price,
            best_bid=best_bid,
            best_ask=best_ask,
            shares=total_shares
        )

    def update_from_price_change(self, price: float) -> None:
        """Update from a price_change WebSocket event."""
        self.update_price(price)

    def update_from_last_trade(self, price: float) -> None:
        """Update from a last_trade WebSocket event."""
        self.last_trade_price = price
        self.update_price(price)

    def set_token_info(self, token_id: str, token_name: str, outcome_type: str = "") -> None:
        """Update token identification."""
        self.token_id = token_id
        self.token_name = token_name
        self.outcome_type = outcome_type
        
        if self.header:
            header_text = f"💹 {self.token_name}"
            if self.outcome_type:
                header_text += f" ({self.outcome_type})"
            self.header.update(header_text)

    def _refresh_display(self) -> None:
        """Refresh all display elements."""
        if not self.price_display:
            return

        # Update price with trend indicator
        trend = self._get_trend_indicator()
        price_text = f"{trend} ${self.current_price:.4f}"
        self.price_display.update(price_text)

        # Update price display styling based on trend
        self._update_price_styling()

        # Update change display
        if self.change_display:
            if self.price_change > 0:
                change_text = f"[green]▲ +{self.price_change:.2f}%[/green]"
            elif self.price_change < 0:
                change_text = f"[red]▼ {self.price_change:.2f}%[/red]"
            else:
                change_text = "━ 0.00%"
            self.change_display.update(f"Change: {change_text}")

        # Update shares display
        if self.shares_display:
            if self.total_shares > 0:
                shares_text = f"Shares: {self.total_shares:,.0f}"
            else:
                shares_text = "Shares: --"
            self.shares_display.update(shares_text)

        # Update spread display
        if self.spread_display:
            if self.best_bid > 0 and self.best_ask > 0:
                spread = self.best_ask - self.best_bid
                spread_pct = (spread / self.best_bid) * 100 if self.best_bid > 0 else 0
                spread_text = f"Spread: ${spread:.4f} ({spread_pct:.2f}%)"
            else:
                spread_text = "Spread: --"
            self.spread_display.update(spread_text)

        # Update volume display (placeholder for now)
        if self.volume_display:
            if self.volume_24h > 0:
                volume_text = f"Volume 24h: ${self.volume_24h:,.2f}"
            else:
                volume_text = "Volume 24h: --"
            self.volume_display.update(volume_text)

    def _get_trend_indicator(self) -> str:
        """Get trend indicator arrow."""
        if self.current_price > self.previous_price:
            return "▲"
        elif self.current_price < self.previous_price:
            return "▼"
        return "━"

    def _update_price_styling(self) -> None:
        """Update price display styling based on price movement."""
        if not self.price_display:
            return

        # Remove all price classes
        self.price_display.remove_class("price-up", "price-down", "price-neutral")

        # Add appropriate class
        if self.current_price > self.previous_price:
            self.price_display.add_class("price-up")
        elif self.current_price < self.previous_price:
            self.price_display.add_class("price-down")
        else:
            self.price_display.add_class("price-neutral")

    def watch_current_price(self, old_price: float, new_price: float) -> None:
        """React to price changes."""
        # This is called automatically when current_price changes
        pass

    def clear(self) -> None:
        """Reset the ticker to initial state."""
        self.current_price = 0.0
        self.previous_price = 0.0
        self.price_change = 0.0
        self.best_bid = 0.0
        self.best_ask = 0.0
        self.total_shares = 0.0
        self.last_trade_price = 0.0
        self.volume_24h = 0.0
        self._refresh_display()
