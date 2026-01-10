# FQS Project Structure

## 📁 Directory Overview

```
fqs/
├── app.py                      # Main application entry point
├── requirements.txt            # Python dependencies
├── SETUP.md                    # Complete setup instructions
├── README.md                   # Full documentation
├── QUICKSTART.md              # Quick reference guide
├── start.sh                    # Automated startup script
│
├── server/                     # Flask Backend
│   ├── run_flask.py           # Flask server entry point
│   ├── __init__.py            # App factory
│   └── api.py                 # REST API endpoints
│
├── ui/                        # Textual Frontend
│   ├── screens/               # Application screens
│   │   ├── welcome_screen.py  # Entry screen
│   │   ├── home_screen.py     # Market selector
│   │   ├── football_trade_screen.py  # Trading interface
│   │   └── settings_screen.py # Configuration
│   │
│   ├── widgets/               # Reusable UI components
│   │   ├── football_widget.py # Match state display
│   │   ├── orderbook.py       # Orderbook widget
│   │   ├── command_input.py   # Command line input
│   │   ├── main_header.py     # Top header
│   │   └── logo.py            # Application logo
│   │
│   └── styles/
│       └── theme.tcss         # CSS styling
│
├── managers/                   # Business logic managers
│   ├── commands_manager.py    # Command dispatcher
│   ├── requests_manager.py    # Request handler
│   ├── navigation_manager.py  # Screen navigation
│   └── quickbuy_manager.py    # Quick trading
│
├── core/                      # Core functionality
│   ├── core.py                # Module aggregator
│   ├── websocket.py           # WebSocket manager
│   ├── wallet.py              # Wallet operations
│   ├── orders.py              # Order management
│   └── fetch.py               # Data fetching
│
├── client/                    # Polymarket API clients
│   ├── clob_client.py         # CLOB API
│   ├── gamma_client.py        # Gamma API
│   ├── webscoket_client.py    # WebSocket client
│   └── WebSocketWrapper.py    # WS wrapper
│
├── utils/                     # Utility functions
│   ├── logger.py              # Logging setup
│   └── market/                # Market utilities
│
├── config/                    # Configuration
│   ├── settings.py            # App settings
│   └── .env                   # API credentials (not in git)
│
├── data/                      # Data storage
│   └── quickbuy_config.json   # Trading profiles
│
└── logs/                      # Application logs
    ├── app.log
    └── commands.log
```

---

## 🔧 Core Components

### 1. Application (`app.py`)

**Purpose**: Main Textual application class

**Key Features**:
- Initializes CoreModule
- Sets up managers (commands, requests, navigation)
- Creates httpx client for Flask API
- Manages screen lifecycle
- Handles global keybindings

**Main Class**: `QSTerminal(App, NavigationManager)`

**Lifecycle**:
```python
__init__() → on_mount() → _start_managers() → _startup_init()
                                        ↓
                                   on_unmount() → cleanup
```

---

### 2. Flask Backend (`server/`)

#### `run_flask.py`
- Entry point for Flask server
- Runs on `http://127.0.0.1:5000`
- Debug mode enabled by default

#### `api.py`
**Endpoints**:

**Trading**:
- `POST /api/order/buy` - Place buy order
- `POST /api/order/sell` - Place sell order
- `GET /api/balance` - Get wallet balance

**Market Data**:
- `GET /api/markets/football` - List football markets
- `GET /api/market/<slug>` - Get market details + token IDs

**Health**:
- `GET /api/health` - Server health check

**Dependencies**:
- Uses `fqs.client.clob_client.ClobClient`
- Uses `fqs.client.gamma_client.GammaAPIClient`
- Loads credentials from `config/.env`

---

### 3. Screens (`ui/screens/`)

#### `welcome_screen.py`
- First screen shown on startup
- Shows logo and welcome message
- Press Enter → Navigate to Home Screen

#### `home_screen.py`
- Lists active football markets from Flask API
- Displays: match name, YES/NO odds, end time
- **Keybindings**:
  - `Enter` - Select market
  - `Ctrl+R` - Refresh markets
  - `Esc` - Go back

#### `football_trade_screen.py`
- Main trading interface
- **Layout**:
  - Top: FootballWidget
  - Middle: YES Orderbook | NO Orderbook | Debug Log
  - Bottom: CommandInput
- **Keybindings**:
  - `Ctrl+Y` - Quick buy YES
  - `Ctrl+N` - Quick buy NO
  - `Ctrl+B` - Get balance
  - `Ctrl+R` - Refresh orderbooks
  - `Ctrl+S` - Update score
  - `Ctrl+T` - Update time
  - `Esc` - Go back

#### `settings_screen.py`
- Configure application parameters
- **Sections**:
  - Trading Parameters (size, slippage, auto-sell)
  - Display Settings (refresh, theme, debug)
  - API Configuration (read-only)
- **Keybindings**:
  - `Ctrl+S` - Save settings
  - `Esc` - Cancel

---

### 4. Widgets (`ui/widgets/`)

#### `football_widget.py`
- Displays match state
- **Data**: score, time, phase, time remaining
- Auto-updates timer if `is_timer_running=True`
- Color-coded indicators

#### `orderbook.py`
- Displays orderbook (bids/asks)
- Updates via WebSocket events
- Methods:
  - `update_from_summary()`
  - `get_best_ask()`
  - `get_best_bid()`

#### `command_input.py`
- Command line interface
- Submits commands to CommandsManager
- Command history navigation

#### `main_header.py`
- Top application header
- Shows balance, connection status

---

### 5. Managers (`managers/`)

#### `commands_manager.py`
- **Purpose**: Async command dispatcher
- **Pattern**: Queue-based worker loop
- **Flow**:
  1. `submit(origin, command)` → returns Future
  2. Worker dequeues command
  3. Handler executes (Flask API call)
  4. Response set on Future
  5. Subscribers notified

**Handlers**:
- `buy` - Buy tokens via Flask API
- `sell` - Sell tokens via Flask API
- `balance` - Get balance via Flask API
- `score` - Update match score
- `time` - Update match time
- `ws` - WebSocket management

#### `requests_manager.py`
- Handles data requests (balance, wallet)
- Queue-based like CommandsManager

#### `navigation_manager.py`
- Screen navigation helpers
- Mixin for app class

#### `quickbuy_manager.py`
- Quick trading functionality
- Profile-based strategies
- Auto-sell management

---

### 6. Core Modules (`core/`)

#### `core.py`
- Aggregates all core modules
- Creates instances:
  - `websocket_manager`
  - `wallet`
  - `orders`
  - `fetch`

#### `websocket.py`
- **Purpose**: WebSocket connection manager
- **Features**:
  - Connects to Polymarket WebSocket
  - Manages multiple token subscriptions
  - OrderBook class for each token
  - Callbacks for events (orderbook, price_change, trade)

**Key Classes**:
```python
class OrderBook:
    token_id, asks, bids, best_ask, best_bid
    update_from_price_change()
    update_from_summary()
    update_from_last_trade()

class WebSocketCore:
    connect_market(token_ids, callbacks)
    disconnect_all()
    get_orderbook(token_id)
```

#### `wallet.py`
- Wallet operations
- Balance checking
- Transaction signing

#### `orders.py`
- Order creation
- Order management
- Order tracking

#### `fetch.py`
- Data fetching utilities
- Market data queries

---

### 7. Clients (`client/`)

#### `clob_client.py`
- Polymarket CLOB API client
- Methods:
  - `create_order()` - Place orders
  - `get_order_book()` - Fetch orderbook
  - `get_balance_allowance()` - Get balance
  - `cancel_order()` - Cancel orders

#### `gamma_client.py`
- Gamma API client (market data)
- Methods:
  - `get_markets()` - List markets
  - `get_market()` - Get market details
  - `search_market()` - Search by keyword

#### `webscoket_client.py`
- Low-level WebSocket client
- Uses `lomond` library
- Connects to:
  - Market data: `wss://ws-subscriptions-clob.polymarket.com/ws/market`
  - User data: `wss://ws-subscriptions-clob.polymarket.com/ws/user`

#### `WebSocketWrapper.py`
- Authenticated WebSocket wrapper
- Handles auth headers
- Auto-reconnection

---

### 8. Utilities (`utils/`)

#### `logger.py`
- Logging setup
- Creates loggers for:
  - Application logs (`logs/app.log`)
  - Command logs (`logs/commands.log`)

#### `market/`
- Market utility functions
- Price calculations
- Market data processing

---

## 🔄 Data Flow

### Trading Flow

```
User Input (Command)
      ↓
CommandInput Widget
      ↓
CommandsManager.submit()
      ↓
Queue → Worker → Handler
      ↓
httpx POST to Flask API
      ↓
Flask → ClobClient → Polymarket CLOB
      ↓
Response ← Flask API
      ↓
Future.set_result()
      ↓
Subscribers notified
      ↓
Debug Panel updated
```

### WebSocket Flow

```
Trading Screen on_mount()
      ↓
WebSocketCore.connect_market(token_ids)
      ↓
WebSocket subscription to Polymarket
      ↓
Events: orderbook_summary, price_change, trade
      ↓
Callbacks: _on_orderbook_update()
      ↓
OrderBookWidget.update_from_summary()
      ↓
UI updates in real-time
```

### Market Selection Flow

```
Home Screen on_mount()
      ↓
httpx GET /api/markets/football
      ↓
Flask → GammaClient → Polymarket Gamma API
      ↓
Markets displayed in ListView
      ↓
User presses Enter on market
      ↓
httpx GET /api/market/<slug>
      ↓
Token IDs stored in app.session
      ↓
Navigate to FootballTradeScreen
      ↓
WebSocket connects with token IDs
```

---

## 🎨 Styling (`ui/styles/theme.tcss`)

**Color Palette**:
```tcss
$surface: #0B1220
$panel: #0F1724
$primary: #2E6A9B
$accent: #9FB0C7
$text: #E6EEF6
$success: #3CB371
$warning: #D69E2E
$danger: #D64545
```

**Common Patterns**:
- Dock: `dock: top/bottom`
- Layout: `layout: vertical/horizontal`
- Borders: `border: solid $primary`
- Height: `height: 1fr` (fractional)

---

## 📝 Configuration

### Environment Variables (`config/.env`)

```env
CLOB_API_URL=https://clob.polymarket.com
CLOB_API_KEY=your_key
CLOB_SECRET=your_secret
CLOB_PASS_PHRASE=your_passphrase
CHAIN_ID=137
PRIVATE_KEY=your_private_key
```

### Settings (`app.session['settings']`)

```python
{
    "default_size": 10,
    "max_position": 1000,
    "slippage": 0.01,
    "auto_sell": False,
    "refresh_interval": 5,
    "theme": "dark",
    "show_debug": True
}
```

---

## 🚀 Extension Points

### Adding New Commands

1. Create handler in `commands_manager.py`:
```python
async def _handle_mycommand(self, req: CommandRequest) -> HandlerResult:
    # Implementation
    return ("Message", success_bool, navigation_string)
```

2. Register in `_register_defaults()`:
```python
self.register_handler("mycommand", self._handle_mycommand)
```

### Adding New Screens

1. Create in `ui/screens/my_screen.py`
2. Import and navigate:
```python
from fqs.ui.screens.my_screen import MyScreen
self.app.push_screen(MyScreen())
```

### Adding New API Endpoints

1. Add route in `server/api.py`:
```python
@api_bp.route('/my_endpoint', methods=['GET'])
def my_endpoint():
    # Implementation
    return jsonify({})
```

2. Call from TUI:
```python
response = await self.app.api_client.get("/api/my_endpoint")
```

---

## 📊 Key Files Summary

| File | Purpose | Dependencies |
|------|---------|-------------|
| `app.py` | Main entry point | textual, httpx |
| `server/api.py` | Flask API | flask, clob_client |
| `core/websocket.py` | WebSocket manager | webscoket_client |
| `managers/commands_manager.py` | Command dispatcher | httpx, asyncio |
| `ui/screens/football_trade_screen.py` | Trading UI | all widgets |
| `client/clob_client.py` | Polymarket client | web3, requests |

---

This structure enables clean separation between:
- **Frontend (Textual)**: UI and user interaction
- **Backend (Flask)**: Trading operations and API calls
- **Core**: Business logic and WebSocket management
- **Clients**: External API integration

All components communicate via well-defined interfaces (HTTP REST, WebSocket callbacks, async queues).
