# FQS - Football Quick Shoot Trading Terminal

A specialized Textual-based TUI (Terminal User Interface) for fast trading on Polymarket football events, built with Flask backend and WebSocket integration.

## Architecture

```
┌─────────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│   Textual TUI       │◄───────►│  Flask Backend   │◄───────►│  Polymarket API  │
│   (fqs/app.py)      │  HTTP   │  (fqs/server/)   │  REST   │  (CLOB + Gamma)  │
│                     │         │                  │         │                  │
│   + WebSocket Core  │◄────────┼──────────────────┼────────►│  WebSocket Feed  │
│   (fqs/core/)       │  WS     │                  │  WS     │  (Live Markets)  │
└─────────────────────┘         └──────────────────┘         └──────────────────┘
```

## Features

### 🏟️ **Football Market Selection**
- Browse active football markets from Polymarket
- Filter and search for specific matches
- View live odds (YES/NO prices)
- One-click navigation to trading screen

### 📊 **Live Trading Interface**
- **Dual Orderbook Display**: Side-by-side YES/NO token orderbooks
- **Real-time WebSocket Updates**: Live price and trade data
- **Football Match Widget**: Display score, time, and match phase
- **Debug Panel**: Real-time command output and logs

### ⚡ **Fast Trading Commands**
- **Keyboard Shortcuts**:
  - `Ctrl+Y` - Quick buy YES token at best ask
  - `Ctrl+N` - Quick buy NO token at best ask
  - `Ctrl+B` - Get wallet balance
  - `Ctrl+R` - Refresh orderbooks
  - `Ctrl+S` - Update match score
  - `Ctrl+T` - Update match time

- **Command Line Interface**:
  ```bash
  buy YES 0.65 100    # Buy 100 YES tokens at 0.65
  sell NO 0.35 50     # Sell 50 NO tokens at 0.35
  balance             # Check USDC balance
  score 2-1           # Update score manually
  time 67:30          # Update match time
  see slug <event>    # Fetch event/market data
  ws <slug>           # Subscribe to WebSocket updates
  ```

### 📊 **Football Widget Mode** (Standalone)
Run a minimal TUI to track a single football match:
```bash
python run_football_widget.py epl-tot-ast-2025-10-19
```

Features:
- Live match score and time tracker
- Auto-incrementing timer
- Market price display (YES/NO tokens)
- Keyboard controls:
  - `P` - Play/Pause timer
  - `S` - Increment score
  - `T` - Add 5 minutes to time
  - `R` - Refresh market data
  - `Q` - Quit

## Setup

### 1. Prerequisites

- **Python 3.6+** (all versions supported)
  - Python 3.10+: Full WebSocket support (FULL mode)
  - Python 3.6-3.9: WebSocket compatibility layer (COMPAT mode)
  - See [WEBSOCKET_COMPAT.md](WEBSOCKET_COMPAT.md) for details
- Virtual environment (recommended)
- Polymarket API credentials (in `config/.env`)

**WebSocket Compatibility:**
- **Python 3.10+**: Native WebSocket client with `match/case` syntax
- **Python 3.6-3.9**: Compatibility layer automatically converts syntax
- No breaking changes - existing code works on all versions

### 2. Installation

```bash
# Navigate to fqs directory
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs

# Install dependencies (if not already installed)
pip install -r ../requirements.txt

# Additional dependencies
pip install flask flask-cors httpx
```

### 3. Configuration

Ensure `config/.env` exists with your Polymarket credentials:

```env
CLOB_API_URL=https://clob.polymarket.com
CLOB_API_KEY=your_api_key
CLOB_SECRET=your_secret
CLOB_PASS_PHRASE=your_passphrase
CHAIN_ID=137
```

## Running the Application

### Two-Terminal Setup (Recommended for Development)

**Terminal 1 - Start Flask Backend:**
```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs/server
python run_flask.py
```

You should see:
```
🚀 FQS FLASK SERVER - Football Trading API
📊 Endpoints:
   POST /api/order/buy         - Place buy order
   POST /api/order/sell        - Place sell order
   GET  /api/balance           - Get wallet balance
   GET  /api/markets/football  - Get active football markets
   GET  /api/market/<slug>     - Get market details and token IDs

🔧 Server starting on http://127.0.0.1:5000
```

**Terminal 2 - Start Textual TUI:**
```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
python app.py
```

### Usage Flow

1. **Launch TUI** → Welcome screen appears
2. **Press Enter** → Navigate to Football Markets (Home Screen)
3. **Browse Markets** → Use arrow keys to select a match
4. **Press Enter** → Enter trading screen for selected match
5. **WebSocket Connects** → Live orderbook updates begin
6. **Trade**:
   - Use commands: `buy YES 0.65 100`
   - Or shortcuts: `Ctrl+Y` for quick buy
7. **Monitor**:
   - Watch orderbook updates in real-time
   - Check debug panel for command results
   - Update match state: `score 2-1`, `time 67:30`

## Project Structure

```
fqs/
├── app.py                      # Main Textual application
├── server/                     # Flask backend
│   ├── run_flask.py           # Flask entry point
│   ├── __init__.py            # App factory
│   └── api.py                 # REST API endpoints
├── ui/
│   ├── screens/
│   │   ├── home_screen.py     # Football market selector
│   │   ├── football_trade_screen.py  # Trading interface
│   │   └── welcome_screen.py  # Welcome splash
│   ├── widgets/
│   │   ├── football_widget.py # Match state display
│   │   ├── orderbook.py       # Orderbook widget
│   │   └── command_input.py   # Command line
│   └── styles/
│       └── theme.tcss         # CSS styling
├── managers/
│   ├── commands_manager.py    # Command dispatcher (Flask API integration)
│   ├── requests_manager.py    # Request handling
│   └── navigation_manager.py  # Screen navigation
├── core/
│   ├── core.py                # Core module aggregator
│   ├── websocket.py           # WebSocket manager
│   ├── wallet.py              # Wallet operations
│   └── orders.py              # Order management
└── client/                     # Polymarket clients
    ├── clob_client.py         # CLOB API client
    ├── gamma_client.py        # Gamma API client
    └── webscoket_client.py    # WebSocket client
```

## API Endpoints

### Trading Endpoints

**POST /api/order/buy**
```json
{
  "token_id": "string",
  "price": 0.65,
  "size": 100
}
```

**POST /api/order/sell**
```json
{
  "token_id": "string",
  "price": 0.35,
  "size": 50
}
```

**GET /api/balance**
```json
{
  "success": true,
  "balance": 1234.56,
  "currency": "USDC"
}
```

### Market Data Endpoints

**GET /api/markets/football**
```json
{
  "success": true,
  "markets": [
    {
      "slug": "epl-match-2025",
      "question": "Will Team A win?",
      "yes_price": 0.65,
      "no_price": 0.35,
      "end_date": "2025-01-15T20:00:00Z"
    }
  ]
}
```

**GET /api/market/<slug>**
```json
{
  "success": true,
  "market": {
    "slug": "epl-match-2025",
    "question": "Will Team A win?",
    "tokens": {
      "yes": "token_id_yes",
      "no": "token_id_no"
    },
    "prices": {
      "yes": 0.65,
      "no": 0.35
    }
  }
}
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Select market / Execute |
| `Escape` | Go back |
| `Ctrl+Y` | Quick buy YES token |
| `Ctrl+N` | Quick buy NO token |
| `Ctrl+B` | Get balance |
| `Ctrl+R` | Refresh orderbooks |
| `Ctrl+S` | Update score |
| `Ctrl+T` | Update time |
| `Ctrl+Q` | Quit application |
| `F1` | Show help |

## Commands

### Trading Commands
```bash
buy YES <price> <size>      # Buy YES tokens
buy NO <price> <size>       # Buy NO tokens
sell YES <price> <size>     # Sell YES tokens
sell NO <price> <size>      # Sell NO tokens
balance                     # Check USDC balance
```

### Match State Commands
```bash
score <home>-<away>         # Update match score (e.g., score 2-1)
time <mm:ss>                # Update match time (e.g., time 67:30)
```

### WebSocket Commands
```bash
ws status                   # Check WebSocket connection
ws sub <token_ids>          # Subscribe to tokens
ws off                      # Disconnect WebSocket
```

## Development Roadmap

### Phase 1: Core Trading (✅ Complete)
- [x] Flask backend with trading endpoints
- [x] Home screen for market selection
- [x] Trading screen with orderbooks
- [x] WebSocket integration for live data
- [x] Command handlers for buy/sell
- [x] Quick trading keyboard shortcuts

### Phase 2: Live Match Data (Next)
- [ ] API-Football integration for live scores
- [ ] Auto-update match time and score
- [ ] Match event notifications (goals, cards)
- [ ] Timer synchronization

### Phase 3: Probability Models
- [ ] Train ML model on historical data
- [ ] Live probability calculations
- [ ] Strategy-based trading suggestions
- [ ] Auto-sell based on probability changes

### Phase 4: Advanced Features
- [ ] Multi-market monitoring
- [ ] Portfolio tracking
- [ ] Profit/loss calculations
- [ ] Trading history and analytics

## Troubleshooting

### Flask Server Won't Start
```bash
# Check if port 5000 is available
lsof -i :5000

# Use different port
export FLASK_PORT=5001
python run_flask.py
```

### WebSocket Connection Failed
- Ensure internet connection is active
- Check Polymarket WebSocket URL is reachable
- Verify token IDs are valid

### Import Errors
```bash
# Ensure you're in the right directory
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs

# Check Python path
python -c "import sys; print(sys.path)"
```

### API Authentication Errors
- Verify `.env` file exists in `config/`
- Check API credentials are correct
- Ensure API key has trading permissions

## Contributing

This is a specialized football trading terminal. Future enhancements welcome:
- Better market filtering
- Advanced order types (stop-loss, take-profit)
- Multi-account support
- Real-time P&L tracking

## License

Part of the Polytrading project.
