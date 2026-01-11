# Command System Architecture

## Overview

The command system connects the UI (CommandInput widget) to the backend (CommandsManager) through a well-defined flow.

## Architecture Flow

```
┌─────────────────┐
│ CommandInput    │  User types command and presses Enter
│ Widget          │
└────────┬────────┘
         │
         │ on_input_submitted()
         │
         ▼
┌─────────────────┐
│ Screen          │  handle_command(command: str)
│ (HomeScreen/    │  - May handle special commands (e.g., LOOK)
│  TradeScreen)   │  - Submits to CommandsManager
└────────┬────────┘
         │
         │ await commands_manager.submit(origin, command)
         │
         ▼
┌─────────────────┐
│ CommandsManager │  1. Queues command
│                 │  2. Worker processes queue
│                 │  3. Dispatches to handler
│                 │  4. Returns response via Future
│                 │  5. Notifies subscribers
└─────────────────┘
```

## Components

### 1. CommandInput Widget
**File:** `ui/widgets/command_input.py`

**Responsibility:** 
- Capture user input
- Call async handler on Enter
- Clear input after submission

**Key Method:**
```python
async def on_input_submitted(self, event: Input.Submitted):
    command = event.value.strip()
    if command and self.command_handler:
        await self.command_handler(command)
    self.value = ""  # Clear input
```

**Fixed Issues:**
- ✅ Removed incorrect return type expectation (was expecting tuple)
- ✅ Now properly handles async handlers that return None
- ✅ Better error handling with app.logger and notifications

### 2. Screen handle_command()
**Files:** 
- `ui/screens/home_screen.py`
- `ui/screens/football_trade_screen.py`

**Responsibility:**
- Receive command from widget
- Handle screen-specific commands (e.g., LOOK)
- Submit to CommandsManager
- Return None (fire-and-forget pattern)

**Example:**
```python
async def handle_command(self, command: str) -> None:
    # Screen-specific handling
    if command.upper().startswith('LOOK '):
        slug = command[5:].strip()
        await self._load_market_by_slug(slug)
        return
    
    # Submit to CommandsManager
    if hasattr(self.app, 'commands_manager'):
        await self.app.commands_manager.submit(
            origin="HomeScreen",
            command=command
        )
```

### 3. CommandsManager
**File:** `managers/commands_manager.py`

**Responsibility:**
- Queue and process commands asynchronously
- Dispatch to registered handlers
- Return responses via Futures
- Notify subscribers

**Key Methods:**

#### submit()
```python
async def submit(
    origin: str, 
    command: str, 
    session: Optional[Dict] = None, 
    meta: Optional[Dict] = None
) -> asyncio.Future:
    """
    Enqueue command and return Future that resolves to CommandResponse
    """
```

#### register_handler()
```python
def register_handler(self, root_cmd: str, handler: Handler):
    """
    Register a command handler.
    Handler signature: (CommandRequest) -> (message, success, navigation)
    """
```

## Registered Commands

### Navigation & System
- `help` - Show help message
- `exit` - Exit application
- `hello` - Test command
- `status` - System status

### Market Information
- `see <slug|name>` - View market details
- `markets [tag]` - List markets
- `refresh` - Refresh data

### Trading
- `buy <YES|NO> <price> <size>` - Buy shares
- `sell <YES|NO> <price> <size>` - Sell shares
- `quickbuy <YES|NO> [size]` - Quick buy at best price

### Portfolio
- `balance` - Check USDC balance
- `orders` - View open orders
- `positions` - View positions
- `trades` - View trade history

### WebSocket
- `ws connect <token_id>` - Connect to token
- `ws disconnect` - Disconnect
- `ws status` - Connection status

### Match Updates
- `score <home>-<away>` - Update score (e.g., "score 2-1")
- `time <mm:ss>` - Update time (e.g., "time 67:30")

### Special (Screen-Specific)
- `LOOK <slug>` - Load market by slug (HomeScreen only)

## Command Response Flow

1. **User Input:** Types command in CommandInput widget
2. **Widget:** Calls `handle_command(command)`
3. **Screen:** Calls `commands_manager.submit(origin, command)`
4. **Manager:** 
   - Queues the command
   - Worker picks it up
   - Dispatches to handler
   - Handler returns `(message, success, navigation)`
   - Creates `CommandResponse`
   - Sets Future result
   - Notifies subscribers
5. **Screen:** Can await the Future if needed
6. **Subscribers:** Receive response for logging/display

## Subscriber Pattern

Screens can subscribe to all command responses:

```python
def on_mount(self):
    if hasattr(self.app, 'commands_manager'):
        self.app.commands_manager.subscribe(self._on_command_response)

def _on_command_response(self, response: CommandResponse):
    if response.success:
        self.log_output(f"✓ {response.message}")
    else:
        self.log_output(f"✗ {response.message}")
```

## CommandResponse Structure

```python
@dataclass
class CommandResponse:
    origin: str              # Who sent the command
    raw: str                 # Original command string
    message: str             # Response message
    success: bool            # True if successful
    navigation: Optional[str] # Screen to navigate to (if any)
    meta: Dict[str, Any]     # Metadata from request
```

## Common Issues & Fixes

### Issue 1: CommandInput expects tuple return
**Problem:** Widget was expecting `(message, success)` from handler  
**Fix:** Changed to fire-and-forget pattern (handler returns None)

### Issue 2: Commands not processing
**Problem:** Worker not started or handler not registered  
**Fix:** Manager auto-starts on first submit; use `register_handler()`

### Issue 3: No response feedback
**Problem:** Screen doesn't show command results  
**Fix:** Subscribe to responses or await the Future

## Testing

Run the integration test:
```bash
python tests/test_command_integration.py
```

This tests:
- CommandsManager startup/shutdown
- Command submission and response
- Handler registration
- Subscriber callbacks
- Full command flow simulation

## Adding New Commands

1. **Create handler in CommandsManager:**
```python
async def _handle_mycommand(self, req: CommandRequest) -> HandlerResult:
    # Process command
    message = "Command processed"
    success = True
    navigation = None  # or "ScreenName"
    return (message, success, navigation)
```

2. **Register handler:**
```python
def _register_defaults(self):
    # ... existing handlers
    self.register_handler("mycommand", self._handle_mycommand)
```

3. **Update CommandsReferenceScreen:**
Add to `COMMANDS` dict in `ui/screens/commands_reference_screen.py`

4. **Test:**
```python
# In app
await app.commands_manager.submit("Test", "mycommand arg1 arg2")
```

## Accessing Commands Reference

Press **CTRL+H** from any screen to view the Commands Reference screen showing all available commands.
