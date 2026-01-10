"""
WebSocket Manager - Core Business Logic
Wraps PolymarketWebsocketsClient for use in PMTerminal
"""

import sys
from pathlib import Path

# Add project root to path BEFORE imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import asyncio
from typing import Callable, Optional, Any, Dict, List
from collections.abc import Callable as CallableType
import json
from threading import Thread

# ============= PYTHON 3.X COMPATIBLE IMPORT STRATEGY =============
# Supports Python 3.6+ by using compatibility layer for match/case syntax
WS_CLIENT_AVAILABLE = False
WS_COMPAT_MODE = False

try:
    # First, try to import type definitions (these don't use match/case)
    from client.py_clob_client.clob_types import ApiCreds
    from client.py_ws_client.types.websockets_types import (
        OrderBookSummaryEvent,
        PriceChangeEvent,
        LastTradePriceEvent,
        OrderEvent,
        TradeEvent,
        LiveDataOrderBookSummaryEvent,
        LiveDataTradeEvent,
    )
    
    # Check Python version for match/case support
    if sys.version_info >= (3, 10):
        # Python 3.10+ can use original client with match/case
        try:
            from client.py_ws_client.websockets_client import PolymarketWebsocketsClient
            WS_CLIENT_AVAILABLE = True
            print(f"[WebSocket] ✓ Running in FULL mode (Python {sys.version_info.major}.{sys.version_info.minor})")
        except (ImportError, SyntaxError) as e:
            print(f"[WebSocket] Warning: Could not load native client: {e}")
            WS_COMPAT_MODE = True
    else:
        # Python 3.6-3.9: match/case not available, use compatibility layer
        WS_COMPAT_MODE = True
        print(f"[WebSocket] ✓ Running in COMPAT mode (Python {sys.version_info.major}.{sys.version_info.minor})")
        print(f"[WebSocket] Using compatibility layer for match/case syntax")
    
    # If compatibility mode needed, import compat layer
    if WS_COMPAT_MODE:
        try:
            from fqs.core.websocket_compat import (
                process_market_event_compat,
                process_user_event_compat,
                process_live_data_event_compat,
                check_python_compatibility,
                get_compatibility_info
            )
            
            # Check compatibility
            is_compat, msg = check_python_compatibility()
            if is_compat:
                WS_CLIENT_AVAILABLE = True
                print(f"[WebSocket] Compatibility check: {msg}")
            else:
                print(f"[WebSocket] Warning: {msg}")
                WS_CLIENT_AVAILABLE = False
                
        except ImportError as e:
            print(f"[WebSocket] Warning: Compatibility layer not available: {e}")
            WS_COMPAT_MODE = False

except (ImportError, SyntaxError) as e:
    # Complete fallback - types not available
    print(f"[WebSocket] Warning: WebSocket types not available: {e}")
    print(f"[WebSocket] Running in STUB mode (WebSocket features disabled)")
    WS_CLIENT_AVAILABLE = False

# Create stub classes if nothing else worked
if not WS_CLIENT_AVAILABLE:
    print(f"[WebSocket] Running in STUB mode (features disabled)")
    
    class ApiCreds:
        def __init__(self, **kwargs):
            pass
    
    class PolymarketWebsocketsClient:
        def __init__(self, *args, **kwargs):
            pass
    
    # Event stubs
    OrderBookSummaryEvent = dict
    PriceChangeEvent = dict
    LastTradePriceEvent = dict
    OrderEvent = dict
    TradeEvent = dict
    LiveDataOrderBookSummaryEvent = dict
    LiveDataTradeEvent = dict


class OrderBook:
    def __init__(self, market_slug: Optional[str] = None):
        self.token_id = None
        self.timestamp = None
        self.condition_id = None # Market ID
        self.market_slug = market_slug  # NEW: store market slug
        self.asks = []  # List of tuples: (price, shares)
        self.bids = []  # List of tuples: (price, shares)
        self.best_ask = None  # Tuple: (price, shares)
        self.best_bid = None  # Tuple: (price, shares)

    #there are 3 responses from ws;     

    def update_from_price_change(self, event):
        """
        Update order book from a PriceChangeEvent object.
        Args:
            event: PriceChangeEvent object containing a list of price_changes
        """
        self.timestamp = getattr(event, "timestamp", None)
        self.condition_id = getattr(event, "condition_id", None)
        self.token_id = getattr(event, "token_id", None)
        for pc in getattr(event, "price_changes", []):
            if pc.side == "SELL":
                self.best_ask = (pc.best_ask, pc.size)
                # Remove any existing ask with the same price
                self.asks = [ask for ask in self.asks if ask[0] != pc.price]
                self.asks.append((pc.price, pc.size))
            elif pc.side == "BUY":
                self.best_bid = (pc.best_bid, pc.size)
                # Remove any existing bid with the same price
                self.bids = [bid for bid in self.bids if bid[0] != pc.price]
                self.bids.append((pc.price, pc.size))

    def update_from_summary(self, event):

        # bids/asks: list of dicts {"price": str, "size": str}
        self.token_id = getattr(event, "token_id", None)
        self.condition_id = getattr(event, "condition_id", None)
        self.timestamp = getattr(event, "timestamp", None)
        self.hash = getattr(event, "hash", None)
        # bids/asks: list of Orderevent objects
        self.bids = [(float(order.price), float(order.size)) for order in (event.bids or [])]
        self.asks = [(float(order.price), float(order.size)) for order in (event.asks or [])]
        self.best_bid = self.bids[0] if self.bids else None
        self.best_ask = self.asks[0] if self.asks else None


    def update_from_last_trade(self, event):
            """
            Update order book from a LastTradePrice event.
            Args:
                event: LastTradePrice object with price, size, side, token_id, condition_id, fee_rate_bps
            """
            self.token_id = getattr(event, "token_id", None)
            self.condition_id = getattr(event, "condition_id", None)
            self.timestamp = getattr(event, "timestamp", None)
            price = getattr(event, "price", None)
            size = getattr(event, "size", None)
            side = getattr(event, "side", None)
            if side == "SELL":
                # Decrement shares at the ask price by trade size
                updated_asks = []
                found = False
                for ask in self.asks:
                    if ask[0] == price:
                        new_size = max(ask[1] - size, 0)
                        updated_asks.append((price, new_size))
                        found = True
                    else:
                        updated_asks.append(ask)
                # If price not found, add with size 0
                if not found:
                    updated_asks.append((price, 0))
                self.asks = updated_asks
                self.best_ask = self.asks[0] if self.asks else None
            elif side == "BUY":
                # Decrement shares at the bid price by trade size
                updated_bids = []
                found = False
                for bid in self.bids:
                    if bid[0] == price:
                        new_size = max(bid[1] - size, 0)
                        updated_bids.append((price, new_size))
                        found = True
                    else:
                        updated_bids.append(bid)
                # If price not found, add with size 0
                if not found:
                    updated_bids.append((price, 0))
                self.bids = updated_bids
                self.best_bid = self.bids[0] if self.bids else None

    def set_market_slug(self, market_slug: str):
        """Set the market slug for this orderbook"""
        self.market_slug = market_slug
    
    def get_orderbook(self, *fields):
        """
        Return orderbook state. If fields are specified, return only those fields. Otherwise, return all.
        Args:
            *fields: Optional field names to include in the result.
        Returns:
            dict of requested fields (or all if none specified)
        """
        all_fields = {
            "token_id": self.token_id,
            "market_slug": self.market_slug,  # NEW: include market slug
            "asks": self.asks,
            "bids": self.bids,
            "best_ask": self.best_ask,
            "best_bid": self.best_bid,
            "timestamp": getattr(self, "timestamp", None),
            "hash": getattr(self, "hash", None)
        }
        if fields:
            return {field: all_fields[field] for field in fields if field in all_fields}
        return all_fields



class WebSocketCore:
    """
    Core WebSocket manager for PMTerminal
    
    Handles connections to Polymarket WebSocket feeds:
    - Market data (orderbooks, price changess)
    - User data (orders, trades)
    - Live activity data
    
    No UI dependencies - returns parsed data to callbacks
    """
    
    def __init__(self, api_creds: Optional[ApiCreds] = None):
        """
        Initialize WebSocket manager
        
        Args:
            api_creds: API credentials for authenticated endpoints
        """
        # Check if WebSocket client is available
        self.ws_available = WS_CLIENT_AVAILABLE
        
        if self.ws_available:
            self.client = PolymarketWebsocketsClient()
        else:
            self.client = None
            print("[WebSocketCore] Running in STUB mode - WebSocket features disabled")
        
        self.api_creds = api_creds
        
        # Multiple orderbooks - one per token
        self.orderbooks: Dict[str, OrderBook] = {}  # {token_id: OrderBook instance}
        
        # Legacy single orderbook (for backward compatibility)
        self.orderbook = OrderBook()
        
        # Connection state (dict for compatibility with tests)
        self.connection_state = {
            'market': False,
            'user': False,
            'live_data': False
        }
        self.market_connected = False
        self.user_connected = False
        self.live_data_connected = False
        
        # Background threads
        self._market_thread: Optional[Thread] = None
        self._user_thread: Optional[Thread] = None
        self._live_data_thread: Optional[Thread] = None
        
        # Event callbacks
        self._orderbook_callback: Optional[Callable] = None
        self._trade_callback: Optional[Callable] = None
        self._order_callback: Optional[Callable] = None
        self._price_change_callback: Optional[Callable] = None
    
    # ═══════════════════════════════════════════════════════════════
    #                    MARKET DATA FEED
    # ═══════════════════════════════════════════════════════════════
    
    def connect_market(
        self, 
        token_ids: List[str],
        on_orderbook: Optional[Callable] = None,
        on_price_change: Optional[Callable] = None,
        on_last_trade: Optional[Callable] = None
    ) -> None:
        """
        Connect to market WebSocket feed
        
        Args:
            token_ids: List of token IDs to subscribe to
            on_orderbook: Callback for orderbook updates
                         Signature: (token_id: str, data: dict) -> None
            on_price_change: Callback for price changes
                           Signature: (token_id: str, old_price: float, new_price: float) -> None
            on_last_trade: Callback for last trade price
                         Signature: (token_id: str, price: float) -> None
        
        Example:
            >>> ws.connect_market(
            ...     token_ids=["0x1234...", "0x5678..."],
            ...     on_orderbook=lambda tid, data: print(f"OrderBook {tid}: {data}")
            ... )
        """
        
        # Check if WebSocket is available
        if not self.ws_available:
            print("[WebSocketCore] Cannot connect: WebSocket client not available (stub mode)")
            print("[WebSocketCore] This may be due to Python version compatibility (requires 3.12+)")
            return

        # Initialize separate OrderBook instance for each token
        for token_id in token_ids:
            self.orderbooks[token_id] = OrderBook()

        # Store callbacks
        self._orderbook_callback = on_orderbook
        self._price_change_callback = on_price_change
        self._last_trade_callback = on_last_trade
        
        # Create custom event processor
        def process_market_event(event):
            try:
                message = event.json
                
                # Handle batch messages
                if isinstance(message, list):
                    for item in message:
                        self._handle_market_message(item)
                    return
                
                # Handle single message
                self._handle_market_message(message)
                
            except Exception as e:
                print(f"Error processing market event: {e}")
        
        # Start WebSocket in background thread
        def run_market_socket():
            self.market_connected = True
            try:
                self.client.market_socket(
                    token_ids=token_ids,
                    process_event=process_market_event
                )
            finally:
                self.market_connected = False
        
        self._market_thread = Thread(target=run_market_socket, daemon=True)
        self._market_thread.start()
    
    def _handle_market_message(self, message: dict) -> None:
        """Process individual market message and update orderbook state"""
        import time
        event_type = message.get("event_type")
        
        # Extract token_id to route to correct orderbook
        token_id = message.get("token_id") or message.get("asset_id")
        
        # For price_change events, token_id is inside each price_change object
        # Process each price_change separately for its token
        if event_type == "price_change" and not token_id:
            price_changes = message.get("price_changes", []) or message.get("pc", [])
            
            # Process each price change separately (each may have different token_id)
            for pc in price_changes:
                # Extract token_id from the price_change object
                pc_token_id = pc.get("token_id") or pc.get("asset_id") or pc.get("a")
                
                if not pc_token_id:
                    print(f"[WS] Price change without token_id in price_changes array")
                    continue
                
                # Get or create OrderBook for this token
                if pc_token_id not in self.orderbooks:
                    self.orderbooks[pc_token_id] = OrderBook()
                
                orderbook = self.orderbooks[pc_token_id]
                
                # Create a temporary message with this specific price_change
                temp_message = message.copy()
                temp_message['price_changes'] = [pc]
                temp_message['token_id'] = pc_token_id  # Add token_id for the event
                
                try:
                    event = PriceChangeEvent(**temp_message)
                    orderbook.update_from_price_change(event)
                    
                    # DEBUG: Print update info
                    print(f"[WS] Price change for {pc_token_id[:8]}... at {time.strftime('%H:%M:%S')}")
                    
                    # Also update legacy single orderbook
                    self.orderbook = orderbook
                    
                    if self._price_change_callback:
                        self._price_change_callback(orderbook.get_orderbook())
                except Exception as e:
                    print(f"[WS] Error processing price_change for {pc_token_id[:8]}: {e}")
            
            # Return early since we processed all price changes
            return
        
        # For other event types, token_id should be at top level
        if not token_id:
            print(f"[WS] Message without token_id - event_type: {event_type}")
            return
        
        # Get or create OrderBook for this token
        if token_id not in self.orderbooks:
            self.orderbooks[token_id] = OrderBook()

        # Route to correct orderbook instance
        orderbook = self.orderbooks[token_id]

        if event_type == "book":
            event = OrderBookSummaryEvent(**message)
            orderbook.update_from_summary(event)
            
            # DEBUG: Print update info
            print(f"[WS] Updated orderbook for {token_id[:8]}... at {time.strftime('%H:%M:%S')} - {len(orderbook.bids)} bids, {len(orderbook.asks)} asks")
            
            # Also update legacy single orderbook (for backward compatibility)
            self.orderbook = orderbook
            
            if self._orderbook_callback:
                self._orderbook_callback(orderbook.get_orderbook())

        elif event_type == "last_trade_price":
            event = LastTradePriceEvent(**message)
            orderbook.update_from_last_trade(event)
            
            # DEBUG: Print update info
            print(f"[WS] Last trade for {token_id[:8]}... at {time.strftime('%H:%M:%S')}")
            
            # Also update legacy single orderbook
            self.orderbook = orderbook
            
            if self._last_trade_callback:
                self._last_trade_callback(orderbook.get_orderbook())
    
    # ═══════════════════════════════════════════════════════════════
    #                    USER DATA FEED (Authenticated)
    # ═══════════════════════════════════════════════════════════════
    
    def connect_user(
        self,
        on_order: Optional[Callable] = None,
        on_trade: Optional[Callable] = None
    ) -> None:
        """
        Connect to user WebSocket feed (requires API credentials)
        
        Args:
            on_order: Callback for order updates
                     Signature: (order_data: dict) -> None
            on_trade: Callback for trade updates
                     Signature: (trade_data: dict) -> None
        
        Raises:
            ValueError: If API credentials not provided
        """
        
        # Check if WebSocket is available
        if not self.ws_available:
            print("[WebSocketCore] Cannot connect user: WebSocket client not available (stub mode)")
            return
        
        if not self.api_creds:
            raise ValueError("API credentials required for user feed")
        
        # Store callbacks
        self._order_callback = on_order
        self._trade_callback = on_trade
        
        # Create custom event processor
        def process_user_event(event):
            try:
                message = event.json
                self._handle_user_message(message)
            except Exception as e:
                print(f"Error processing user event: {e}")
        
        # Start WebSocket in background thread
        def run_user_socket():
            self.user_connected = True
            try:
                self.client.user_socket(
                    creds=self.api_creds,
                    process_event=process_user_event
                )
            finally:
                self.user_connected = False
        
        self._user_thread = Thread(target=run_user_socket, daemon=True)
        self._user_thread.start()
    
    def _handle_user_message(self, message: dict) -> None:
        """Process individual user message"""
        event_type = message.get("event_type")
        
        if event_type == "order":
            # Order update
            event = OrderEvent(**message)
            
            if self._order_callback:
                data = {
                    "order_id": event.id,
                    "market": event.market,
                    "condition_id": event.condition_id,
                    "side": event.side,
                    "size": float(event.original_size),
                    "price": float(event.price),
                    "status": event.status,
                    "timestamp": event.timestamp
                }
                self._order_callback(data)
        
        elif event_type == "trade":
            # Trade execution
            event = TradeEvent(**message)
            print(f"trade event in:")
            if self._trade_callback:
                data = {
                    "trade_id": event.id,
                    "market": event.market,
                    "condition_id": event.condition_id,
                    "side": event.side,
                    "size": float(event.size),
                    "price": float(event.price),
                    "fee": float(event.fee_rate_bps),
                    "timestamp": event.timestamp
                }
                self._trade_callback(data)
    
    # ═══════════════════════════════════════════════════════════════
    #                    LIVE DATA FEED
    # ═══════════════════════════════════════════════════════════════
    
    def connect_live_data(
        self,
        subscriptions: List[Dict[str, Any]],
        on_event: Callable[[str, dict], None]
    ) -> None:
        """
        Connect to live data feed
        
        Args:
            subscriptions: List of subscription configs
            on_event: Generic callback for all events
                     Signature: (event_type: str, data: dict) -> None
        
        Subscription examples:
            [
                {"asset_id": "0x1234..."},  # Book updates for specific asset
                {"market": "CRYPTO-ETH-USD"}   # All trades in market
            ]
        """
        
        # Check if WebSocket is available
        if not self.ws_available:
            print("[WebSocketCore] Cannot connect live data: WebSocket client not available (stub mode)")
            return
        
        self._live_data_callback = on_event
        
        def process_live_event(event):
            try:
                message = event.json
                event_type = message.get("type")
                if event_type and self._live_data_callback:
                    self._live_data_callback(event_type, message)
            except Exception as e:
                print(f"Error processing live event: {e}")
        
        def run_live_socket():
            self.live_data_connected = True
            try:
                self.client.live_data_socket(
                    subscriptions=subscriptions,
                    process_event=process_live_event,
                    creds=self.api_creds
                )
            finally:
                self.live_data_connected = False
        
        self._live_data_thread = Thread(target=run_live_socket, daemon=True)
        self._live_data_thread.start()
    
    # ═══════════════════════════════════════════════════════════════
    #                    CONNECTION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════
    
    def disconnect_all(self) -> None:
        """Disconnect all WebSocket connections"""
        # Mark as disconnected (this will stop monitoring loops)
        self.market_connected = False
        self.user_connected = False
        self.live_data_connected = False
        
        # Update connection state dict
        self.connection_state = {
            'market': False,
            'user': False,
            'live_data': False
        }
        
        # Clear orderbooks
        self.orderbooks.clear()
        
        # Note: The WebSocket thread will continue until the next reconnect attempt
        # due to lomond's persist() behavior, but marking disconnected will prevent
        # our monitoring loops from processing data
    
    def is_connected(self) -> bool:
        """Check if any WebSocket is connected"""
        return (
            self.market_connected or 
            self.user_connected or 
            self.live_data_connected
        )
    
    def get_orderbook(self, token_id: str) -> Optional[Dict]:
        """
        Get orderbook data for a specific token
        
        Args:
            token_id: Token ID to get orderbook for
            
        Returns:
            dict with orderbook data, or None if token not found
        """
        if token_id in self.orderbooks:
            return self.orderbooks[token_id].get_orderbook()
        return None
    
    def get_all_orderbooks(self) -> Dict[str, Dict]:
        """
        Get all orderbook data for all subscribed tokens
        
        Returns:
            dict mapping token_id to orderbook data
        """
        return {
            token_id: ob.get_orderbook() 
            for token_id, ob in self.orderbooks.items()
        }
    
    def get_subscribed_tokens(self) -> list:
        """
        Get list of all currently subscribed token IDs
        
        Returns:
            list of token_id strings
        """
        return list(self.orderbooks.keys())
    
    def set_market_slugs(self, token_to_market: Dict[str, str]) -> None:
        """
        Set market slugs for orderbooks
        
        Args:
            token_to_market: Dict mapping token_id to market_slug
        """
        for token_id, market_slug in token_to_market.items():
            if token_id in self.orderbooks:
                self.orderbooks[token_id].set_market_slug(market_slug)
    
    @property
    def connection_status(self) -> Dict[str, bool]:
        """Get status of all connections"""
        return {
            "market": self.market_connected,
            "user": self.user_connected,
            "live_data": self.live_data_connected
        }


# ═══════════════════════════════════════════════════════════════
#                    HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def create_orderbook_subscription(market_id: str, assets: List[str] = ["YES", "NO"]) -> dict:
    """Create orderbook subscription config"""
    return {
        "topic": "agg_orderbook",
        "market": market_id,
        "assets": assets
    }

def create_trades_subscription(market_id: str) -> dict:
    """Create trades subscription config"""
    return {
        "topic": "trades",
        "market": market_id
    }

def create_user_subscription(market_id: str) -> dict:
    """Create user orders subscription config (requires auth)"""
    return {
        "topic": "clob_user",
        "market": market_id
    }


# ...existing code...

# ═══════════════════════════════════════════════════════════════
#                    TESTING & DEMO
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Test WebSocket Manager with real Polymarket feeds
    
    Usage:
        python -m PMTerminal.core.websocket
    """
    import time

    YES_TOKEN = "18343134191781390338706117950809371935207471732225103576701507454188936834377"
    NO_TOKEN = "11130821479462670924992395579501640462002624823776508142717086195486388580728"

    def print_orderbook(data):
        print(f"OrderBook update:")
        for key, value in data.items():
            print(f"{key}: {value}")

    def print_price_change(data):
        print(f"Price Change:")
        for key, value in data.items():
            print(f"{key}: {value}")

    def print_last_trade(data):
        print(f"Last trade price:")
        for key, value in data.items():
            print(f"{key}: {value}")

    data = WebSocketCore()


    data.connect_market(
        token_ids=[YES_TOKEN],
        on_orderbook=print_orderbook,
        on_price_change=print_price_change,
        on_last_trade=print_last_trade
    )

    while True:
        time.sleep(10)
  
    
    
    
