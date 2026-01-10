

from fqs.core.websocket import WebSocketCore
from fqs.core.wallet import WalletCore
from fqs.core.orders import OrdersCore
from fqs.core.fetch import FetchManager
# from fqs.core.cache import CacheCore


class CoreModule:

    def __init__(self):
        self.websocket_manager = WebSocketCore()  # Use consistent naming
        self.websocket = self.websocket_manager    # Alias for backward compatibility
        self.wallet = WalletCore()
        self.orders = OrdersCore()
        self.fetch = FetchManager()
        # self.cache = CacheCore()


