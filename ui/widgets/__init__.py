"""
PMTerminal UI Widgets
Reusable UI components for the terminal interface
"""

# Import only existing widgets
try:
    from .header import MainHeader
except ImportError:
    MainHeader = None

try:
    from .logo import Logo
except ImportError:
    Logo = None

try:
    from .command_input import CommandInput
except ImportError:
    CommandInput = None

from .orderbook import OrderBookWidget, OrderBookContainer

try:
    from .football_widget import FootballWidget
except ImportError:
    FootballWidget = None

try:
    from .open_orders import OpenOrdersWidget
except ImportError:
    OpenOrdersWidget = None

try:
    from .price_ticker import PriceTickerWidget
except ImportError:
    PriceTickerWidget = None

try:
    from .trade_history import TradeHistoryWidget
except ImportError:
    TradeHistoryWidget = None

try:
    from .position_summary import PositionSummaryWidget
except ImportError:
    PositionSummaryWidget = None

__all__ = [
    "OrderBookWidget",
    "OrderBookContainer",
]

# Add optional widgets if they exist
if MainHeader is not None:
    __all__.append("MainHeader")
if Logo is not None:
    __all__.append("Logo")
if CommandInput is not None:
    __all__.append("CommandInput")
if FootballWidget is not None:
    __all__.append("FootballWidget")
if OpenOrdersWidget is not None:
    __all__.append("OpenOrdersWidget")
if PriceTickerWidget is not None:
    __all__.append("PriceTickerWidget")
if TradeHistoryWidget is not None:
    __all__.append("TradeHistoryWidget")
if PositionSummaryWidget is not None:
    __all__.append("PositionSummaryWidget")
