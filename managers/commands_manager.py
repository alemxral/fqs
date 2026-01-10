"""
CommandsManager - minimal and reliable command dispatcher with explanatory comments.

Purpose
- Provide a simple async queue-based command processing service used by UI screens.
- Keep behaviour deterministic and easy to reason about:
  * submit() enqueues a CommandRequest and returns a Future
  * a single background worker consumes the queue and calls handlers
  * handlers return (message, success, navigation)
  * CommandsManager builds a CommandResponse dataclass and:
      - sets the awaiting Future result (so the submitter can await it)
      - notifies all subscribers with the same CommandResponse (for logs/other screens)
- Logging and a couple of helper diagnostics are provided.

Concurrency model
- Everything runs on asyncio event loop(s). The manager expects to be used from the same loop
  (Textual uses asyncio) so we avoid mixing threads here.
- Subscriber callbacks are called synchronously from the worker loop — they should be fast,
  or delegate heavy work back to the main loop if needed.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
import time
import json
from pathlib import Path
from datetime import datetime

# local logger setup (compatibly imported)
try:
    from PMTerminal.utils.logger import setup_command_logger
except Exception:
    # fallback import attempts for different run modes
    try:
        from ..utils.logger import setup_command_logger  # type: ignore
    except Exception:
        import sys
        from pathlib import Path
        PROJECT_ROOT = Path(__file__).resolve().parents[2]
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        from PMTerminal.utils.logger import setup_command_logger  # type: ignore

# ------------------------
# Typing aliases
# ------------------------
CommandParts = List[str]
HandlerResult = Tuple[str, bool, Optional[str]]   # (message, success, navigation)
Handler = Callable[["CommandRequest"], Awaitable[HandlerResult]]
NotifyCallback = Callable[["CommandResponse"], None]  # subscriber signature

# ------------------------
# Data classes
# ------------------------
@dataclass
class CommandRequest:
    """
    One queued command.
    - origin: who called submit (screen name, etc.)
    - raw: original command string
    - parts: tokenized command words
    - session: optional caller context
    - meta: optional metadata (CommandsManager preserves it into CommandResponse)
    - response_future: asyncio.Future returned to caller by submit(); manager will set_result(resp)
    """
    origin: str
    raw: str
    parts: CommandParts = field(default_factory=list)
    session: Optional[Dict[str, Any]] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    response_future: Optional[asyncio.Future] = None


@dataclass
class CommandResponse:
    """
    Structured response delivered both to the awaiting future and to subscribers.
    - meta is copied from the CommandRequest.meta so caller-generated fields (e.g., client_trace_id)
      are preserved and visible to subscribers.
    """
    origin: str
    raw: str
    message: str
    success: bool
    navigation: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


# ------------------------
# Helper: support sync or async handlers
# ------------------------
async def maybe_await(maybe):
    if asyncio.iscoroutine(maybe):
        return await maybe
    return maybe


# ------------------------
# CommandsManager class
# ------------------------
class CommandsManager:
    """
    Core command manager used by screens.
    Key public methods:
      - start() / stop(): lifecycle management (worker)
      - submit(origin, command, meta=...): enqueue + returns Future that resolves to CommandResponse
      - register_handler(root, handler): add command handlers (handler(req) -> (message, success, nav))
      - subscribe(cb) / unsubscribe(cb): register UI log callbacks

    Important behaviour notes:
      - submit auto-starts the worker if not running (convenience to avoid "enqueued but not processed")
      - Handlers must return a 3-tuple; manager converts this to CommandResponse.
      - The manager will try to set_result on the Future; if the Future is already done/cancelled,
        the manager logs and continues, but subscribers will still receive the CommandResponse.
    """
    def __init__(self, core: Optional[Any] = None, *, app: Optional[Any] = None, logger: Optional[Any] = None):
        self.core = core
        self.app = app  # Reference to main app for accessing request_manager

        # internal queue and worker task
        self._queue: "asyncio.Queue[CommandRequest]" = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False

        # registered handlers and subscribers
        self._handlers: Dict[str, Handler] = {}
        self._subscribers: List[NotifyCallback] = []

        # small diagnostic map for active handler tasks (optional)
        self._active_tasks: Dict[int, asyncio.Task] = {}

        # logger: writes to PMTerminal/logs/commands.log (setup_command_logger creates it)
        self.logger = logger or setup_command_logger()

        # register default handlers (help, exit, hello)
        self._register_defaults()
    
    def _save_ws_tokens_to_file(self, token_ids: List[str], market_slug: Optional[str] = None) -> None:
        """
        Save active WebSocket token IDs to a JSON file for easy access.
        
        Args:
            token_ids: List of token IDs (YES and NO tokens)
            market_slug: Optional market slug for context
        """
        try:
            # Define the path to save the data
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            file_path = data_dir / "ws_active_tokens.json"
            
            # Prepare the data
            ws_data = {
                "timestamp": datetime.now().isoformat(),
                "market_slug": market_slug,
                "token_count": len(token_ids),
                "tokens": {
                    "all": token_ids,
                    "YES": [tid for tid in token_ids if tid],  # Will be first if ordered
                    "NO": [tid for tid in token_ids if tid]   # Will be second if ordered
                }
            }
            
            # If we have exactly 2 tokens, label them properly
            if len(token_ids) == 2:
                ws_data["tokens"]["YES"] = [token_ids[0]]
                ws_data["tokens"]["NO"] = [token_ids[1]]
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(ws_data, f, indent=2)
            
            self.logger.info(f"Saved {len(token_ids)} active token IDs to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save WebSocket tokens to file: {e}", exc_info=True)

    # ---------- Lifecycle ----------
    async def start(self) -> None:
        """Start the worker loop (idempotent)."""
        if self._running:
            self.logger.debug("start() called but already running")
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        self.logger.info("CommandsManager started (worker launched)")

    async def stop(self) -> None:
        """Stop the worker loop cleanly by sending a sentinel."""
        if not self._running:
            self.logger.debug("stop() called but not running")
            return
        self._running = False
        await self._queue.put(CommandRequest(origin="__shutdown__", raw="__shutdown__"))
        if self._worker_task:
            await self._worker_task
        self._worker_task = None
        self.logger.info("CommandsManager stopped")

    # ---------- Submit ----------
    async def submit(self, origin: str, command: str, session: Optional[Dict] = None, meta: Optional[Dict] = None) -> asyncio.Future:
        """
        Enqueue a command and return a Future that resolves to CommandResponse.

        Practical notes:
        - The caller should await the returned Future; it will be resolved after the handler runs.
        - 'meta' can contain arbitrary client data. A common field is 'client_trace_id' used to
          correlate the response in subscribers with the awaiting caller.
        """
        # auto-start worker (convenience)
        if not self._running:
            self.logger.debug("submit() called while not running - auto-starting worker")
            try:
                await self.start()
            except Exception:
                self.logger.exception("Auto-start failed")

        parts = [p for p in command.strip().split() if p]
        req = CommandRequest(origin=origin, raw=command, parts=parts, session=session or {}, meta=meta or {})
        loop = asyncio.get_running_loop()
        req.response_future = loop.create_future()
        # attach a trace id if none; useful for logs and correlation
        req.meta.setdefault("_trace_id", f"{int(time.time()*1000)}-{id(req)}")
        await self._queue.put(req)
        self.logger.debug("Enqueued command from %s: %s (queue=%d) trace=%s", origin, command, self._queue.qsize(), req.meta.get("_trace_id"))
        return req.response_future

    # ---------- Subscribers ----------
    def subscribe(self, cb: NotifyCallback) -> None:
        """Add a subscriber callback that receives every CommandResponse. Keep callbacks fast."""
        if cb not in self._subscribers:
            self._subscribers.append(cb)
            self.logger.debug("Subscriber added (total=%d)", len(self._subscribers))

    def unsubscribe(self, cb: NotifyCallback) -> None:
        """Remove a previously added subscriber."""
        try:
            self._subscribers.remove(cb)
            self.logger.debug("Subscriber removed (total=%d)", len(self._subscribers))
        except ValueError:
            pass

    # ---------- Worker loop ----------
    async def _worker_loop(self) -> None:
        """
        Background consumer loop:
        - awaits items from the queue,
        - dispatches to the handler,
        - wraps handler result into CommandResponse,
        - attempts to set the awaiting Future,
        - notifies all subscribers with the CommandResponse.
        """
        self.logger.debug("Worker loop started")
        try:
            while True:
                # small log so you can tell the worker is alive
                try:
                    self.logger.debug("Worker waiting for next command (queue=%d)", self._queue.qsize())
                except Exception:
                    pass

                req = await self._queue.get()
                # immediate log on dequeuing
                self.logger.debug("Dequeued command '%s' from %s (trace=%s)", req.raw, req.origin, req.meta.get("_trace_id"))

                # sentinel ends the loop
                if req.origin == "__shutdown__" and req.raw == "__shutdown__":
                    self.logger.debug("Worker loop received shutdown sentinel")
                    break

                try:
                    # call handler and get CommandResponse
                    resp = await self._dispatch(req)
                except Exception as e:
                    # create an error response if something unexpected happens
                    self.logger.exception("Unhandled exception while dispatching command '%s'", req.raw)
                    resp = CommandResponse(origin=req.origin, raw=req.raw, message=f"Internal error: {e}", success=False, meta=req.meta)

                # Attempt to set the caller's Future (best-effort)
                try:
                    if req.response_future and not req.response_future.done():
                        req.response_future.set_result(resp)
                        self.logger.debug("Set result for command '%s' (trace=%s)", req.raw, req.meta.get("_trace_id"))
                    else:
                        self.logger.debug("Response future already done/cancelled for command '%s' (trace=%s)", req.raw, req.meta.get("_trace_id"))
                except Exception:
                    self.logger.exception("Failed to set result for command '%s' (trace=%s)", req.raw, req.meta.get("_trace_id"))

                # Notify subscribers (deliver the same CommandResponse)
                for cb in list(self._subscribers):
                    try:
                        cb(resp)
                    except Exception:
                        # subscriber errors should not stop the manager
                        self.logger.exception("Subscriber callback error while notifying for command '%s'", req.raw)
        finally:
            self.logger.debug("Worker loop exiting")

    # ---------- Dispatch ----------
    async def _dispatch(self, req: CommandRequest) -> CommandResponse:
        """
        Call the handler for the command root and translate its tuple result to CommandResponse.
        Handlers can be synchronous (return tuple) or async (return coroutine that yields tuple).
        """
        if not req.parts:
            return CommandResponse(origin=req.origin, raw=req.raw, message="Empty command", success=False, meta=req.meta)

        root = req.parts[0].lower()
        handler = self._handlers.get(root, self._handle_unknown)

        trace = req.meta.get("_trace_id")
        self.logger.info("Dispatching command '%s' from %s (trace=%s)", req.raw, req.origin, trace)

        # run handler (may be sync or async)
        try:
            result = await maybe_await(handler(req))
            # expect (message, success, navigation)
            try:
                message, success, navigation = result
            except Exception:
                self.logger.exception("Handler returned invalid result for command '%s' (trace=%s)", req.raw, trace)
                return CommandResponse(origin=req.origin, raw=req.raw, message="Handler returned invalid result", success=False, meta=req.meta)

            self.logger.info("Command '%s' handled (trace=%s) -> success=%s message=%s", req.raw, trace, success, message)
            return CommandResponse(origin=req.origin, raw=req.raw, message=message, success=bool(success), navigation=navigation, meta=req.meta)
        except asyncio.CancelledError:
            self.logger.warning("Handler task cancelled for command '%s' (trace=%s)", req.raw, trace)
            return CommandResponse(origin=req.origin, raw=req.raw, message="Command cancelled", success=False, meta=req.meta)
        except Exception as e:
            self.logger.exception("Exception while running handler for command '%s' (trace=%s)", req.raw, trace)
            return CommandResponse(origin=req.origin, raw=req.raw, message=f"Handler error: {e}", success=False, meta=req.meta)
        finally:
            # If we were tracking handler tasks for diagnostics we'd clean them here.
            pass

    # ---------- Default handlers ----------
    def _register_defaults(self) -> None:
        self.register_handler("help", self._handle_help)
        self.register_handler("exit", self._handle_exit)
        self.register_handler("hello", self._handle_hello)
        self.register_handler("ws", self._handle_ws)
        self.register_handler("status", self._handle_status)
        self.register_handler("see", self._handle_see)
        self.register_handler("refresh", self._handle_refresh)
        self.register_handler("quickbuy", self._handle_quickbuy)
        # Flask API-based handlers for football trading
        self.register_handler("buy", self._handle_buy)
        self.register_handler("sell", self._handle_sell)
        self.register_handler("balance", self._handle_balance)
        self.register_handler("score", self._handle_score)
        self.register_handler("time", self._handle_time)
        # New extended commands
        self.register_handler("markets", self._handle_markets)
        self.register_handler("orders", self._handle_orders)
        self.register_handler("positions", self._handle_positions)
        self.register_handler("trades", self._handle_trades)

    def register_handler(self, root_cmd: str, handler: Handler) -> None:
        """Add or override a handler for a root command token."""
        self._handlers[root_cmd.lower()] = handler
        self.logger.debug("Handler registered for '%s'", root_cmd.lower())
    
    @property
    def handlers(self) -> dict:
        """Get registered handlers (for testing)."""
        return self._handlers

    async def _handle_help(self, req: CommandRequest) -> HandlerResult:
        help_text = """Available Commands:

═══════════════════════════════════════════════════════════════════════
GENERAL COMMANDS
═══════════════════════════════════════════════════════════════════════
  help                        - Show this help
  exit                        - Return to welcome screen
  status                      - Show system status

═══════════════════════════════════════════════════════════════════════
WEBSOCKET COMMANDS
═══════════════════════════════════════════════════════════════════════
  ws sub [token_ids...]       - Subscribe to WebSocket (by token IDs)
  ws sub <slug>               - Subscribe to WebSocket (by market slug)
  ws off                      - Disconnect WebSocket
  ws status                   - Show WebSocket connection status

═══════════════════════════════════════════════════════════════════════
DATA COMMANDS
═══════════════════════════════════════════════════════════════════════
  see slug <slug>             - Auto-detect and show event/market data
  see event <slug>            - Show event data as table
  see market <slug>           - Show market data as table
  clear see                   - Clear all query results

═══════════════════════════════════════════════════════════════════════
BALANCE COMMANDS
═══════════════════════════════════════════════════════════════════════
  refresh balance             - Fetch fresh balance from blockchain

═══════════════════════════════════════════════════════════════════════
QUICKBUY COMMANDS
═══════════════════════════════════════════════════════════════════════
  quickbuy see                - Show configuration
  quickbuy setup <prop> <val> - Update property
  quickbuy execute yes        - Execute quick buy YES (or Ctrl+Y)
  quickbuy execute no         - Execute quick buy NO (or Ctrl+N)
  quickbuy pending            - Show pending auto-sells
  quickbuy cancel <order_id>  - Cancel auto-sell

QuickBuy Properties:
  amount_percent   - % of wallet (0-100)
  auto_sell        - Enable/disable auto-sell (true/false)
  auto_sell_time   - Seconds before auto-sell
  shortcut_yes     - Keyboard shortcut for YES (default: ctrl+y)
  shortcut_no      - Keyboard shortcut for NO (default: ctrl+n)

═══════════════════════════════════════════════════════════════════════
PROFILE & STRATEGY MANAGEMENT
═══════════════════════════════════════════════════════════════════════
  quickbuy profile current              - Show current active profile
  quickbuy profile list                 - List all available profiles
  quickbuy profile switch <name>        - Switch to different profile
  quickbuy profile create <name> [base] - Create new profile

Available Profiles:
  generic      - Standard trading (uses generic strategy)
  football     - Football goal trading (simple strategy)
  football_ml  - Football with ML predictions (linear regression)

═══════════════════════════════════════════════════════════════════════
FOOTBALL PROFILE COMMANDS (when football/football_ml profile active)
═══════════════════════════════════════════════════════════════════════
Match Setup:
  quickbuy football score <home> <away>      - Set match score
  quickbuy football time <minute> [+injury]  - Set match time
  quickbuy football timer start              - Start match timer
  quickbuy football timer stop               - Stop match timer
  quickbuy football side <home|away>         - Set tracked team

Match Statistics (for ML strategy):
  quickbuy football stats possession <home%>        - Set possession
  quickbuy football stats shots <home> <away>       - Set shots
  quickbuy football stats corners <home> <away>     - Set corners
  quickbuy football stats attacks <home> <away>     - Set attacks
  quickbuy football stats momentum <-1 to +1>       - Set momentum

Examples:
  quickbuy profile switch football_ml
  quickbuy football score 1 0
  quickbuy football time 67
  quickbuy football timer start
  quickbuy football side home
  quickbuy football stats possession 58
  quickbuy football stats shots 8 5
  Ctrl+Y  (execute quick buy based on ML predictions)

═══════════════════════════════════════════════════════════════════════
MARKET COMMANDS
═══════════════════════════════════════════════════════════════════════
  markets search <query>      - Search for markets by keyword
  markets activate <slug>     - Activate market for trading
  markets list                - List available football markets

═══════════════════════════════════════════════════════════════════════
ORDER MANAGEMENT
═══════════════════════════════════════════════════════════════════════
  orders list                 - Show all open orders
  orders cancel <order_id>    - Cancel a specific order
  orders cancel all           - Cancel all open orders

═══════════════════════════════════════════════════════════════════════
POSITION & TRADE TRACKING
═══════════════════════════════════════════════════════════════════════
  positions show              - Display current positions
  positions pnl               - Show P&L summary
  trades history              - Show trade history
  trades recent               - Show recent trades
  trades today                - Show today's trades

═══════════════════════════════════════════════════════════════════════
KEYBOARD SHORTCUTS
═══════════════════════════════════════════════════════════════════════
  Ctrl+Y    - Quick buy YES token (customizable)
  Ctrl+N    - Quick buy NO token (customizable)
  Escape    - Go back
  R         - Refresh
  C         - Clear
  F1        - Help
"""
        return (help_text, True, None)

    async def _handle_exit(self, req: CommandRequest) -> HandlerResult:
        return ("Returning to welcome screen", True, "welcome")

    async def _handle_unknown(self, req: CommandRequest) -> HandlerResult:
        return (f"Unknown command: {req.parts[0]}", False, None)
    
    async def _handle_status(self, req: CommandRequest) -> HandlerResult:
        """Show system status and diagnostics"""
        try:
            status_lines = ["System Status:"]
            
            # Check core module
            if self.core:
                status_lines.append("✓ Core module: OK")
                
                # Check websocket manager
                if hasattr(self.core, 'websocket_manager'):
                    ws_manager = self.core.websocket_manager
                    is_connected = ws_manager.is_connected()
                    status_lines.append(f"✓ WebSocket manager: OK (Connected: {is_connected})")
                    
                    if is_connected:
                        conn_status = ws_manager.connection_status
                        status_lines.append(f"  - Market: {conn_status.get('market', False)}")
                        status_lines.append(f"  - User: {conn_status.get('user', False)}")
                        status_lines.append(f"  - Live Data: {conn_status.get('live_data', False)}")
                    
                    # Check orderbook cache
                    if hasattr(self, '_orderbook_cache') and self._orderbook_cache:
                        status_lines.append(f"✓ Orderbook cache: {len(self._orderbook_cache)} token(s)")
                        for token_id, data in self._orderbook_cache.items():
                            token_short = f"{token_id[:8]}...{token_id[-4:]}"
                            bids_count = len(data.get('bids', []))
                            asks_count = len(data.get('asks', []))
                            last_update = data.get('last_update')
                            update_str = f"{int(time.time() - last_update)}s ago" if last_update else "never"
                            status_lines.append(f"  - {token_short}: {bids_count} bids, {asks_count} asks (updated {update_str})")
                    else:
                        status_lines.append("  - No cached orderbooks")
                else:
                    status_lines.append("✗ WebSocket manager: NOT FOUND")
                
                # Check other core modules
                if hasattr(self.core, 'wallet'):
                    status_lines.append("✓ Wallet module: OK")
                if hasattr(self.core, 'orders'):
                    status_lines.append("✓ Orders module: OK")
            else:
                status_lines.append("✗ Core module: NOT INITIALIZED")
            
            # Check command manager
            status_lines.append(f"✓ Commands manager: Running={self._running}, Queue={self._queue.qsize()}")
            
            return ("\n".join(status_lines), True, None)
        except Exception as e:
            self.logger.error(f"Failed to get status: {e}", exc_info=True)
            return (f"Status check failed: {e}", False, None)

    async def _handle_hello(self, req: CommandRequest) -> HandlerResult:
        name = req.parts[1] if len(req.parts) > 1 else None
        origin = req.origin or "unknown"
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        if name:
            return (f"Hello, {name}! (from {origin} at {ts} UTC)", True, None)
        return (f"Hello! (from {origin} at {ts} UTC)", True, None)
    


    async def _handle_ws(self, req: CommandRequest) -> HandlerResult:
        """
        WebSocket subscription handler
        
        Commands:
            ws sub <token_id1> <token_id2> ...  # Subscribe by specific token IDs
            ws sub <slug>                        # Subscribe by event/market slug (auto-lookup tokens)
            ws sub                               # Subscribe to default YES/NO tokens
            ws off                               # Disconnect WebSocket
        
        Returns:
            HandlerResult: (message, success, navigation)
        """
        # Default tokens
        YES_TOKEN = "18343134191781390338706117950809371935207471732225103576701507454188936834377"
        NO_TOKEN = "11130821479462670924992395579501640462002624823776508142717086195486388580728"
        
        if len(req.parts) < 2:
            return ("Usage: 'ws sub [token_ids...]' or 'ws off'", False, None)
        
        subcommand = req.parts[1].lower()
        
        # Validate core module availability
        if not self.core:
            self.logger.error("Core module not initialized in CommandsManager")
            return ("Core module not available. Please restart the application.", False, None)
        
        if not hasattr(self.core, 'websocket_manager'):
            self.logger.error("WebSocket manager not found in core module")
            return ("WebSocket manager not initialized. Check core module setup.", False, None)
        
        ws_manager = self.core.websocket_manager
        
        # Handle 'ws off' - disconnect
        if subcommand == "off":
            try:
                if not ws_manager.is_connected():
                    return ("WebSocket not connected", False, None)
                
                ws_manager.disconnect_all()
                
                # Clear orderbook cache if exists
                if hasattr(self, '_orderbook_cache'):
                    self._orderbook_cache.clear()
                
                # Signal UI to clear (via meta flag that screens can check)
                req.meta['clear_ui'] = True
                
                # Clear the saved token file when disconnecting
                try:
                    data_dir = Path(__file__).parent.parent / "data"
                    file_path = data_dir / "ws_active_tokens.json"
                    if file_path.exists():
                        file_path.unlink()
                        self.logger.info(f"Cleared WebSocket token file: {file_path}")
                except Exception as clear_error:
                    self.logger.warning(f"Failed to clear token file: {clear_error}")
                
                self.logger.info("WebSocket disconnected via command - UI clear requested")
                return ("WebSocket disconnected - UI data cleared", True, None)
                
            except Exception as e:
                self.logger.error(f"Failed to disconnect WebSocket: {e}", exc_info=True)
                return (f"Failed to disconnect: {str(e)}", False, None)
        
        # Handle 'ws sub' - subscribe
        elif subcommand == "sub":
            try:
                # Check if already connected
                if ws_manager.is_connected():

                    ws_manager.disconnect_all()
                
                # Get arguments from command or use defaults
                raw_args = req.parts[2:] if len(req.parts) > 2 else [YES_TOKEN, NO_TOKEN]
                
                token_ids = []
                
                # Check if first argument looks like a market/event slug (not a token ID)
                # Token IDs are long numeric strings, slugs contain hyphens/letters
                slug = None  # Store slug for later
                if raw_args and ('-' in raw_args[0] or not raw_args[0].isdigit()):
                    # This looks like a slug (event or market) - look up token IDs
                    slug = raw_args[0]  # Store the slug
                    self.logger.info(f"Detected slug: {slug}, looking up token IDs...")
                    
                    try:
                        # Use FetchManager to auto-detect event vs market (same logic as 'see' command)
                        if not hasattr(self.core, 'gamma_api_manager'):
                            from fqs.core.fetch import FetchManager
                            self.core.gamma_api_manager = FetchManager(logger=self.logger)
                            self.logger.info("Initialized FetchManager for Gamma API")
                        
                        gamma_api = self.core.gamma_api_manager
                        
                        # Extract table data (auto-detects event vs market)
                        table_data = gamma_api.extract_market_table_data(slug)
                        
                        # Extract all token IDs from all markets in the response
                        for market in table_data.get('markets', []):
                            market_token_ids = market.get('token_ids', [])
                            token_ids.extend(market_token_ids)
                        
                        if not token_ids:
                            return (f"No tokens found for slug '{slug}'", False, None)
                        
                        # Store token_to_market mapping in session for later use
                        token_to_market_map = table_data.get('token_to_market', {})
                        if req.session:
                            req.session['token_to_market'] = token_to_market_map
                        
                        # Log what we found
                        event_title = table_data.get('event_title', slug)
                        num_markets = len(table_data.get('markets', []))
                        self.logger.info(f"Found {len(token_ids)} tokens across {num_markets} market(s) for '{event_title}'")
                        
                    except ValueError as e:
                        return (f"Slug not found: {str(e)}", False, None)
                    except Exception as e:
                        self.logger.error(f"Failed to lookup slug '{slug}': {e}", exc_info=True)
                        return (f"Failed to lookup slug: {str(e)}", False, None)
                else:
                    # These are token IDs - process as before
                    # Handle comma-separated tokens (split and clean)
                    for token in raw_args:
                        # Split by comma and strip whitespace
                        tokens = [t.strip() for t in token.split(',') if t.strip()]
                        token_ids.extend(tokens)
                
                # Remove duplicates while preserving order
                seen = set()
                token_ids = [t for t in token_ids if not (t in seen or seen.add(t))]
                
                self.logger.info(f"Attempting to connect WebSocket with {len(token_ids)} token(s): {[t[:8]+'...' for t in token_ids]}")
                
                # Store token IDs in session for screen access
                if req.session:
                    req.session["ws_token_ids"] = token_ids
                
                # Get token_to_market mapping from session (if available)
                token_to_market_map = req.session.get('token_to_market', {}) if req.session else {}
                
                # Initialize orderbook cache (per-token storage)
                if not hasattr(self, '_orderbook_cache'):
                    self._orderbook_cache = {}
                
                # Initialize cache for each token
                for token_id in token_ids:
                    market_slug = token_to_market_map.get(token_id, 'unknown')
                    self._orderbook_cache[token_id] = {
                        'token_id': token_id,
                        'market_slug': market_slug,  # NEW: store market slug for this token
                        'bids': [],
                        'asks': [],
                        'best_bid': None,
                        'best_ask': None,
                        'timestamp': None,
                        'last_update': None
                    }
                    self.logger.info(f"Initialized cache for token {token_id[:8]}...{token_id[-4:]} (market: {market_slug})")
                
                # Connect to WebSocket with callbacks that update the cache
                def on_orderbook_update(data):
                    """
                    Handle orderbook summary updates (event_type: 'book')
                    This gives full orderbook snapshot
                    """
                    token_id = data.get('token_id')
                    if token_id and token_id in self._orderbook_cache:
                        import time
                        # Full update - replace all data
                        self._orderbook_cache[token_id].update({
                            'bids': data.get('bids', []),
                            'asks': data.get('asks', []),
                            'best_bid': data.get('best_bid'),
                            'best_ask': data.get('best_ask'),
                            'timestamp': data.get('timestamp'),
                            'last_update': time.time()
                        })
                        self.logger.debug(f"OrderBook full update for token {token_id[:8]}... (bids: {len(data.get('bids', []))}, asks: {len(data.get('asks', []))})")
                
                def on_price_change(data):
                    """
                    Handle price change updates (event_type: 'price_change')
                    This gives partial updates to existing orderbook
                    """
                    token_id = data.get('token_id')
                    if token_id and token_id in self._orderbook_cache:
                        import time
                        # Partial update - merge with existing data
                        cache_entry = self._orderbook_cache[token_id]
                        
                        # Update bids/asks if provided
                        if 'bids' in data:
                            cache_entry['bids'] = data['bids']
                        if 'asks' in data:
                            cache_entry['asks'] = data['asks']
                        if 'best_bid' in data:
                            cache_entry['best_bid'] = data['best_bid']
                        if 'best_ask' in data:
                            cache_entry['best_ask'] = data['best_ask']
                        if 'timestamp' in data:
                            cache_entry['timestamp'] = data['timestamp']
                        
                        cache_entry['last_update'] = time.time()
                        self.logger.debug(f"Price change for token {token_id[:8]}...")
                
                def on_last_trade(data):
                    """
                    Handle last trade updates (event_type: 'last_trade_price')
                    This updates based on executed trades
                    """
                    token_id = data.get('token_id')
                    if token_id and token_id in self._orderbook_cache:
                        import time
                        # Trade execution might affect orderbook
                        cache_entry = self._orderbook_cache[token_id]
                        
                        # Update bids/asks if provided
                        if 'bids' in data:
                            cache_entry['bids'] = data['bids']
                        if 'asks' in data:
                            cache_entry['asks'] = data['asks']
                        if 'best_bid' in data:
                            cache_entry['best_bid'] = data['best_bid']
                        if 'best_ask' in data:
                            cache_entry['best_ask'] = data['best_ask']
                        if 'timestamp' in data:
                            cache_entry['timestamp'] = data['timestamp']
                        
                        cache_entry['last_update'] = time.time()
                        self.logger.debug(f"Last trade for token {token_id[:8]}... (price: {data.get('price', 'N/A')})")
                
                ws_manager.connect_market(
                    token_ids=token_ids,
                    on_orderbook=on_orderbook_update,
                    on_price_change=on_price_change,
                    on_last_trade=on_last_trade
                )
                
                # NEW: Set market slugs for orderbooks after connection
                if token_to_market_map:
                    ws_manager.set_market_slugs(token_to_market_map)
                    self.logger.info(f"Set market slugs for {len(token_to_market_map)} token(s)")
                
                token_display = ", ".join([f"{t[:8]}..." for t in token_ids])
                self.logger.info(f"WebSocket connected to {len(token_ids)} token(s): {token_display}")
                
                # Save token IDs to JSON file for easy access
                self._save_ws_tokens_to_file(token_ids, market_slug=slug)
                
                # Update QuickBuy manager with YES and NO token IDs
                if self.app and hasattr(self.app, 'request_manager'):
                    request_manager = self.app.request_manager
                    if hasattr(request_manager, 'quickbuy_manager') and request_manager.quickbuy_manager:
                        quickbuy_manager = request_manager.quickbuy_manager
                        try:
                            # Store both YES and NO token IDs
                            quickbuy_manager._yes_token_id = token_ids[0] if len(token_ids) > 0 else None
                            quickbuy_manager._no_token_id = token_ids[1] if len(token_ids) > 1 else None
                            self.logger.info(f"QuickBuy tokens updated - YES: {quickbuy_manager._yes_token_id[:10] if quickbuy_manager._yes_token_id else 'N/A'}..., NO: {quickbuy_manager._no_token_id[:10] if quickbuy_manager._no_token_id else 'N/A'}...")
                        except Exception as e:
                            self.logger.warning(f"Failed to update QuickBuy tokens: {e}")
                
                # Store the slug in meta for UI display
                success_message = f"WebSocket connected to {len(token_ids)} token(s)"
                if slug:
                    req.meta['market_slug'] = slug  # Pass slug to UI
                    success_message += f" [{slug}]"
                
                return (success_message, True, None)
                
            except Exception as e:
                self.logger.error(f"Failed to connect WebSocket: {e}", exc_info=True)
                return (f"Failed to connect: {str(e)}", False, None)
        
        else:
            return (f"Unknown ws subcommand: {subcommand}. Use 'ws sub' or 'ws off'", False, None)
    
    async def _handle_see(self, req: CommandRequest) -> HandlerResult:
        """
        Fetch and display information about events or markets by slug
        
        Commands:
            see slug <slug>           # Auto-detect if it's an event or market slug
            see event <slug>          # Force fetch as event
            see market <slug>         # Force fetch as market
        
        Examples:
            see slug lal-vil-bet-2025-10-18
            see event lal-vil-bet-2025-10-18
            see market will-lakers-beat-warriors-oct-18
        
        Returns:
            HandlerResult: (message, success, navigation)
        """
        if len(req.parts) < 3:
            return (
                "Usage: 'see slug <slug>' or 'see event <slug>' or 'see market <slug>'\n"
                "Example: see slug lal-vil-bet-2025-10-18",
                False,
                None
            )
        
        subcommand = req.parts[1].lower()
        slug = " ".join(req.parts[2:])  # Allow multi-word slugs
        
        # Validate core module availability
        if not self.core:
            self.logger.error("Core module not initialized in CommandsManager")
            return ("Core module not available. Please restart the application.", False, None)
        
        # Get or create gamma_api_manager (using FetchManager)
        if not hasattr(self.core, 'gamma_api_manager'):
            try:
                from fqs.core.fetch import FetchManager
                self.core.gamma_api_manager = FetchManager(logger=self.logger)
                self.logger.info("Initialized FetchManager for Gamma API")
            except Exception as e:
                self.logger.error(f"Failed to initialize FetchManager: {e}", exc_info=True)
                return (f"Failed to initialize Fetch manager: {e}", False, None)
        
        gamma_api = self.core.gamma_api_manager
        
        # Handle different subcommands
        if subcommand == "event":
            # Force fetch as event - use table format
            try:
                self.logger.info(f"Fetching event by slug: {slug}")
                table_data = gamma_api.extract_market_table_data(slug)
                formatted_table = gamma_api.format_market_table(table_data)
                return (formatted_table, True, None)
            except ValueError as e:
                return (str(e), False, None)
            except Exception as e:
                self.logger.error(f"Failed to fetch event: {e}", exc_info=True)
                return (f"Failed to fetch event: {str(e)}", False, None)
        
        elif subcommand == "market":
            # Force fetch as market - use table format
            try:
                self.logger.info(f"Fetching market by slug: {slug}")
                table_data = gamma_api.extract_market_table_data(slug)
                formatted_table = gamma_api.format_market_table(table_data)
                return (formatted_table, True, None)
            except ValueError as e:
                return (str(e), False, None)
            except Exception as e:
                self.logger.error(f"Failed to fetch market: {e}", exc_info=True)
                return (f"Failed to fetch market: {str(e)}", False, None)
        
        elif subcommand == "slug":
            # Auto-detect: try event first, then market
            # Use new table format showing: event-slug, market-slugs, tokenIds, lastTradePrice
            try:
                self.logger.info(f"Auto-detecting slug type for: {slug} (trying event first)")
                
                # Extract table data (auto-detects event vs market)
                table_data = gamma_api.extract_market_table_data(slug)
                
                # Format as table
                formatted_table = gamma_api.format_market_table(table_data)
                
                type_label = "EVENT" if table_data['type'] == 'event' else "MARKET"
                return (f"[Detected as {type_label}]\n{formatted_table}", True, None)
                
            except ValueError as e:
                return (f"Slug '{slug}' not found as either event or market", False, None)
            except Exception as e:
                self.logger.error(f"Failed to fetch slug: {e}", exc_info=True)
                return (f"Failed to fetch data: {str(e)}", False, None)
        
        else:
            return (
                f"Unknown see subcommand: {subcommand}\n"
                "Use: 'see slug <slug>', 'see event <slug>', or 'see market <slug>'",
                False,
                None
            )


    async def _handle_refresh(self, req: CommandRequest) -> HandlerResult:
        """
        Handle 'refresh balance' command - manually fetch balance from blockchain
        
        Usage:
            refresh balance    - Fetch fresh balance and update cache
        """
        if len(req.parts) < 2 or req.parts[1].lower() != "balance":
            return (
                "Usage: refresh balance\n"
                "Fetches fresh balance from blockchain and updates the cache.",
                False,
                None
            )
        
        try:
            # Get app and RequestManager (now an instance, not a mixin)
            if not hasattr(self.core, 'app'):
                return ("Balance refresh not available", False, None)
            
            app = self.core.app
            
            if not hasattr(app, 'request_manager'):
                return ("RequestManager not initialized", False, None)
            
            # Submit both balance_header requests via RequestManager (use_cache=False for fresh data)
            # Funder balance
            funder_future = await app.request_manager.submit(
                origin="RefreshCommand",
                request_type="balance_header",
                params={"use_cache": False}
            )
            
            # Proxy balance
            proxy_future = await app.request_manager.submit(
                origin="RefreshCommand",
                request_type="proxy_balance_header",
                params={"use_cache": False}
            )
            
            # Wait for both responses
            funder_response = await funder_future
            proxy_response = await proxy_future
            
            # Check results
            success_count = 0
            errors = []
            
            if funder_response.success:
                success_count += 1
            else:
                errors.append(f"Funder: {funder_response.message}")
            
            if proxy_response.success:
                success_count += 1
            else:
                errors.append(f"Proxy: {proxy_response.message}")
            
            # Return result
            if success_count == 2:
                return ("Both balances refreshed successfully - check header for updated values", True, None)
            elif success_count == 1:
                return (f"Partial success: {', '.join(errors)}", True, None)
            else:
                return (f"Balance refresh failed: {', '.join(errors)}", False, None)
            
        except Exception as e:
            self.logger.error(f"Failed to refresh balance: {e}", exc_info=True)
            return (f"Failed to refresh balance: {str(e)}", False, None)
    
    async def _handle_quickbuy(self, req: CommandRequest) -> HandlerResult:
        """
        Handle quickbuy commands for quick buy/sell operations with profile support.
        
        Commands:
            quickbuy see                          - Show current configuration
            quickbuy setup <property> <value>     - Update a configuration property
            quickbuy execute <yes|no>             - Execute quick buy
            quickbuy pending                      - Show pending auto-sells
            quickbuy cancel <order_id>            - Cancel a pending auto-sell
            quickbuy profile list                 - List all profiles
            quickbuy profile switch <name>        - Switch to different profile
            quickbuy profile create <name>        - Create new profile
            quickbuy football score <home> <away> - Set match score (football profile)
            quickbuy football time <minute>       - Set match time (football profile)
            quickbuy football timer start|stop    - Control match timer (football profile)
            quickbuy football side <home|away>    - Set tracked team (football profile)
        
        Properties that can be updated:
            - amount_percent: Percentage of funder wallet (0-100)
            - auto_sell: true/false
            - auto_sell_time: Seconds to wait before auto-sell
            - shortcut_yes: Keyboard shortcut for YES (default: ctrl+y)
            - shortcut_no: Keyboard shortcut for NO (default: ctrl+n)
        
        Examples:
            quickbuy see
            quickbuy profile switch football
            quickbuy setup amount_percent 25
            quickbuy football score 1 0
            quickbuy football time 67
            quickbuy execute yes
        """
        if len(req.parts) < 2:
            return (
                "Usage: quickbuy [see|setup|execute|pending|cancel|profile|football]\n"
                "  quickbuy see                       - Show configuration\n"
                "  quickbuy setup <property> <value>  - Update property\n"
                "  quickbuy execute <yes|no>          - Execute quick buy\n"
                "  quickbuy profile list              - List profiles\n"
                "  quickbuy profile switch <name>     - Switch profile\n"
                "  quickbuy football score <h> <a>    - Set match score",
                False, None
            )
        
        subcommand = req.parts[1].lower()
        
        # Get QuickBuyManager from RequestManager
        # RequestManager is on the app, not on core
        quickbuy_manager = None
        if hasattr(self, 'app') and self.app and hasattr(self.app, 'request_manager'):
            request_manager = self.app.request_manager
            if hasattr(request_manager, 'quickbuy_manager'):
                quickbuy_manager = request_manager.quickbuy_manager
        
        if not quickbuy_manager:
            return ("QuickBuy system not available - please check logs", False, None)
        
        # Handle 'see' - show configuration
        if subcommand == "see":
            try:
                config_summary = quickbuy_manager.get_config_summary()
                return (config_summary, True, None)
            except Exception as e:
                self.logger.error(f"Failed to get quickbuy config: {e}", exc_info=True)
                return (f"Failed to get config: {str(e)}", False, None)
        
        # Handle 'setup' - update property
        elif subcommand == "setup":
            if len(req.parts) < 4:
                return (
                    "Usage: quickbuy setup <property> <value>\n"
                    "Properties: amount_percent, auto_sell, auto_sell_time, shortcut_yes, shortcut_no",
                    False, None
                )
            
            property_name = req.parts[2]
            value = " ".join(req.parts[3:])  # Join remaining parts for values with spaces
            
            try:
                message, success = quickbuy_manager.update_property(property_name, value)
                return (message, success, None)
            except Exception as e:
                self.logger.error(f"Failed to update quickbuy property: {e}", exc_info=True)
                return (f"Failed to update: {str(e)}", False, None)
        
        # Handle 'execute' - execute quick buy with token side
        elif subcommand == "execute":
            if len(req.parts) < 3:
                return (
                    "Usage: quickbuy execute <yes|no>\n"
                    "  quickbuy execute yes - Buy YES token\n"
                    "  quickbuy execute no  - Buy NO token\n"
                    "Or use keyboard shortcuts: Ctrl+Y (YES) or Ctrl+N (NO)",
                    False, None
                )
            
            token_side = req.parts[2].upper()
            if token_side not in ("YES", "NO"):
                return ("Token side must be 'yes' or 'no'", False, None)
            
            try:
                message, success = await quickbuy_manager.execute_quick_buy(token_side=token_side, session=req.session)
                return (message, success, None)
            except Exception as e:
                self.logger.error(f"Failed to execute quickbuy: {e}", exc_info=True)
                return (f"Failed to execute: {str(e)}", False, None)
        
        # Handle 'pending' - show pending auto-sells
        elif subcommand == "pending":
            try:
                pending_summary = quickbuy_manager.get_pending_auto_sells()
                return (pending_summary, True, None)
            except Exception as e:
                self.logger.error(f"Failed to get pending auto-sells: {e}", exc_info=True)
                return (f"Failed to get pending: {str(e)}", False, None)
        
        # Handle 'cancel' - cancel auto-sell
        elif subcommand == "cancel":
            if len(req.parts) < 3:
                return ("Usage: quickbuy cancel <order_id>", False, None)
            
            order_id = req.parts[2]
            try:
                message, success = quickbuy_manager.cancel_auto_sell(order_id)
                return (message, success, None)
            except Exception as e:
                self.logger.error(f"Failed to cancel auto-sell: {e}", exc_info=True)
                return (f"Failed to cancel: {str(e)}", False, None)
        
        # Handle 'profile' - profile management
        elif subcommand == "profile":
            if len(req.parts) < 3:
                return (
                    "Usage: quickbuy profile [list|current|switch|create]\n"
                    "  quickbuy profile list          - Show all profiles\n"
                    "  quickbuy profile current       - Show active profile details\n"
                    "  quickbuy profile switch <name> - Switch to profile\n"
                    "  quickbuy profile create <name> - Create new profile",
                    False, None
                )
            
            profile_cmd = req.parts[2].lower()
            
            if profile_cmd == "list":
                try:
                    profiles_list = quickbuy_manager.list_profiles()
                    return (profiles_list, True, None)
                except Exception as e:
                    self.logger.error(f"Failed to list profiles: {e}", exc_info=True)
                    return (f"Failed to list profiles: {str(e)}", False, None)
            
            elif profile_cmd == "current":
                try:
                    active_profile = quickbuy_manager.active_profile
                    config = quickbuy_manager.config
                    
                    current_info = [
                        "Current Active Profile:",
                        "=" * 60,
                        f"Profile ID: {active_profile}",
                        f"Name: {config.name}",
                        f"Strategy: {config.strategy}",
                        f"Amount: {config.amount_percent}% of funder wallet",
                        f"Auto-Sell: {'Enabled' if config.auto_sell else 'Disabled'}",
                        f"Auto-Sell Time: {config.auto_sell_time} seconds",
                        f"Shortcuts: {config.shortcut_yes.upper()} (YES) | {config.shortcut_no.upper()} (NO)",
                        "=" * 60,
                    ]
                    
                    # Add strategy-specific info if available
                    if quickbuy_manager.strategy and hasattr(quickbuy_manager.strategy, 'get_display_info'):
                        strategy_info = quickbuy_manager.strategy.get_display_info()
                        current_info.append("")
                        current_info.append(strategy_info)
                    
                    return ("\n".join(current_info), True, None)
                except Exception as e:
                    self.logger.error(f"Failed to get current profile: {e}", exc_info=True)
                    return (f"Failed to get current profile: {str(e)}", False, None)
            
            elif profile_cmd == "switch":
                if len(req.parts) < 4:
                    return ("Usage: quickbuy profile switch <name>", False, None)
                
                profile_name = req.parts[3]
                try:
                    message, success = quickbuy_manager.switch_profile(profile_name)
                    return (message, success, None)
                except Exception as e:
                    self.logger.error(f"Failed to switch profile: {e}", exc_info=True)
                    return (f"Failed to switch profile: {str(e)}", False, None)
            
            elif profile_cmd == "create":
                if len(req.parts) < 4:
                    return ("Usage: quickbuy profile create <name> [base_profile]", False, None)
                
                profile_name = req.parts[3]
                base_profile = req.parts[4] if len(req.parts) > 4 else None
                try:
                    message, success = quickbuy_manager.create_profile(profile_name, base_profile)
                    return (message, success, None)
                except Exception as e:
                    self.logger.error(f"Failed to create profile: {e}", exc_info=True)
                    return (f"Failed to create profile: {str(e)}", False, None)
            
            else:
                return (f"Unknown profile command: {profile_cmd}", False, None)
        
        # Handle 'football' - delegate to FootballCommands handler
        elif subcommand == "football":
            try:
                from PMTerminal.profiles.football.commands import FootballCommands
                football_handler = FootballCommands(quickbuy_manager)
                return football_handler.handle_command(req.parts, self.logger)
            except ImportError as e:
                self.logger.error(f"Failed to import FootballCommands: {e}", exc_info=True)
                return ("Football module not available", False, None)
            except Exception as e:
                self.logger.error(f"Failed to handle football command: {e}", exc_info=True)
                return (f"Failed to handle football command: {str(e)}", False, None)
        
        else:
            return (f"Unknown quickbuy subcommand: {subcommand}", False, None)

    # ========== FLASK API HANDLERS (Football Trading) ==========
    
    async def _handle_buy(self, req: CommandRequest) -> HandlerResult:
        """
        Handle buy command via Flask API
        
        Usage:
            buy YES <price> <size>
            buy NO <price> <size>
        """
        if len(req.parts) < 4:
            return ("Usage: buy <YES|NO> <price> <size>", False, None)
        
        try:
            side = req.parts[1].upper()
            price = float(req.parts[2])
            size = int(req.parts[3])
            
            if side not in ['YES', 'NO']:
                return ("Side must be YES or NO", False, None)
            
            # Get token ID from session
            session = req.session or {}
            token_key = 'yes_token' if side == 'YES' else 'no_token'
            token_id = session.get(token_key)
            
            if not token_id:
                return (f"No {side} token found in session. Please select a market first.", False, None)
            
            self.logger.info(f"Submitting buy order: {side} @ {price} x {size}")
            
            # Call Flask API
            response = await self.app.api_client.post(
                "/api/order/buy",
                json={
                    "token_id": token_id,
                    "price": price,
                    "size": size
                }
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                order_id = data.get('order', {}).get('order_id', 'N/A')
                return (f"✓ Buy order placed: {side} @ {price} x {size} (ID: {order_id})", True, None)
            else:
                error = data.get('error', 'Unknown error')
                return (f"✗ Buy order failed: {error}", False, None)
                
        except Exception as e:
            self.logger.error(f"Buy command error: {e}", exc_info=True)
            return (f"✗ Buy error: {str(e)}", False, None)
    
    async def _handle_sell(self, req: CommandRequest) -> HandlerResult:
        """
        Handle sell command via Flask API
        
        Usage:
            sell YES <price> <size>
            sell NO <price> <size>
        """
        if len(req.parts) < 4:
            return ("Usage: sell <YES|NO> <price> <size>", False, None)
        
        try:
            side = req.parts[1].upper()
            price = float(req.parts[2])
            size = int(req.parts[3])
            
            if side not in ['YES', 'NO']:
                return ("Side must be YES or NO", False, None)
            
            # Get token ID from session
            session = req.session or {}
            token_key = 'yes_token' if side == 'YES' else 'no_token'
            token_id = session.get(token_key)
            
            if not token_id:
                return (f"No {side} token found in session. Please select a market first.", False, None)
            
            self.logger.info(f"Submitting sell order: {side} @ {price} x {size}")
            
            # Call Flask API
            response = await self.app.api_client.post(
                "/api/order/sell",
                json={
                    "token_id": token_id,
                    "price": price,
                    "size": size
                }
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                order_id = data.get('order', {}).get('order_id', 'N/A')
                return (f"✓ Sell order placed: {side} @ {price} x {size} (ID: {order_id})", True, None)
            else:
                error = data.get('error', 'Unknown error')
                return (f"✗ Sell order failed: {error}", False, None)
                
        except Exception as e:
            self.logger.error(f"Sell command error: {e}", exc_info=True)
            return (f"✗ Sell error: {str(e)}", False, None)
    
    async def _handle_balance(self, req: CommandRequest) -> HandlerResult:
        """
        Handle balance command via Flask API
        
        Usage:
            balance
        """
        try:
            self.logger.info("Fetching wallet balance")
            
            # Call Flask API
            response = await self.app.api_client.get("/api/balance")
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                balance = data.get('balance', 0)
                currency = data.get('currency', 'USDC')
                return (f"Balance: ${balance:.2f} {currency}", True, None)
            else:
                error = data.get('error', 'Unknown error')
                return (f"✗ Balance fetch failed: {error}", False, None)
                
        except Exception as e:
            self.logger.error(f"Balance command error: {e}", exc_info=True)
            return (f"✗ Balance error: {str(e)}", False, None)
    
    async def _handle_score(self, req: CommandRequest) -> HandlerResult:
        """
        Handle manual score update for football widget
        
        Usage:
            score <home>-<away>
            score 2-1
        """
        if len(req.parts) < 2:
            return ("Usage: score <home>-<away> (e.g., score 2-1)", False, None)
        
        try:
            score_str = req.parts[1]
            
            if '-' not in score_str:
                return ("Score format must be: <home>-<away> (e.g., 2-1)", False, None)
            
            home, away = score_str.split('-')
            home_score = int(home.strip())
            away_score = int(away.strip())
            
            self.logger.info(f"Manual score update: {home_score}-{away_score}")
            
            # This would update the football widget through a callback
            # For now, just return success message
            return (f"✓ Score updated: {home_score}-{away_score}", True, None)
            
        except ValueError:
            return ("Invalid score format. Use: score <home>-<away> (e.g., score 2-1)", False, None)
        except Exception as e:
            self.logger.error(f"Score command error: {e}", exc_info=True)
            return (f"✗ Score update error: {str(e)}", False, None)
    
    async def _handle_time(self, req: CommandRequest) -> HandlerResult:
        """
        Handle manual time update for football widget
        
        Usage:
            time <mm:ss>
            time 67:30
        """
        if len(req.parts) < 2:
            return ("Usage: time <mm:ss> (e.g., time 67:30)", False, None)
        
        try:
            time_str = req.parts[1]
            
            if ':' not in time_str:
                return ("Time format must be: <mm:ss> (e.g., 67:30)", False, None)
            
            minute, seconds = time_str.split(':')
            minute_val = int(minute.strip())
            seconds_val = int(seconds.strip())
            
            if not (0 <= minute_val <= 120):
                return ("Minute must be between 0 and 120", False, None)
            
            if not (0 <= seconds_val <= 59):
                return ("Seconds must be between 0 and 59", False, None)
            
            self.logger.info(f"Manual time update: {minute_val}:{seconds_val:02d}")
            
            # This would update the football widget through a callback
            # For now, just return success message
            return (f"✓ Time updated: {minute_val}:{seconds_val:02d}", True, None)
            
        except ValueError:
            return ("Invalid time format. Use: time <mm:ss> (e.g., time 67:30)", False, None)
        except Exception as e:
            self.logger.error(f"Time command error: {e}", exc_info=True)
            return (f"✗ Time update error: {str(e)}", False, None)

    async def _handle_markets(self, req: CommandRequest) -> HandlerResult:
        """
        Handle market operations
        
        Usage:
            markets search <query>    - Search for markets
            markets activate <slug>   - Activate/load a market for trading
            markets list              - List available football markets
        """
        if len(req.parts) < 2:
            return ("Usage: markets [search|activate|list] <args>", False, None)
        
        subcommand = req.parts[1].lower()
        
        try:
            if subcommand == "search":
                if len(req.parts) < 3:
                    return ("Usage: markets search <query>", False, None)
                
                query = " ".join(req.parts[2:])
                self.logger.info(f"Searching markets for: {query}")
                
                # Use fetch manager to search markets
                if hasattr(self.app.core, 'fetch') and self.app.core.fetch:
                    # For now, return a placeholder message
                    return (f"🔍 Searching markets for '{query}'...\n(Market search feature coming soon)", True, None)
                else:
                    return ("Market search unavailable (fetch core not initialized)", False, None)
            
            elif subcommand == "activate":
                if len(req.parts) < 3:
                    return ("Usage: markets activate <slug>", False, None)
                
                market_slug = req.parts[2]
                self.logger.info(f"Activating market: {market_slug}")
                
                # Store in session for use by trading commands
                if req.session is not None:
                    req.session["active_market_slug"] = market_slug
                    return (f"✓ Market activated: {market_slug}\nYou can now use buy/sell commands.", True, None)
                else:
                    return ("Cannot activate market (no session context)", False, None)
            
            elif subcommand == "list":
                self.logger.info("Listing football markets")
                return ("📊 Fetching football markets...\n(Use 'see event <slug>' for detailed market info)", True, None)
            
            else:
                return (f"Unknown markets subcommand: {subcommand}\nUse: search, activate, or list", False, None)
        
        except Exception as e:
            self.logger.error(f"Markets command error: {e}", exc_info=True)
            return (f"✗ Markets command error: {str(e)}", False, None)

    async def _handle_orders(self, req: CommandRequest) -> HandlerResult:
        """
        Handle order operations
        
        Usage:
            orders list               - List all open orders
            orders cancel <order_id>  - Cancel a specific order
            orders cancel all         - Cancel all open orders
        """
        if len(req.parts) < 2:
            return ("Usage: orders [list|cancel] <args>", False, None)
        
        subcommand = req.parts[1].lower()
        
        try:
            # Get orders core
            if not hasattr(self.app.core, 'orders') or not self.app.core.orders:
                return ("Orders core not available", False, None)
            
            orders_core = self.app.core.orders
            
            if subcommand == "list":
                self.logger.info("Fetching open orders")
                
                result = await orders_core.get_active_orders()
                
                if not result.get("success"):
                    return (f"✗ Failed to get orders: {result.get('message')}", False, None)
                
                orders = result.get("orders", [])
                count = len(orders)
                
                if count == 0:
                    return ("No open orders", True, None)
                
                # Format orders list
                msg = f"📋 Open Orders ({count}):\n\n"
                for i, order in enumerate(orders[:10], 1):  # Limit to 10 for display
                    order_id = order.get("id", "N/A")[:8] + "..."
                    side = order.get("side", "N/A")
                    price = order.get("price", 0.0)
                    size = order.get("size", 0.0)
                    status = order.get("status", "N/A")
                    msg += f"{i}. {order_id} | {side} | ${price:.4f} × {size:.2f} | {status}\n"
                
                if count > 10:
                    msg += f"\n... and {count - 10} more"
                
                return (msg, True, None)
            
            elif subcommand == "cancel":
                if len(req.parts) < 3:
                    return ("Usage: orders cancel <order_id> or orders cancel all", False, None)
                
                target = req.parts[2].lower()
                
                if target == "all":
                    self.logger.info("Cancelling all orders")
                    result = await orders_core.cancel_all_orders()
                    
                    if result.get("success"):
                        count = result.get("cancelled_count", 0)
                        return (f"✓ Cancelled {count} order(s)", True, None)
                    else:
                        return (f"✗ {result.get('message')}", False, None)
                else:
                    order_id = target
                    self.logger.info(f"Cancelling order: {order_id}")
                    
                    result = await orders_core.cancel_order(order_id)
                    
                    if result.get("success"):
                        return (f"✓ Order cancelled: {order_id}", True, None)
                    else:
                        return (f"✗ {result.get('message')}", False, None)
            
            else:
                return (f"Unknown orders subcommand: {subcommand}\nUse: list or cancel", False, None)
        
        except Exception as e:
            self.logger.error(f"Orders command error: {e}", exc_info=True)
            return (f"✗ Orders command error: {str(e)}", False, None)

    async def _handle_positions(self, req: CommandRequest) -> HandlerResult:
        """
        Handle position operations
        
        Usage:
            positions show            - Show current positions
            positions pnl             - Show P&L summary
        """
        if len(req.parts) < 2:
            # Default to 'show'
            subcommand = "show"
        else:
            subcommand = req.parts[1].lower()
        
        try:
            self.logger.info(f"Fetching positions ({subcommand})")
            
            # For now, return a placeholder
            # In full implementation, this would query CLOB for positions
            if subcommand == "show":
                return ("💼 Current Positions:\n\n(No positions)\n\nUse 'buy' or 'sell' commands to open positions.", True, None)
            elif subcommand == "pnl":
                return ("📊 P&L Summary:\n\nTotal P&L: $0.00 (0.00%)\nRealized: $0.00\nUnrealized: $0.00", True, None)
            else:
                return (f"Unknown positions subcommand: {subcommand}\nUse: show or pnl", False, None)
        
        except Exception as e:
            self.logger.error(f"Positions command error: {e}", exc_info=True)
            return (f"✗ Positions command error: {str(e)}", False, None)

    async def _handle_trades(self, req: CommandRequest) -> HandlerResult:
        """
        Handle trade history operations
        
        Usage:
            trades history            - Show trade history
            trades recent             - Show recent trades
            trades today              - Show today's trades
        """
        if len(req.parts) < 2:
            # Default to 'recent'
            subcommand = "recent"
        else:
            subcommand = req.parts[1].lower()
        
        try:
            self.logger.info(f"Fetching trade history ({subcommand})")
            
            # For now, return a placeholder
            # In full implementation, this would query trade history from CLOB or database
            if subcommand in ["history", "recent"]:
                return ("📊 Recent Trades:\n\n(No trades yet)\n\nYour executed trades will appear here.", True, None)
            elif subcommand == "today":
                from datetime import datetime
                today = datetime.now().strftime("%Y-%m-%d")
                return (f"📊 Trades for {today}:\n\n(No trades today)\n\nYour executed trades will appear here.", True, None)
            else:
                return (f"Unknown trades subcommand: {subcommand}\nUse: history, recent, or today", False, None)
        
        except Exception as e:
            self.logger.error(f"Trades command error: {e}", exc_info=True)
            return (f"✗ Trades command error: {str(e)}", False, None)

    # ---------- Diagnostics ----------
    def active_handlers_info(self) -> Dict[str, Any]:
        """Return a small diagnostic snapshot: active tasks and queue size."""
        out = {}
        for t_id, task in list(self._active_tasks.items()):
            out[str(t_id)] = {"done": task.done(), "cancelled": task.cancelled(), "coro": repr(task.get_coro())}
        out["queue_size"] = self._queue.qsize()
        return out

    def dump_diagnostics(self) -> None:
        """Write a diagnostic snapshot to the log (useful when debugging from REPL)."""
        info = self.active_handlers_info()
        self.logger.debug("DIAGNOSTIC SNAPSHOT running=%s info=%s", self._running, info)