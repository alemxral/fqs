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
