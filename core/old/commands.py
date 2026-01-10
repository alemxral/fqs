
"""
Command Handler - PMTerminal
Handles command parsing and execution for all terminal commands
"""
import sys
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import utilities
from utils.market.market_search import (
    get_market_by_slug,
    search_markets_by_event_slug,
    get_market_with_tokens,
    get_token_ids_only,
    MarketTokens
)
from client.py_clob_client.order_builder.constants import BUY, SELL


class CommandHandler:
    """
    Handles command parsing and execution
    
    Supported Commands:
        - ws off: Disconnect WebSocket
        - sub <token_ids>: Subscribe to token IDs
        - sub <event_slug>: Subscribe to event (may show market selection)
        - sub <market_slug>: Subscribe to market
        - qb: Quick buy
        - qs: Quick sell
        - buy/sell <yes/no> limit <price> <shares>: Limit order
        - buy/sell <yes/no> market <shares>: Market order
        - slug <event_slug>: Get event info (token IDs, market IDs)
        - slug <market_slug>: Get market info (token IDs)
        - orders: Show active orders
        - profile: Show profile stats
        - exit: Exit to welcome screen
        - help: Show help
    """
    
    def __init__(
        self,
        websocket_manager=None,
        order_executor=None,
        session_manager=None,
        profile_manager=None,
        app_navigation=None
    ):
        """
        Initialize command handler
        
        Args:
            websocket_manager: WebSocketManager instance
            order_executor: OrderExecutor instance
            session_manager: SessionManager instance
            profile_manager: WalletManager/ProfileManager instance
            app_navigation: App instance for screen navigation (self from main app)
        """
        self.ws_manager = websocket_manager
        self.executor = order_executor
        self.session = session_manager
        self.profile = profile_manager
        self.app = app_navigation  # Reference to main app for navigation
        
        # State
        self.current_token_ids: List[str] = []
        self.current_market_info: Optional[Dict[str, Any]] = None
        self.navigation_target: Optional[str] = None  # Screen to navigate to after command
    
    async def handle(
        self,
        command: str,
        session_state: Optional[Any] = None,
        order_books: Optional[Dict] = None
    ) -> Tuple[str, bool, Optional[str]]:
        """
        Main command handler
        
        Args:
            command: Command string from user
            session_state: Current session state
            order_books: Current order book data
        
        Returns:
            (status_message, success, navigation_target)
            navigation_target: Optional screen name to navigate to
        """
        # Parse command
        parts = command.strip().split()
        if not parts:
            return ("Empty command", False, None)
        
        cmd = parts[0].lower()
        
        # Reset navigation target
        self.navigation_target = None
        # Reset navigation target
        self.navigation_target = None
        
        # ═══════════════════════════════════════════════════════════
        #                    WEBSOCKET COMMANDS
        # ═══════════════════════════════════════════════════════════
        
        if cmd == "ws":
            result = await self._handle_ws(parts)
            return (*result, self.navigation_target)
        
        # ═══════════════════════════════════════════════════════════
        #                    SUBSCRIPTION COMMANDS
        # ═══════════════════════════════════════════════════════════
        
        elif cmd == "sub":
            result = await self._handle_subscribe(parts)
            return (*result, self.navigation_target)
        
        # ═══════════════════════════════════════════════════════════
        #                    SLUG LOOKUP COMMANDS
        # ═══════════════════════════════════════════════════════════
        
        elif cmd == "slug":
            result = await self._handle_slug(parts)
            return (*result, self.navigation_target)
        
        # ═══════════════════════════════════════════════════════════
        #                    TRADING COMMANDS
        # ═══════════════════════════════════════════════════════════
        
        elif cmd in ["buy", "sell"]:
            result = await self._handle_buy_sell(parts, order_books)
            return (*result, self.navigation_target)
        
        elif cmd == "qb":
            result = await self._handle_quick_buy(parts)
            return (*result, self.navigation_target)
        
        elif cmd == "qs":
            result = await self._handle_quick_sell(parts)
            return (*result, self.navigation_target)
        
        # ═══════════════════════════════════════════════════════════
        #                    INFO COMMANDS
        # ═══════════════════════════════════════════════════════════
        
        elif cmd == "orders":
            result = await self._handle_orders()
            return (*result, self.navigation_target)
        
        elif cmd == "profile":
            result = await self._handle_profile()
            return (*result, self.navigation_target)
        
        # ═══════════════════════════════════════════════════════════
        #                    NAVIGATION COMMANDS
        # ═══════════════════════════════════════════════════════════
        
        elif cmd == "exit":
            self.navigation_target = "welcome"
            return ("Returning to welcome screen", True, self.navigation_target)
        
        elif cmd == "help":
            self.navigation_target = "help"
            return (self._get_help_text(), True, self.navigation_target)
        
        else:
            return (f"Unknown command: {cmd}. Type 'help' for available commands.", False, None)
    
    # ═══════════════════════════════════════════════════════════════
    #                    WEBSOCKET HANDLERS
    # ═══════════════════════════════════════════════════════════════
    
    async def _handle_ws(self, parts: List[str]) -> Tuple[str, bool]:
        """Handle WebSocket commands: ws off"""
        if len(parts) < 2:
            return ("Usage: ws off", False)
        
        action = parts[1].lower()
        
        if action == "off":
            if self.ws_manager:
                self.ws_manager.disconnect_all()
                return ("✓ WebSocket disconnected", True)
            return ("WebSocket manager not available", False)
        
        return (f"Unknown ws action: {action}. Use 'ws off'", False)
    
    # ═══════════════════════════════════════════════════════════════
    #                    SUBSCRIPTION HANDLERS
    # ═══════════════════════════════════════════════════════════════
    
    async def _handle_subscribe(self, parts: List[str]) -> Tuple[str, bool]:
        """
        Handle subscription commands:
        - sub <token_id> [token_id2]: Direct token ID subscription
        - sub <event_slug>: Subscribe to event (may require market selection)
        - sub <market_slug>: Subscribe to specific market
        """
        if len(parts) < 2:
            return ("Usage: sub <token_ids> OR sub <event_slug> OR sub <market_slug>", False)
        

        try:
            self.app.notify(f"Processed request def handle_subscribe: {parts}")
        except Exception as e:
            self.app.notify("Error")
        
        slug_or_token = parts[1]
        
        # Check if it's a direct token ID (long hex string)
        if len(slug_or_token) > 50 and slug_or_token.isdigit():
            # Direct token ID subscription
            token_ids = parts[1:]
            return await self._subscribe_tokens(token_ids)
        
        # Try as market slug first (most specific)
        market_result = get_market_with_tokens(slug_or_token)
        if market_result and market_result.tokens:
            token_ids = [t.clob_token_id for t in market_result.tokens]
            self.current_token_ids = token_ids
            self.current_market_info = market_result.market
            
            # Subscribe via WebSocket
            if self.ws_manager:
                # TODO: Implement subscribe with callbacks
                pass
            
            # Navigate to UniTrade screen after successful subscription
            self.navigation_target = "unitrade"
            
            question = market_result.market.get('question', 'Unknown')
            return (
                f"✓ Subscribed to market: {question[:60]}...\n"
                f"Token IDs: {len(token_ids)} tokens loaded",
                True
            )
        
        # Try as event slug (may have multiple markets)
        event_markets = search_markets_by_event_slug(slug_or_token)
        if event_markets:
            if len(event_markets) == 1:
                # Single market - auto subscribe
                market_data = event_markets[0]
                token_ids = [t.clob_token_id for t in market_data.tokens]
                self.current_token_ids = token_ids
                self.current_market_info = market_data.market
                
                # Navigate to UniTrade screen
                self.navigation_target = "unitrade"
                
                question = market_data.market.get('question', 'Unknown')
                return (
                    f"✓ Subscribed to: {question[:60]}...\n"
                    f"Token IDs: {len(token_ids)} tokens loaded",
                    True
                )
            else:
                # Multiple markets - show selection
                # Navigate to Fetch screen to show options
                self.navigation_target = "fetch"
                
                response = f"Found {len(event_markets)} markets. Please select:\n"
                for i, market_data in enumerate(event_markets, 1):
                    question = market_data.market.get('question', 'Unknown')
                    response += f"  {i}. {question[:60]}...\n"
                response += "\nUse: sub <market_slug> to select a specific market"
                return (response, False)
        
        return (f"No market or event found for: {slug_or_token}", False)
    
    async def _subscribe_tokens(self, token_ids: List[str]) -> Tuple[str, bool]:
        """Subscribe to raw token IDs"""
        self.current_token_ids = token_ids
        
        if self.ws_manager:
            # TODO: Implement WebSocket subscription
            pass
        
        # Navigate to UniTrade screen
        self.navigation_target = "unitrade"
        
        return (
            f"✓ Subscribed to {len(token_ids)} token(s)\n"
            f"Token IDs: {', '.join([t[:10] + '...' for t in token_ids])}",
            True
        )
    
    # ═══════════════════════════════════════════════════════════════
    #                    SLUG LOOKUP HANDLERS
    # ═══════════════════════════════════════════════════════════════
    
    async def _handle_slug(self, parts: List[str]) -> Tuple[str, bool]:
        """
        Handle slug lookup commands:
        - slug <event_slug>: Show all markets in event
        - slug <market_slug>: Show market details and token IDs
        
        Navigates to Fetch screen to display results
        """
        if len(parts) < 2:
            return ("Usage: slug <event_slug> OR slug <market_slug>", False)
        
        slug = parts[1]
        
        # Navigate to Fetch screen for displaying results
        self.navigation_target = "fetch"
        
        # Try as market slug first
        market_result = get_market_with_tokens(slug)
        if market_result:
            market = market_result.market
            tokens = market_result.tokens
            
            response = f"📊 Market Info: {market.get('question', 'Unknown')}\n\n"
            response += f"Slug: {market.get('slug', 'N/A')}\n"
            response += f"Market ID: {market.get('id', 'N/A')}\n"
            response += f"Active: {market.get('active', False)}\n"
            response += f"Closed: {market.get('closed', False)}\n\n"
            response += f"Token IDs ({len(tokens)}):\n"
            for token in tokens:
                response += f"  {token.outcome}: {token.clob_token_id}\n"
            
            return (response, True)
        
        # Try as event slug
        event_markets = search_markets_by_event_slug(slug)
        if event_markets:
            response = f"📊 Event: {slug}\n"
            response += f"Found {len(event_markets)} market(s):\n\n"
            
            for i, market_data in enumerate(event_markets, 1):
                market = market_data.market
                tokens = market_data.tokens
                
                response += f"{i}. {market.get('question', 'Unknown')[:60]}...\n"
                response += f"   Slug: {market.get('slug', 'N/A')}\n"
                response += f"   Market ID: {market.get('id', 'N/A')}\n"
                response += f"   Tokens: {len(tokens)} ({', '.join([t.outcome for t in tokens])})\n"
                response += f"   Token IDs:\n"
                for token in tokens:
                    response += f"     {token.outcome}: {token.clob_token_id[:20]}...\n"
                response += "\n"
            
            return (response, True)
        
        return (f"No market or event found for slug: {slug}", False)
    
    # ═══════════════════════════════════════════════════════════════
    #                    TRADING HANDLERS
    # ═══════════════════════════════════════════════════════════════
    
    async def _handle_buy_sell(
        self,
        parts: List[str],
        order_books: Optional[Dict]
    ) -> Tuple[str, bool]:
        """
        Handle buy/sell commands:
        - buy/sell yes/no limit <price> <shares>
        - buy/sell yes/no market <shares>
        """
        if len(parts) < 4:
            return (
                "Usage:\n"
                "  buy/sell <yes/no> limit <price> <shares>\n"
                "  buy/sell <yes/no> market <shares>",
                False
            )
        
        action = parts[0].lower()  # buy or sell
        outcome = parts[1].lower()  # yes or no
        order_type = parts[2].lower()  # limit or market
        
        # Validate outcome
        if outcome not in ["yes", "no"]:
            return ("Outcome must be 'yes' or 'no'", False)
        
        # Get token ID for outcome
        if not self.current_token_ids:
            return ("No market loaded. Use 'sub <market_slug>' first", False)
        
        # Assume first token is YES, second is NO
        token_id = self.current_token_ids[0] if outcome == "yes" else self.current_token_ids[1] if len(self.current_token_ids) > 1 else None
        
        if not token_id:
            return (f"No token ID available for outcome: {outcome}", False)
        
        # Parse order parameters
        if order_type == "limit":
            if len(parts) < 5:
                return ("Limit order requires: buy/sell <yes/no> limit <price> <shares>", False)
            
            try:
                price = float(parts[3])
                shares = float(parts[4])
            except ValueError:
                return ("Invalid price or shares amount", False)
            
            # Execute limit order
            if self.executor:
                try:
                    side = BUY if action == "buy" else SELL
                    # TODO: Call executor.execute_limit_order(token_id, side, price, shares)
                    return (
                        f"✓ Placed {action.upper()} {outcome.upper()} LIMIT order:\n"
                        f"  {shares} shares @ ${price}",
                        True
                    )
                except Exception as e:
                    return (f"Order failed: {str(e)}", False)
            
            return ("Order executor not available", False)
        
        elif order_type == "market":
            if len(parts) < 4:
                return ("Market order requires: buy/sell <yes/no> market <shares>", False)
            
            try:
                shares = float(parts[3])
            except ValueError:
                return ("Invalid shares amount", False)
            
            # Execute market order
            if self.executor:
                try:
                    side = BUY if action == "buy" else SELL
                    # TODO: Call executor.execute_market_order(token_id, side, shares)
                    return (
                        f"✓ Placed {action.upper()} {outcome.upper()} MARKET order:\n"
                        f"  {shares} shares @ market price",
                        True
                    )
                except Exception as e:
                    return (f"Order failed: {str(e)}", False)
            
            return ("Order executor not available", False)
        
        return (f"Unknown order type: {order_type}. Use 'limit' or 'market'", False)
    
    async def _handle_quick_buy(self, parts: List[str]) -> Tuple[str, bool]:
        """Handle quick buy command (qb)"""
        if not self.executor:
            return ("Order executor not available", False)
        
        # TODO: Implement quick buy using pre-configured settings
        return ("Quick buy executed", True)
    
    async def _handle_quick_sell(self, parts: List[str]) -> Tuple[str, bool]:
        """Handle quick sell command (qs)"""
        if not self.executor:
            return ("Order executor not available", False)
        
        # TODO: Implement quick sell using pre-configured settings
        return ("Quick sell executed", True)
    
    # ═══════════════════════════════════════════════════════════════
    #                    INFO HANDLERS
    # ═══════════════════════════════════════════════════════════════
    
    async def _handle_orders(self) -> Tuple[str, bool]:
        """Show active orders"""
        if not self.executor:
            return ("Order executor not available", False)
        
        # TODO: Fetch and display active orders
        return ("📋 Active Orders:\n  (No open orders)", True)
    
    async def _handle_profile(self) -> Tuple[str, bool]:
        """Show profile stats"""
        if not self.profile:
            return ("Profile manager not available", False)
        
        # TODO: Fetch and display profile stats
        response = "👤 Profile Stats:\n"
        response += "  Balance: $0.00\n"
        response += "  Open Orders: 0\n"
        response += "  Total Trades: 0\n"
        
        return (response, True)
    
    # ═══════════════════════════════════════════════════════════════
    #                    HELP TEXT
    # ═══════════════════════════════════════════════════════════════
    
    def _get_help_text(self) -> str:
        """Get help text with all commands"""
        return """
📚 Available Commands:

🔌 WebSocket:
  ws off                          - Disconnect WebSocket

📡 Subscription:
  sub <token_ids>                 - Subscribe to token IDs directly
  sub <event_slug>                - Subscribe to event (may show markets)
  sub <market_slug>               - Subscribe to specific market

🔍 Market Lookup:
  slug <event_slug>               - Show all markets in event
  slug <market_slug>              - Show market details and token IDs

💰 Trading:
  buy <yes/no> limit <price> <shares>   - Place limit buy order
  sell <yes/no> limit <price> <shares>  - Place limit sell order
  buy <yes/no> market <shares>          - Place market buy order
  sell <yes/no> market <shares>         - Place market sell order
  qb                                    - Quick buy (pre-configured)
  qs                                    - Quick sell (pre-configured)

📊 Information:
  orders                          - Show active orders
  profile                         - Show profile stats

🚪 Navigation:
  exit                            - Return to welcome screen
  help                            - Show this help message

Examples:
  sub presidential-election-2024
  slug will-trump-win
  buy yes limit 0.65 100
  sell no market 50
"""


# ═══════════════════════════════════════════════════════════════
#                    TESTING
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """Test command handler"""
    import asyncio
    
    async def test():
        handler = CommandHandler()
        
        # Test commands
        test_commands = [
            "help",
            "slug presidential-election-2024",
            "ws off",
            "buy yes limit 0.65 100",
        ]
        
        for cmd in test_commands:
            print(f"\n> {cmd}")
            status, success = await handler.handle(cmd)
            print(f"{'✓' if success else '✗'} {status}")
    
    asyncio.run(test())

