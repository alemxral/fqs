"""
Polymarket WebSocket Authentication Wrapper
Provides easy WebSocket connection setup with authentication
"""

import asyncio
import json
import os
import time
import hmac
import hashlib
from typing import Dict, Any, Callable, Optional, List
import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")


class PolymarketWebSocket:
    """
    Authenticated WebSocket wrapper for Polymarket CLOB
    """
    
    def __init__(self, 
                 ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market",
                 auto_reconnect: bool = True):
        """
        Initialize WebSocket wrapper
        
        Args:
            ws_url: WebSocket URL
            auto_reconnect: Whether to automatically reconnect on disconnect
        """
        self.ws_url = ws_url
        self.auto_reconnect = auto_reconnect
        self.websocket = None
        self.subscriptions: Dict[str, List[str]] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.is_connected = False
        
        # Load credentials from environment
        self.api_key = os.getenv("CLOB_API_KEY")
        self.api_secret = os.getenv("CLOB_SECRET")
        self.api_passphrase = os.getenv("CLOB_PASS_PHRASE")
        
        if not all([self.api_key, self.api_secret, self.api_passphrase]):
            raise ValueError("Missing required credentials: CLOB_API_KEY, CLOB_SECRET, CLOB_PASS_PHRASE")
    
    def _generate_auth_headers(self) -> Dict[str, str]:
        """
        Generate authentication headers for WebSocket connection
        
        Returns:
            Dict with authentication headers
        """
        timestamp = str(int(time.time()))
        
        # Create signature
        message = timestamp + "GET" + "/ws/market"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "POLY-API-KEY": self.api_key,
            "POLY-SIGNATURE": signature,
            "POLY-TIMESTAMP": timestamp,
            "POLY-PASSPHRASE": self.api_passphrase
        }
        
    async def connect(self):
        """Establish WebSocket connection with authentication"""
        try:
            # Get authentication headers
            headers = self._generate_auth_headers()
            
            # Convert headers to list of tuples for websockets library
            header_list = [(k, v) for k, v in headers.items()]
            
            # Connect to WebSocket
            self.websocket = await websockets.connect(
                self.ws_url,
                additional_headers=header_list,
                ping_interval=30,
                ping_timeout=10
            )
            
            self.is_connected = True
            print(f"✅ Connected to {self.ws_url}")
            
            # Start message listener
            asyncio.create_task(self._message_listener())
            
        except Exception as e:
            print(f"❌ WebSocket connection failed: {e}")
            self.is_connected = False
            raise
    
    async def disconnect(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            print("📡 WebSocket disconnected")
    
    async def _message_listener(self):
        """Listen for incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    print(f"⚠️  Invalid JSON message: {message}")
                except Exception as e:
                    print(f"⚠️  Error handling message: {e}")
        
        except ConnectionClosedError:
            print("📡 WebSocket connection closed")
            self.is_connected = False
            
            if self.auto_reconnect:
                print("🔄 Attempting to reconnect...")
                await self._reconnect()
        
        except WebSocketException as e:
            print(f"❌ WebSocket error: {e}")
            self.is_connected = False
    
    async def _reconnect(self):
        """Attempt to reconnect with exponential backoff"""
        max_retries = 5
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                delay = base_delay * (2 ** attempt)
                print(f"🔄 Reconnection attempt {attempt + 1}/{max_retries} in {delay}s...")
                await asyncio.sleep(delay)
                
                await self.connect()
                
                # Resubscribe to previous subscriptions
                await self._resubscribe()
                
                print("✅ Reconnection successful!")
                return
                
            except Exception as e:
                print(f"❌ Reconnection attempt {attempt + 1} failed: {e}")
        
        print("❌ Max reconnection attempts reached")
    
    async def _resubscribe(self):
        """Resubscribe to all previous subscriptions after reconnection"""
        for subscription_type, markets in self.subscriptions.items():
            for market in markets:
                await self.subscribe(subscription_type, market)
    
    async def _handle_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket messages"""
        message_type = data.get('type', 'unknown')
        
        # Call registered handler if exists
        if message_type in self.message_handlers:
            await self.message_handlers[message_type](data)
        else:
            # Default handler - just print the message
            print(f"📨 {message_type}: {data}")
    
    def register_handler(self, message_type: str, handler: Callable):
        """
        Register a message handler for specific message types
        
        Args:
            message_type: Type of message to handle
            handler: Async function to handle the message
        """
        self.message_handlers[message_type] = handler
    
    async def subscribe(self, subscription_type: str, market_id: str = None):
        """
        Subscribe to market data
        
        Args:
            subscription_type: Type of subscription ('book', 'trades', 'ticker', etc.)
            market_id: Market ID to subscribe to (optional for some types)
        """
        if not self.is_connected:
            raise Exception("WebSocket not connected")
        
        subscription_msg = {
            "type": "subscribe",
            "market": market_id,
            "subscription": subscription_type
        }
        
        # Remove None values
        subscription_msg = {k: v for k, v in subscription_msg.items() if v is not None}
        
        await self.websocket.send(json.dumps(subscription_msg))
        
        # Track subscription for reconnection
        if subscription_type not in self.subscriptions:
            self.subscriptions[subscription_type] = []
        
        if market_id and market_id not in self.subscriptions[subscription_type]:
            self.subscriptions[subscription_type].append(market_id)
        
        print(f"📡 Subscribed to {subscription_type}" + (f" for market {market_id}" if market_id else ""))
    
    async def unsubscribe(self, subscription_type: str, market_id: str = None):
        """
        Unsubscribe from market data
        
        Args:
            subscription_type: Type of subscription to cancel
            market_id: Market ID to unsubscribe from
        """
        if not self.is_connected:
            raise Exception("WebSocket not connected")
        
        unsubscribe_msg = {
            "type": "unsubscribe",
            "market": market_id,
            "subscription": subscription_type
        }
        
        # Remove None values
        unsubscribe_msg = {k: v for k, v in unsubscribe_msg.items() if v is not None}
        
        await self.websocket.send(json.dumps(unsubscribe_msg))
        
        # Remove from tracking
        if subscription_type in self.subscriptions and market_id:
            if market_id in self.subscriptions[subscription_type]:
                self.subscriptions[subscription_type].remove(market_id)
        
        print(f"📡 Unsubscribed from {subscription_type}" + (f" for market {market_id}" if market_id else ""))
    
    async def send_message(self, message: Dict[str, Any]):
        """Send custom message to WebSocket"""
        if not self.is_connected:
            raise Exception("WebSocket not connected")
        
        await self.websocket.send(json.dumps(message))


# Example usage
async def example_usage():
    """Example of how to use the WebSocket wrapper"""
    
    # Create WebSocket instance
    ws = PolymarketWebSocket()
    
    # Register custom message handlers
    async def handle_book_update(data):
        print(f"📖 Book update: {data}")
    
    async def handle_trade(data):
        print(f"💰 Trade: {data}")
    
    ws.register_handler('book', handle_book_update)
    ws.register_handler('trade', handle_trade)
    
    try:
        # Connect
        await ws.connect()
        
        # Example market ID (replace with real one)
        market_id = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        # Subscribe to some data
        await ws.subscribe('book', market_id)
        await ws.subscribe('trades', market_id)
        
        # Keep connection alive
        print("\n⏳ Listening for 60 seconds... (Press Ctrl+C to stop)")
        await asyncio.sleep(60)  # Listen for 1 minute
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
    
    finally:
        await ws.disconnect()


if __name__ == "__main__":
    asyncio.run(example_usage())