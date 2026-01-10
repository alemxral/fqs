"""
RequestManager - async queue-based request processing for wallet/balance operations.

Purpose:
- Provide a simple async queue-based request processing service for wallet operations
- Similar to CommandsManager but specialized for balance/wallet requests
- Keep behavior deterministic and easy to reason about:
  * submit() enqueues a RequestQuery and returns a Future
  * a single background worker consumes the queue and calls handlers
  * handlers return (success, data, message)
  * RequestManager builds a RequestResponse dataclass and:
      - sets the awaiting Future result (so the submitter can await it)
      - notifies all subscribers with the same RequestResponse

Concurrency model:
- Everything runs on asyncio event loop
- Subscriber callbacks are called synchronously from worker loop
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
import time

# local logger setup
try:
    from PMTerminal.utils.logger import setup_logger
except Exception:
    try:
        from ..utils.logger import setup_logger  # type: ignore
    except Exception:
        import sys
        from pathlib import Path
        PROJECT_ROOT = Path(__file__).resolve().parents[2]
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        from PMTerminal.utils.logger import setup_logger  # type: ignore

# ------------------------
# Typing aliases
# ------------------------
HandlerResult = Tuple[bool, Dict[str, Any], str]  # (success, data, message)
Handler = Callable[["RequestQuery"], Awaitable[HandlerResult]]
NotifyCallback = Callable[["RequestResponse"], None]


# ------------------------
# Data classes
# ------------------------
@dataclass
class RequestQuery:
    """
    One queued request.
    - origin: who called submit (screen name, widget, etc.)
    - request_type: type of request ('balance', 'balance_header', etc.)
    - params: request parameters (e.g., {'use_cache': True})
    - meta: optional metadata preserved into RequestResponse
    - response_future: asyncio.Future returned to caller by submit()
    """
    origin: str
    request_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
    response_future: Optional[asyncio.Future] = None


@dataclass
class RequestResponse:
    """
    Structured response delivered both to the awaiting future and to subscribers.
    - meta is copied from RequestQuery.meta
    """
    origin: str
    request_type: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)


# ------------------------
# RequestManager class
# ------------------------
class RequestManager:
    """
    Core request manager for wallet/balance operations.
    
    Key public methods:
      - start() / stop(): lifecycle management (worker)
      - submit(origin, request_type, params, meta): enqueue + returns Future that resolves to RequestResponse
      - register_handler(request_type, handler): add request handlers
      - subscribe(cb) / unsubscribe(cb): register callbacks for responses
      
    Usage:
        # Create instance (in app.py)
        self.request_manager = RequestManager(self.core, app=self, logger=self.logger)
        await self.request_manager.start()
        
        # Submit request (from widget)
        future = await app.request_manager.submit("MainHeader", "balance", {"use_cache": True})
        response = await future
        if response.success:
            usdc_balance = response.data.get("usdc_balance", 0.0)
    """
    
    def __init__(self, core: Any, app: Optional[Any] = None, logger: Optional[Any] = None):
        """
        Initialize RequestManager
        
        Args:
            core: CoreModule instance for accessing fetch_manager
            app: Reference to main app (for notifications, screen access)
            logger: Logger instance
        """
        self.core = core
        self.app = app
        
        # internal queue and worker task
        self._queue: "asyncio.Queue[RequestQuery]" = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False
        
        # registered handlers and subscribers
        self._handlers: Dict[str, Handler] = {}
        self._subscribers: List[NotifyCallback] = []
        
        # logger
        self.logger = logger or setup_logger()
        
        # Initialize QuickBuyManager at boot
        try:
            from PMTerminal.managers.quickbuy_manager import QuickBuyManager
            self.quickbuy_manager = QuickBuyManager(core=self.core, logger=self.logger)
            self.logger.info("QuickBuyManager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize QuickBuyManager: {e}", exc_info=True)
            self.quickbuy_manager = None
        
        # register default handlers
        self._register_defaults()
    
    # ---------- Lifecycle ----------
    async def start(self) -> None:
        """Start the worker loop (idempotent)."""
        if self._running:
            self.logger.debug("RequestManager start() called but already running")
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        self.logger.info("RequestManager started (worker launched)")
    
    async def stop(self) -> None:
        """Stop the worker loop cleanly by sending a sentinel."""
        if not self._running:
            self.logger.debug("RequestManager stop() called but not running")
            return
        self._running = False
        await self._queue.put(RequestQuery(origin="__shutdown__", request_type="__shutdown__"))
        if self._worker_task:
            await self._worker_task
        self._worker_task = None
        self.logger.info("RequestManager stopped")
    
    # ---------- Submit ----------
    async def submit(self, origin: str, request_type: str, params: Optional[Dict] = None, meta: Optional[Dict] = None) -> asyncio.Future:
        """
        Enqueue a request and return a Future that resolves to RequestResponse.
        
        Args:
            origin: Who is submitting (e.g., "MainHeader", "BalanceWidget")
            request_type: Type of request ("balance", "balance_header")
            params: Request parameters (e.g., {"use_cache": True})
            meta: Optional metadata for correlation
        
        Returns:
            Future that will resolve to RequestResponse when processed
        """
        # auto-start worker (convenience)
        if not self._running:
            self.logger.debug("submit() called while not running - auto-starting worker")
            try:
                await self.start()
            except Exception:
                self.logger.exception("RequestManager auto-start failed")
        
        req = RequestQuery(
            origin=origin,
            request_type=request_type,
            params=params or {},
            meta=meta or {}
        )
        loop = asyncio.get_running_loop()
        req.response_future = loop.create_future()
        req.meta.setdefault("_trace_id", f"{int(time.time()*1000)}-{id(req)}")
        
        await self._queue.put(req)
        self.logger.debug(
            "Enqueued request from %s: %s (queue=%d) trace=%s",
            origin, request_type, self._queue.qsize(), req.meta.get("_trace_id")
        )
        return req.response_future
    
    # ---------- Subscribers ----------
    def subscribe(self, cb: NotifyCallback) -> None:
        """Add a subscriber callback that receives every RequestResponse."""
        if cb not in self._subscribers:
            self._subscribers.append(cb)
            self.logger.debug("RequestManager subscriber added (total=%d)", len(self._subscribers))
    
    def unsubscribe(self, cb: NotifyCallback) -> None:
        """Remove a previously added subscriber."""
        try:
            self._subscribers.remove(cb)
            self.logger.debug("RequestManager subscriber removed (total=%d)", len(self._subscribers))
        except ValueError:
            pass
    
    # ---------- Worker loop ----------
    async def _worker_loop(self) -> None:
        """
        Background consumer loop:
        - awaits items from the queue
        - dispatches to the handler
        - wraps handler result into RequestResponse
        - attempts to set the awaiting Future
        - notifies all subscribers
        """
        self.logger.debug("RequestManager worker loop started")
        try:
            while True:
                try:
                    self.logger.debug("Worker waiting for next request (queue=%d)", self._queue.qsize())
                except Exception:
                    pass
                
                req = await self._queue.get()
                self.logger.debug(
                    "Dequeued request '%s' from %s (trace=%s)",
                    req.request_type, req.origin, req.meta.get("_trace_id")
                )
                
                # sentinel ends the loop
                if req.origin == "__shutdown__" and req.request_type == "__shutdown__":
                    self.logger.debug("Worker loop received shutdown sentinel")
                    break
                
                try:
                    # call handler and get RequestResponse
                    resp = await self._dispatch(req)
                except Exception as e:
                    # create an error response if something unexpected happens
                    self.logger.exception("Unhandled exception while dispatching request '%s'", req.request_type)
                    resp = RequestResponse(
                        origin=req.origin,
                        request_type=req.request_type,
                        success=False,
                        message=f"Internal error: {e}",
                        meta=req.meta
                    )
                
                # Attempt to set the caller's Future (best-effort)
                try:
                    if req.response_future and not req.response_future.done():
                        req.response_future.set_result(resp)
                        self.logger.debug(
                            "Set result for request '%s' (trace=%s)",
                            req.request_type, req.meta.get("_trace_id")
                        )
                    else:
                        self.logger.debug(
                            "Response future already done/cancelled for request '%s' (trace=%s)",
                            req.request_type, req.meta.get("_trace_id")
                        )
                except Exception:
                    self.logger.exception(
                        "Failed to set result for request '%s' (trace=%s)",
                        req.request_type, req.meta.get("_trace_id")
                    )
                
                # Notify subscribers
                for cb in list(self._subscribers):
                    try:
                        cb(resp)
                    except Exception:
                        self.logger.exception("Subscriber callback failed for request '%s'", req.request_type)
        
        finally:
            self.logger.debug("RequestManager worker loop ended")
    
    # ---------- Dispatch ----------
    async def _dispatch(self, req: RequestQuery) -> RequestResponse:
        """
        Dispatch a request to its handler.
        
        Args:
            req: RequestQuery to process
        
        Returns:
            RequestResponse with result
        """
        handler = self._handlers.get(req.request_type)
        
        if not handler:
            self.logger.warning("No handler for request type '%s'", req.request_type)
            return RequestResponse(
                origin=req.origin,
                request_type=req.request_type,
                success=False,
                message=f"Unknown request type: {req.request_type}",
                meta=req.meta
            )
        
        try:
            success, data, message = await handler(req)
            return RequestResponse(
                origin=req.origin,
                request_type=req.request_type,
                success=success,
                data=data,
                message=message,
                meta=req.meta
            )
        except Exception as e:
            self.logger.exception("Handler failed for request type '%s'", req.request_type)
            return RequestResponse(
                origin=req.origin,
                request_type=req.request_type,
                success=False,
                message=f"Handler error: {e}",
                meta=req.meta
            )
    
    # ---------- Handler registration ----------
    def register_handler(self, request_type: str, handler: Handler) -> None:
        """
        Register a handler for a request type.
        
        Args:
            request_type: Type of request to handle
            handler: Async function that takes RequestQuery and returns (success, data, message)
        """
        self._handlers[request_type] = handler
        self.logger.debug("Registered handler for request type '%s'", request_type)
    
    def _register_defaults(self) -> None:
        """Register default request handlers."""
        self.register_handler("balance", self._handle_balance)
        self.register_handler("balance_header", self._handle_balance_header)
        self.register_handler("proxy_balance", self._handle_proxy_balance)
        self.register_handler("proxy_balance_header", self._handle_proxy_balance_header)
        self.logger.debug("Registered default request handlers")
    
    # ---------- Default handlers ----------
    async def _handle_balance(self, req: RequestQuery) -> HandlerResult:
        """
        Handle 'balance' request - fetch funder balance
        
        Params:
            use_cache: bool (default True) - use cached balance if available
        
        Returns:
            (success, data, message) where data contains:
            - usdc_balance: float
            - pol_balance: float
            - address: str
            - timestamp: str
            - from_cache: bool
        """
        try:
            use_cache = req.params.get("use_cache", True)
            
            # Get or create FetchManager
            if not hasattr(self.core, 'fetch_manager'):
                from PMTerminal.core.fetch import FetchManager
                self.core.fetch_manager = FetchManager(logger=self.logger)
                self.logger.info("Initialized FetchManager for balance requests")
            
            fetch_manager = self.core.fetch_manager
            
            # Try cache first if requested
            if use_cache:
                cached = fetch_manager.get_cached_balance()
                if cached:
                    self.logger.debug("Returning cached balance")
                    return (
                        True,
                        {
                            "usdc_balance": cached.get("usdc_balance", 0.0),
                            "pol_balance": cached.get("pol_balance", 0.0),
                            "address": cached.get("address", "Unknown"),
                            "timestamp": cached.get("timestamp", ""),
                            "from_cache": True
                        },
                        "Balance loaded from cache"
                    )
            
            # Fetch fresh from blockchain
            self.logger.info("Fetching fresh balance from blockchain...")
            
            try:
                result = fetch_manager.get_funder_balance()
            except ValueError as ve:
                # Specific error for missing PRIVATE_KEY
                error_msg = f"Configuration error: {str(ve)}"
                self.logger.error(error_msg)
                if self.app and hasattr(self.app, 'notify'):
                    self.app.notify(
                        f"⚠️ {error_msg}\nPlease check PMTerminal/config/.env file",
                        severity="warning",
                        timeout=10
                    )
                return (False, {}, error_msg)
            except Exception as e:
                error_msg = f"Blockchain fetch error: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                if self.app and hasattr(self.app, 'notify'):
                    self.app.notify(f"✗ {error_msg}", severity="error", timeout=5)
                return (False, {}, error_msg)
            
            # Notify on successful fresh fetch
            if self.app and hasattr(self.app, 'notify'):
                self.app.notify(
                    f"✓ Balance updated: ${result.get('usdc_balance', 0.0):.2f} USDC",
                    severity="information",
                    timeout=3
                )
            
            self.logger.info(f"Balance fetched: ${result.get('usdc_balance', 0.0):.2f} USDC")
            
            return (
                True,
                {
                    "usdc_balance": result.get("usdc_balance", 0.0),
                    "pol_balance": result.get("pol_balance", 0.0),
                    "address": result.get("address", "Unknown"),
                    "timestamp": result.get("timestamp", ""),
                    "from_cache": False
                },
                "Balance fetched successfully"
            )
            
        except Exception as e:
            error_msg = f"Failed to get funder balance: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            # Notify error
            if self.app and hasattr(self.app, 'notify'):
                self.app.notify(f"✗ Balance fetch failed: {str(e)}", severity="error", timeout=5)
            
            return (False, {}, error_msg)
    
    async def _handle_balance_header(self, req: RequestQuery) -> HandlerResult:
        """
        Handle 'balance_header' request - fetch balance and update header widget
        
        Params:
            use_cache: bool (default False) - use cached balance if available
        
        Returns:
            (success, data, message)
        """
        try:
            use_cache = req.params.get("use_cache", False)
            
            # First, get the balance using the balance handler
            balance_req = RequestQuery(
                origin=req.origin,
                request_type="balance",
                params={"use_cache": use_cache},
                meta=req.meta
            )
            success, balance_data, message = await self._handle_balance(balance_req)
            
            if not success:
                return (False, {}, message)
            
            # Update header widget if app and screen available
            if self.app and hasattr(self.app, 'screen'):
                try:
                    from ..ui.widgets.main_header import MainHeader
                    header = self.app.screen.query_one(MainHeader)
                    
                    # Update funder info
                    header.update_funder(
                        address=balance_data["address"],
                        balance=balance_data["usdc_balance"]
                    )
                    
                    cache_status = "(cached)" if balance_data.get("from_cache") else "(fresh)"
                    self.logger.debug(
                        f"Header updated with funder balance: "
                        f"${balance_data['usdc_balance']:.2f} {cache_status}"
                    )
                    
                    return (True, balance_data, f"Header updated with balance {cache_status}")
                    
                except Exception as e:
                    self.logger.debug(f"Could not update header: {e}")
                    # Return success anyway since balance was fetched
                    return (True, balance_data, f"Balance fetched but header update failed: {e}")
            else:
                # No app/screen available, just return balance data
                return (True, balance_data, "Balance fetched (no header to update)")
                
        except Exception as e:
            error_msg = f"Failed to refresh balance in header: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            if self.app and hasattr(self.app, 'notify'):
                self.app.notify(f"✗ Header refresh failed: {str(e)}", severity="error", timeout=5)
            
            return (False, {}, error_msg)
    
    async def _handle_proxy_balance(self, req: RequestQuery) -> HandlerResult:
        """
        Handle 'proxy_balance' request - fetch proxy wallet balance
        
        Params:
            use_cache: bool (default True) - use cached balance if available
        
        Returns:
            (success, data, message) where data contains:
            - usdc_balance: float
            - allowance: float (-1 for unlimited)
            - address: str
            - timestamp: str
            - from_cache: bool
        """
        try:
            use_cache = req.params.get("use_cache", True)
            
            # Get or create FetchManager
            if not hasattr(self.core, 'fetch_manager'):
                from PMTerminal.core.fetch import FetchManager
                self.core.fetch_manager = FetchManager(logger=self.logger)
                self.logger.info("Initialized FetchManager for balance requests")
            
            fetch_manager = self.core.fetch_manager
            
            # Try cache first if requested
            if use_cache:
                cached = fetch_manager.get_cached_proxy_balance()
                if cached:
                    self.logger.debug("Returning cached proxy balance")
                    return (
                        True,
                        {
                            "usdc_balance": cached.get("usdc_balance", 0.0),
                            "allowance": cached.get("allowance", 0.0),
                            "address": cached.get("address", "Unknown"),
                            "timestamp": cached.get("timestamp", ""),
                            "from_cache": True
                        },
                        "Proxy balance loaded from cache"
                    )
            
            # Fetch fresh from blockchain
            self.logger.info("Fetching fresh proxy balance from blockchain...")
            
            try:
                result = fetch_manager.get_proxy_balance()
            except ValueError as ve:
                # Specific error for missing PROXY_ADDRESS
                error_msg = f"Configuration error: {str(ve)}"
                self.logger.error(error_msg)
                if self.app and hasattr(self.app, 'notify'):
                    self.app.notify(
                        f"⚠️ {error_msg}\nPlease check PMTerminal/config/.env file",
                        severity="warning",
                        timeout=10
                    )
                return (False, {}, error_msg)
            except Exception as e:
                error_msg = f"Blockchain fetch error: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                if self.app and hasattr(self.app, 'notify'):
                    self.app.notify(f"✗ {error_msg}", severity="error", timeout=5)
                return (False, {}, error_msg)
            
            # Notify on successful fresh fetch
            if self.app and hasattr(self.app, 'notify'):
                allowance_str = "UNLIMITED" if result.get("allowance", 0) == -1 else f"${result.get('allowance', 0):.2f}"
                self.app.notify(
                    f"✓ Proxy balance updated: ${result.get('usdc_balance', 0.0):.2f} USDC (Allowance: {allowance_str})",
                    severity="information",
                    timeout=3
                )
            
            self.logger.info(f"Proxy balance fetched: ${result.get('usdc_balance', 0.0):.2f} USDC")
            
            return (
                True,
                {
                    "usdc_balance": result.get("usdc_balance", 0.0),
                    "allowance": result.get("allowance", 0.0),
                    "address": result.get("address", "Unknown"),
                    "timestamp": result.get("timestamp", ""),
                    "from_cache": False
                },
                "Proxy balance fetched successfully"
            )
            
        except Exception as e:
            error_msg = f"Failed to get proxy balance: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            # Notify error
            if self.app and hasattr(self.app, 'notify'):
                self.app.notify(f"✗ Proxy balance fetch failed: {str(e)}", severity="error", timeout=5)
            
            return (False, {}, error_msg)
    
    async def _handle_proxy_balance_header(self, req: RequestQuery) -> HandlerResult:
        """
        Handle 'proxy_balance_header' request - fetch proxy balance and update header widget
        
        Params:
            use_cache: bool (default False) - use cached balance if available
        
        Returns:
            (success, data, message)
        """
        try:
            use_cache = req.params.get("use_cache", False)
            
            # First, get the balance using the proxy_balance handler
            balance_req = RequestQuery(
                origin=req.origin,
                request_type="proxy_balance",
                params={"use_cache": use_cache},
                meta=req.meta
            )
            success, balance_data, message = await self._handle_proxy_balance(balance_req)
            
            if not success:
                return (False, {}, message)
            
            # Update header widget if app and screen available
            if self.app and hasattr(self.app, 'screen'):
                try:
                    from ..ui.widgets.main_header import MainHeader
                    header = self.app.screen.query_one(MainHeader)
                    
                    # Update proxy info
                    header.update_proxy(
                        address=balance_data["address"],
                        balance=balance_data["usdc_balance"]
                    )
                    
                    cache_status = "(cached)" if balance_data.get("from_cache") else "(fresh)"
                    self.logger.debug(
                        f"Header updated with proxy balance: "
                        f"${balance_data['usdc_balance']:.2f} {cache_status}"
                    )
                    
                    return (True, balance_data, f"Header updated with proxy balance {cache_status}")
                    
                except Exception as e:
                    self.logger.debug(f"Could not update header: {e}")
                    # Return success anyway since balance was fetched
                    return (True, balance_data, f"Proxy balance fetched but header update failed: {e}")
            else:
                # No app/screen available, just return balance data
                return (True, balance_data, "Proxy balance fetched (no header to update)")
                
        except Exception as e:
            error_msg = f"Failed to refresh proxy balance in header: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            if self.app and hasattr(self.app, 'notify'):
                self.app.notify(f"✗ Proxy header refresh failed: {str(e)}", severity="error", timeout=5)
            
            return (False, {}, error_msg)
    
    # ---------- Convenience methods (optional - for backwards compatibility) ----------
    async def get_balance(self, use_cache: bool = True) -> RequestResponse:
        """
        Convenience method to get balance synchronously.
        
        Args:
            use_cache: If True, use cached balance (fast). If False, fetch fresh (slow).
        
        Returns:
            RequestResponse with balance data
        """
        future = await self.submit("DirectCall", "balance", {"use_cache": use_cache})
        return await future
    
    async def refresh_header(self, use_cache: bool = False) -> RequestResponse:
        """
        Convenience method to refresh balance in header.
        
        Args:
            use_cache: If True, use cached balance. If False, fetch fresh.
        
        Returns:
            RequestResponse with result
        """
        future = await self.submit("DirectCall", "balance_header", {"use_cache": use_cache})
        return await future
    
    async def get_proxy_balance_data(self, use_cache: bool = True) -> RequestResponse:
        """
        Convenience method to get proxy balance synchronously.
        
        Args:
            use_cache: If True, use cached balance (fast). If False, fetch fresh (slow).
        
        Returns:
            RequestResponse with proxy balance data
        """
        future = await self.submit("DirectCall", "proxy_balance", {"use_cache": use_cache})
        return await future
    
    async def refresh_proxy_header(self, use_cache: bool = False) -> RequestResponse:
        """
        Convenience method to refresh proxy balance in header.
        
        Args:
            use_cache: If True, use cached balance. If False, fetch fresh.
        
        Returns:
            RequestResponse with result
        """
        future = await self.submit("DirectCall", "proxy_balance_header", {"use_cache": use_cache})
        return await future
    
    # ---------- Address loading methods ----------
    async def load_funder_address(self) -> str:
        """
        Load funder wallet address from config or environment
        
        Priority:
        1. PMTerminal/data/config.json (funder_address field)
        2. FUNDER_ADDRESS environment variable
        
        Returns:
            Funder wallet address or empty string if not found
        """
        try:
            # Determine config path (relative to PMTerminal root)
            config_path = Path(__file__).parent.parent / "data" / "config.json"
            
            # Try config file first
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                    address = config.get("funder_address", "")
                    if address:
                        self.logger.info(f"Loaded funder address from config: {address[:6]}...{address[-4:]}")
                        return address
            
            # Fallback to environment variable
            address = os.getenv("FUNDER_ADDRESS", "")
            if address:
                self.logger.info(f"Loaded funder address from env: {address[:6]}...{address[-4:]}")
            else:
                self.logger.warning("Funder address not found in config or environment")
            
            return address
            
        except Exception as e:
            self.logger.error(f"Failed to load funder address: {e}")
            return ""
    
    async def load_proxy_address(self) -> str:
        """
        Load proxy wallet address from config or environment
        
        Priority:
        1. PMTerminal/data/config.json (proxy_address field)
        2. PROXY_ADDRESS environment variable
        
        Returns:
            Proxy wallet address or empty string if not found
        """
        try:
            # Determine config path (relative to PMTerminal root)
            config_path = Path(__file__).parent.parent / "data" / "config.json"
            
            # Try config file first
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                    address = config.get("proxy_address", "")
                    if address:
                        self.logger.info(f"Loaded proxy address from config: {address[:6]}...{address[-4:]}")
                        return address
            
            # Fallback to environment variable
            address = os.getenv("PROXY_ADDRESS", "")
            if address:
                self.logger.info(f"Loaded proxy address from env: {address[:6]}...{address[-4:]}")
            else:
                self.logger.warning("Proxy address not found in config or environment")
            
            return address
            
        except Exception as e:
            self.logger.error(f"Failed to load proxy address: {e}")
            return ""
