"""
Order Executor - Wrapper around existing utils/trading functions
"""
from typing import Optional, Dict, Any, List
import asyncio
import sys
from pathlib import Path


# Add project root to path BEFORE imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import existing trading utilities
try:
    from fqs.utils.trading.create_order import create_order
    from fqs.utils.trading.buy import buy
    from fqs.utils.trading.sell import sell
    from fqs.utils.trading.cancel_order import cancel_order as cancel_order_util
    from fqs.utils.trading.get_orders import get_orders, get_order, get_open_orders, get_orders_summary
    from fqs.utils.trading.create_limit_order import create_limit_order, create_buy_limit_order, create_sell_limit_order
    from py_clob_client.order_builder.constants import BUY, SELL
    UTILS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: trading utils not available: {e}")
    UTILS_AVAILABLE = False


class OrdersCore:
    """
    Execute trading orders via existing utils/trading functions
    
    Features:
    - Place limit orders
    - Place market orders
    - Cancel orders
    - Get order status
    - Get active orders
    """
    
    def __init__(self):
        """
        Initialize order executor (uses utils, no client needed)
        """
        self._initialized = UTILS_AVAILABLE
    
    async def initialize(self, private_key: Optional[str] = None) -> None:
        """
        Initialize order executor (utils handle auth automatically)
        
        Args:
            private_key: Not used - utils load from env
        """
        if not UTILS_AVAILABLE:
            print("Warning: Trading utils not available, running in demo mode")
            self._initialized = False
            return
        
        self._initialized = True
        print("✅ OrdersCore initialized (using utils/trading)")
    
    async def execute_limit_order(
        self,
        token_id: str,
        side: str,  # "BUY" or "SELL"
        price: float,
        size: float
    ) -> Dict[str, Any]:
        """
        Execute a limit order
        
        Args:
            token_id: Token ID to trade
            side: "BUY" or "SELL"
            price: Limit price
            size: Order size in shares
            
        Returns:
            Order result dictionary
        """
        if not self._initialized or not self.client:
            return {
                "success": False,
                "message": "CLOB client not initialized",
                "order_id": None
            }
        
        try:
            # Convert side to py-clob-client format
    async def execute_market_order(
        self,
        token_id: str,
        side: str,  # "BUY" or "SELL"
        size: float,
        slippage: float = 0.05  # 5% default slippage tolerance
    ) -> Dict[str, Any]:
        """
        Execute a market order
        
        Args:
            token_id: Token ID to trade
            side: "BUY" or "SELL"
            size: Order size in shares
            slippage: Maximum acceptable slippage (default 5%)
            
        Returns:
            Order result dictionary
        """
        if not self._initialized or not self.client:
            return {
                "success": False,
                "message": "CLOB client not initialized",
                "order_id": None
            }
        
        try:
            # Get current market price from orderbook
            book = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.get_order_book(token_id)
            )
            
            # Determine market price based on side
            if side.upper() == "BUY":
                # For buying, use best ask price
                market_price = float(book.get("asks", [[0, 0]])[0][0]) if book.get("asks") else None
                if market_price:
                    # Add slippage tolerance
                    limit_price = market_price * (1 + slippage)
                else:
                    return {
                        "success": False,
                        "message": "No asks available in orderbook",
                        "order_id": None
                    }
            else:
                # For selling, use best bid price
                market_price = float(book.get("bids", [[0, 0]])[0][0]) if book.get("bids") else None
                if market_price:
                    # Subtract slippage tolerance
                    limit_price = market_price * (1 - slippage)
                else:
                    return {
                        "success": False,
                        "message": "No bids available in orderbook",
                        "order_id": None
                    }
            
            # Execute as limit order with market price + slippage
            return await self.execute_limit_order(token_id, side, limit_price, size)
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Market order execution failed: {str(e)}",
                "order_id": None,
                "error": str(e)
            }xcept Exception as e:
            return {
                "success": False,
                "message": f"Order execution failed: {str(e)}",
                "order_id": None,
                "error": str(e)
            }
    
    async def execute_market_order(
        self,
        token_id: str,
        side: str,  # "BUY" or "SELL"
        size: int
    ) -> Dict[str, Any]:
        """
        Execute a market order
        
        Args:
            token_id: Token ID to trade
            side: "BUY" or "SELL"
            size: Order size in shares
            
        Returns:
            Order result dictionary
        """
        # TODO: Implement actual market order execution
        await asyncio.sleep(0.1)  # Simulate API call
        
        return {
            "success": False,
            "message": "Market order execution not yet implemented",
            "order_id": None
        }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an existing order using utils/trading/cancel_order.py
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Cancellation result
        """
        if not self._initialized:
            return {
                "success": False,
                "message": "OrdersCore not initialized"
            }
        
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: cancel_order_util(order_id)
            )
            
            return {
                "success": True,
                "message": "Order cancelled successfully",
                "result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Order cancellation failed: {str(e)}",
                "error": str(e)
            }
    
    async def cancel_all_orders(self) -> Dict[str, Any]:
        """
        Cancel all active orders
        
        Returns:
            Cancellation result with count
        """
        if not self._initialized or not self.client:
            return {
                "success": False,
                "message": "CLOB client not initialized",
                "cancelled_count": 0
            }
        
        try:
            # Get all active orders first
            orders_result = await self.get_active_orders()
            if not orders_result.get("success"):
                return orders_result
            
            orders = orders_result.get("orders", [])
            cancelled_count = 0
            errors = []
            
            # Cancel each order
            for order in orders:
                order_id = order.get("id") or order.get("order_id")
                if order_id:
                    result = await self.cancel_order(order_id)
                    if result.get("success"):
                        cancelled_count += 1
                    else:
                        errors.append(f"{order_id}: {result.get('message')}")
            
            return {
                "success": True,
                "message": f"Cancelled {cancelled_count}/{len(orders)} orders",
                "cancelled_count": cancelled_count,
                "total_orders": len(orders),
                "errors": errors if errors else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Bulk cancellation failed: {str(e)}",
                "cancelled_count": 0,
                "error": str(e)
            }
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get order status
        
        Args:
            order_id: Order ID
            
        Returns:
            Order status dictionary
        """
        if not self._initialized or not self.client:
            return {
                "success": False,
                "message": "CLOB client not initialized",
                "order": None
            }
        
        try:
            order = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.get_order(order_id)
            )
            
            return {
                "success": True,
                "message": "Order retrieved successfully",
                "order": order
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get order status: {str(e)}",
                "order": None,
                "error": str(e)
            }
    
    async def get_active_orders(self, market: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all active orders using utils/trading/get_orders.py
        
        Args:
            market: Optional market filter
        
        Returns:
            List of active orders
        """
        if not self._initialized:
            return {
                "success": True,
                "orders": [],
                "message": "OrdersCore not initialized (demo mode)"
            }
        
        try:
            # Get open orders using utility
            orders = await asyncio.get_event_loop().run_in_executor(
                None,
                get_open_orders
            )
            
            # Filter by market if specified
            if market and isinstance(orders, list):
                orders = [o for o in orders if o.get("market") == market]
            
            return {
                "success": True,
                "orders": orders if orders else [],
                "count": len(orders) if orders else 0,
                "message": f"Retrieved {len(orders) if orders else 0} active orders"
            }
            
        except Exception as e:
            return {
                "success": False,
                "orders": [],
                "count": 0,
                "message": f"Failed to get active orders: {str(e)}",
                "error": str(e)
            }
    
    async def get_orderbook(self, token_id: str) -> Dict[str, Any]:
        """
        Get orderbook for a token
        
        Args:
            token_id: Token ID
            
        Returns:
            Orderbook data
        """
        if not self._initialized or not self.client:
            return {
                "success": False,
                "message": "CLOB client not initialized",
                "orderbook": None
            }
        
        try:
            book = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.get_order_book(token_id)
            )
            
            return {
                "success": True,
                "message": "Orderbook retrieved successfully",
                "orderbook": book
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get orderbook: {str(e)}",
                "orderbook": None,
                "error": str(e)
            }
