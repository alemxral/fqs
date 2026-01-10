# FQS Setup Guide

Complete setup instructions for the Football Quick Shoot Trading Terminal.

---

## 📋 Prerequisites

- **Python**: 3.10 or higher
- **Operating System**: Linux, macOS, or Windows with WSL
- **Polymarket Account**: API credentials (key, secret, passphrase)
- **Terminal**: Support for TUI (Textual-based interface)

---

## 🚀 Installation

### Step 1: Navigate to FQS Directory

```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# On Windows (if using WSL):
# source venv/Scripts/activate
```

### Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create or edit the configuration file:

```bash
# Navigate to config directory
cd ../config

# Create .env file (if it doesn't exist)
touch .env

# Edit with your credentials
nano .env
```

Add the following (replace with your actual credentials):

```env
# Polymarket CLOB API
CLOB_API_URL=https://clob.polymarket.com
CLOB_API_KEY=your_api_key_here
CLOB_SECRET=your_secret_here
CLOB_PASS_PHRASE=your_passphrase_here

# Blockchain
CHAIN_ID=137

# Private Key (for wallet operations)
PRIVATE_KEY=your_private_key_here

# Gamma API (optional, for market data)
GAMMA_API_URL=https://gamma-api.polymarket.com
```

**⚠️ Security Warning**: Never commit `.env` files to version control!

### Step 5: Verify Installation

```bash
# Return to fqs directory
cd ../fqs

# Test imports
python -c "import textual; import flask; import httpx; print('✅ All dependencies installed')"
```

---

## 🎮 Running the Application

### Method 1: Automated Startup (Recommended)

```bash
# Make startup script executable (first time only)
chmod +x start.sh

# Run the application
./start.sh
```

This will automatically launch:
- **Terminal 1**: Flask backend server (port 5000)
- **Terminal 2**: Textual TUI interface

### Method 2: Manual Startup

**Terminal 1 - Flask Backend:**
```bash
cd server
python run_flask.py
```

Wait for:
```
🚀 FQS FLASK SERVER - Football Trading API
🔧 Server starting on http://127.0.0.1:5000
```

**Terminal 2 - Textual Frontend:**
```bash
# In a new terminal, activate venv first
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
source venv/bin/activate

# Run the TUI
python app.py
```

---

## 📚 How the Application Works

### Architecture Overview

```
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│  Textual TUI     │◄───────►│  Flask Backend   │◄───────►│  Polymarket      │
│  (Frontend)      │  HTTP   │  (Trading API)   │  REST   │  (CLOB + Gamma)  │
│                  │         │                  │         │                  │
│  + WebSocket     │◄────────┴──────────────────┴────────►│  WebSocket Feed  │
│    Core          │          Direct Connection           │  (Live Markets)  │
└──────────────────┘                                       └──────────────────┘
```

### Component Flow

#### 1. **Application Startup** (`app.py`)
- Initializes Textual App
- Creates CoreModule (WebSocket, Wallet, Orders)
- Initializes CommandsManager (command dispatcher)
- Sets up httpx client for Flask API communication
- Shows Welcome Screen

#### 2. **Flask Backend** (`server/`)
- **`run_flask.py`**: Entry point
- **`api.py`**: REST endpoints
  - Trading: `/api/order/buy`, `/api/order/sell`
  - Data: `/api/balance`, `/api/markets/football`, `/api/market/<slug>`
- Uses local `client/clob_client.py` for Polymarket CLOB API
- Uses local `client/gamma_client.py` for market data

#### 3. **Screen Navigation**

**Welcome Screen** → **Home Screen** → **Trading Screen**
                                    ↓
                             **Settings Screen**

#### 4. **Home Screen** (`ui/screens/home_screen.py`)
- Fetches football markets from Flask API
- Displays list of active matches
- User selects market → stores token IDs in session
- Navigates to Trading Screen

#### 5. **Trading Screen** (`ui/screens/football_trade_screen.py`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ ⚽ Match Info: Team A vs Team B | Score: 0-0 | Time: 0:00  │ ← Football Widget
├──────────────────────────┬──────────────────────┬──────────┤
│   YES Orderbook          │   NO Orderbook       │  Debug   │ ← Orderbooks + Log
│   Bids        Asks       │   Bids       Asks    │  Panel   │
│   0.64x100   0.66x50     │   0.34x80   0.36x40  │          │
├──────────────────────────┴──────────────────────┴──────────┤
│ > _                                                         │ ← Command Input
└─────────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. On mount: Connect WebSocket to Polymarket
2. Subscribe to YES/NO token IDs
3. WebSocket callbacks update OrderBookWidgets in real-time
4. Commands submitted to CommandsManager
5. CommandsManager sends HTTP requests to Flask API
6. Results displayed in Debug Panel

#### 6. **Settings Screen** (`ui/screens/settings_screen.py`)
- Configure trading parameters
- View/edit API credentials
- Adjust display settings
- Manage trading limits

#### 7. **WebSocket Integration** (`core/websocket.py`)
- Connects directly to Polymarket WebSocket
- Subscribes to token IDs for live orderbook data
- Callbacks update UI widgets
- Events: `orderbook_summary`, `price_change`, `last_trade`

#### 8. **Command System** (`managers/commands_manager.py`)

**Command Processing:**
1. User types command in CommandInput
2. Command submitted to async queue
3. Worker processes command
4. Handler executes (calls Flask API or local operation)
5. Response returned to Future
6. Subscribers notified (debug panel, logs)

**Available Commands:**
```bash
# Trading
buy YES 0.65 100      # Buy 100 YES @ 0.65
sell NO 0.35 50       # Sell 50 NO @ 0.35
balance               # Check USDC balance

# Match State (manual)
score 2-1             # Update score
time 67:30            # Update time

# WebSocket
ws status             # Check connection
ws sub <tokens>       # Subscribe
ws off                # Disconnect
```

---

## 🎯 Usage Workflow

### Basic Trading Flow

1. **Start Application**
   ```bash
   ./start.sh
   ```

2. **Welcome Screen**
   - Press `Enter` to continue

3. **Home Screen (Market Selection)**
   - Browse football markets
   - Use `↑/↓` arrows to navigate
   - Press `Enter` to select market
   - Press `Ctrl+R` to refresh markets

4. **Trading Screen**
   - WebSocket connects automatically
   - Orderbooks populate with live data
   - **Quick Trading:**
     - `Ctrl+Y` - Buy YES at best ask
     - `Ctrl+N` - Buy NO at best ask
   - **Manual Trading:**
     - Type: `buy YES 0.65 100`
     - Press `Enter`
   - **Check Balance:**
     - `Ctrl+B` or type `balance`
   - **Update Match State:**
     - Type: `score 2-1`
     - Type: `time 67:30`

5. **Settings** (from any screen)
   - Press `Ctrl+S`
   - Adjust parameters
   - Save changes

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Select / Execute |
| `Esc` | Go Back |
| `Ctrl+Y` | Quick Buy YES |
| `Ctrl+N` | Quick Buy NO |
| `Ctrl+B` | Get Balance |
| `Ctrl+R` | Refresh |
| `Ctrl+S` | Settings |
| `Ctrl+Q` | Quit |
| `F1` | Help |

---

## 🔧 Configuration

### Trading Parameters (Settings Screen)

```yaml
# Default trade size
default_size: 10

# Maximum position size
max_position: 1000

# Price slippage tolerance
slippage: 0.01

# Auto-refresh interval (seconds)
refresh_interval: 5
```

### Flask Server Configuration

Edit `server/run_flask.py` to change:
- Port (default: 5000)
- Host (default: 127.0.0.1)
- Debug mode (default: True)

---

## 🐛 Troubleshooting

### Issue: Flask server won't start

```bash
# Check if port 5000 is in use
lsof -i :5000

# Kill process if needed
kill -9 <PID>

# Or use different port
export FLASK_PORT=5001
python server/run_flask.py
```

### Issue: "ModuleNotFoundError"

```bash
# Ensure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "No markets found"

**Causes:**
- Flask server not running
- No internet connection
- Gamma API down

**Solutions:**
```bash
# Check Flask is running
curl http://127.0.0.1:5000/api/health

# Test Gamma API
python -c "from fqs.client.gamma_client import GammaAPIClient; c = GammaAPIClient(); print(c.get_markets(limit=1))"
```

### Issue: WebSocket connection failed

**Solutions:**
- Verify token IDs are correct
- Check internet connectivity
- Restart both Flask and TUI
- Check debug panel for specific errors

### Issue: API authentication errors

**Check:**
1. `.env` file exists in `config/` directory
2. Credentials are correct (no extra spaces)
3. API key has trading permissions
4. Wallet has sufficient USDC balance

---

## 📊 Data Persistence

### Session Data
- Market selections stored in `app.session`
- Active WebSocket subscriptions tracked
- Command history available (press `↑` in command input)

### Logs
- Application logs: `fqs/logs/app.log`
- Command logs: `fqs/logs/commands.log`
- Flask logs: `fqs/server/logs/flask.log`

---

## 🔒 Security Best Practices

1. **Never commit `.env` files**
   ```bash
   # Already in .gitignore
   config/.env
   ```

2. **Use separate API keys for trading**
   - Development: Read-only keys
   - Production: Full trading keys

3. **Set trading limits**
   - Configure max position sizes in Settings
   - Test with small amounts first

4. **Monitor logs**
   - Review command logs for unusual activity
   - Check Flask logs for API errors

---

## 🚦 Quick Start Checklist

- [ ] Python 3.10+ installed
- [ ] Virtual environment created
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with API credentials
- [ ] Flask server starts without errors
- [ ] Textual TUI launches successfully
- [ ] Can fetch football markets
- [ ] WebSocket connects to orderbooks
- [ ] Commands execute (test with `balance`)

---

## 📞 Support & Resources

- **README.md**: Full documentation
- **QUICKSTART.md**: Quick reference guide
- **API Docs**: See `server/api.py` for endpoint details
- **Code Structure**: See project directory tree in README.md

---

## 🎓 Learning Path

### Beginner
1. Start application
2. Browse markets
3. Select a market
4. Check balance
5. Place test trade (small size)

### Intermediate
1. Use quick buy shortcuts (Ctrl+Y/N)
2. Monitor orderbook changes
3. Update match state manually
4. Check debug panel logs

### Advanced
1. Customize settings
2. Understand WebSocket events
3. Create custom commands
4. Integrate live match data APIs

---

**Ready to Trade! ⚽💰**

For questions or issues, check the debug panel and logs first.
