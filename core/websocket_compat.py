"""
WebSocket Compatibility Layer for Python 3.6+
Provides compatible wrappers that work across all Python 3.x versions
Replaces match/case syntax with if/elif for broader compatibility
"""

from collections.abc import Callable
from json import JSONDecodeError
from typing import Any, Optional, Dict
import sys

try:
    from pydantic import ValidationError
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    ValidationError = Exception

try:
    from lomond import WebSocket
    from lomond.persist import persist
    LOMOND_AVAILABLE = True
except ImportError:
    LOMOND_AVAILABLE = False
    WebSocket = None
    persist = None


# ============= PYTHON 3.X COMPATIBLE EVENT PROCESSORS =============

def process_market_event_compat(event, event_types: Dict[str, type]):
    """
    Python 3.x compatible version of _process_market_event
    Replaces match/case with if/elif for Python 3.6-3.9 compatibility
    """
    try:
        message = event.json
        if isinstance(message, list):
            for item in message:
                try:
                    if 'OrderBookSummaryEvent' in event_types:
                        print(event_types['OrderBookSummaryEvent'](**item), "\n")
                except Exception as e:
                    if PYDANTIC_AVAILABLE and isinstance(e, ValidationError):
                        print(e.errors())
                    else:
                        print(f"Error: {e}")
            return
        
        event_type = message.get("event_type")
        
        if event_type == "book" and 'OrderBookSummaryEvent' in event_types:
            print(event_types['OrderBookSummaryEvent'](**message), "\n")
        elif event_type == "price_change" and 'PriceChangeEvent' in event_types:
            print(event_types['PriceChangeEvent'](**message), "\n")
        elif event_type == "tick_size_change" and 'TickSizeChangeEvent' in event_types:
            print(event_types['TickSizeChangeEvent'](**message), "\n")
        elif event_type == "last_trade_price" and 'LastTradePriceEvent' in event_types:
            print(event_types['LastTradePriceEvent'](**message), "\n")
        else:
            print(message)
    except JSONDecodeError:
        print(event.text)
    except Exception as e:
        if PYDANTIC_AVAILABLE and isinstance(e, ValidationError):
            print(e.errors())
            print(event.json)
        else:
            print(f"Error: {e}")


def process_user_event_compat(event, event_types: Dict[str, type]):
    """Python 3.x compatible - replaces match/case with if/elif"""
    try:
        message = event.json
        event_type = message.get("event_type")
        
        if event_type == "order" and 'OrderEvent' in event_types:
            print(event_types['OrderEvent'](**message), "\n")
        elif event_type == "trade" and 'TradeEvent' in event_types:
            print(event_types['TradeEvent'](**message), "\n")
    except JSONDecodeError:
        print(event.text)
    except Exception as e:
        if PYDANTIC_AVAILABLE and isinstance(e, ValidationError):
            print(event.text)
            print(e.errors(), "\n")
        else:
            print(f"Error: {e}")


def process_live_data_event_compat(event, event_types: Dict[str, type]):
    """Python 3.x compatible - replaces match/case with if/elif"""
    try:
        message = event.json
        msg_type = message.get("type")
        
        if msg_type == "trades" and 'ActivityTradeEvent' in event_types:
            print(event_types['ActivityTradeEvent'](**message), "\n")
        elif msg_type == "orders_matched" and 'ActivityOrderMatchEvent' in event_types:
            print(event_types['ActivityOrderMatchEvent'](**message), "\n")
        elif msg_type in ("comment_created", "comment_removed") and 'CommentEvent' in event_types:
            print(event_types['CommentEvent'](**message), "\n")
        elif msg_type in ("reaction_created", "reaction_removed") and 'ReactionEvent' in event_types:
            print(event_types['ReactionEvent'](**message), "\n")
        elif msg_type in ("request_created", "request_edited", "request_canceled", "request_expired"):
            if 'RequestEvent' in event_types:
                print(event_types['RequestEvent'](**message), "\n")
        elif msg_type in ("quote_created", "quote_edited", "quote_canceled", "quote_expired"):
            if 'QuoteEvent' in event_types:
                print(event_types['QuoteEvent'](**message), "\n")
        elif msg_type == "subscribe" and 'CryptoPriceSubscribeEvent' in event_types:
            print(event_types['CryptoPriceSubscribeEvent'](**message), "\n")
        elif msg_type == "update" and 'CryptoPriceUpdateEvent' in event_types:
            print(event_types['CryptoPriceUpdateEvent'](**message), "\n")
        elif msg_type == "agg_orderbook" and 'LiveDataOrderBookSummaryEvent' in event_types:
            print(event_types['LiveDataOrderBookSummaryEvent'](**message), "\n")
        elif msg_type == "price_change" and 'LiveDataPriceChangeEvent' in event_types:
            print(event_types['LiveDataPriceChangeEvent'](**message), "\n")
        elif msg_type == "last_trade_price" and 'LiveDataLastTradePriceEvent' in event_types:
            print(event_types['LiveDataLastTradePriceEvent'](**message), "\n")
        elif msg_type == "tick_size_change" and 'LiveDataTickSizeChangeEvent' in event_types:
            print(event_types['LiveDataTickSizeChangeEvent'](**message), "\n")
        elif msg_type in ("market_created", "market_resolved"):
            if 'MarketStatusChangeEvent' in event_types:
                print(event_types['MarketStatusChangeEvent'](**message), "\n")
        elif msg_type == "order" and 'LiveDataOrderEvent' in event_types:
            print(event_types['LiveDataOrderEvent'](**message), "\n")
        elif msg_type == "trade" and 'LiveDataTradeEvent' in event_types:
            print(event_types['LiveDataTradeEvent'](**message), "\n")
        else:
            print(message)
    except JSONDecodeError:
        print(event.text)
    except Exception as e:
        if PYDANTIC_AVAILABLE and isinstance(e, ValidationError):
            print(e.errors(), "\n")
            print(event.text)
        else:
            print(f"Error: {e}")


def check_python_compatibility():
    """Check Python version and library compatibility"""
    version = sys.version_info
    
    if version.major < 3:
        return False, f"Python {version.major} not supported (requires 3.6+)"
    
    if version.minor < 6:
        return False, f"Python 3.{version.minor} not supported (requires 3.6+)"
    
    if not LOMOND_AVAILABLE:
        return False, "Lomond library not installed (pip install lomond)"
    
    return True, f"Python {version.major}.{version.minor} is compatible"


def get_compatibility_info():
    """Get detailed compatibility information"""
    version = sys.version_info
    info = {
        'python_version': f"{version.major}.{version.minor}.{version.micro}",
        'is_compatible': version >= (3, 6),
        'has_match_case': version >= (3, 10),
        'lomond_available': LOMOND_AVAILABLE,
        'pydantic_available': PYDANTIC_AVAILABLE,
        'recommended_mode': 'FULL' if version >= (3, 10) else 'COMPAT'
    }
    return info
