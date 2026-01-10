# FQS Football Trading Terminal - Improvement Plan

## Executive Summary

This document outlines architectural improvements, feature enhancements, and development roadmap for the Football Quick Shoot (FQS) trading terminal. The plan focuses on improving code quality, expanding functionality, and optimizing the trading experience.

---

## 1. Architecture Improvements

### 1.1 WebSocket Integration - HIGH PRIORITY ⚠️

**Current State:**
- `fqs/core/websocket.py` contains stub implementation
- Removed `PolymarketWebsocketsClient` import due to Python 3.12 syntax incompatibility
- WebSocket connection methods exist but don't actually connect

**Required Changes:**
1. **Port WebSocket client from py_ws_client**
   - Copy `py_ws_client/` to `fqs/client/` 
   - Simplify type hints to Python 3.10 compatible syntax
   - Remove `PaginatedResponse[T]` generic, use `Dict[str, Any]`
   - Keep core functionality: connect, subscribe, orderbook parsing

2. **Implement WebSocketCore properly**
   ```python
   # fqs/core/websocket.py
   from fqs.client.py_ws_client import PolymarketWebsocketsClient
   
   class WebSocketCore:
       def __init__(self, api_creds: Dict, ...):
           self.client = PolymarketWebsocketsClient()
           self.orderbooks = {}
           # ... existing code
   ```

3. **Test live orderbook updates**
   - Subscribe to token IDs on football_trade_screen mount
   - Verify orderbook widgets update in real-time
   - Handle reconnection on network errors

**Impact:** Enables live price tracking, critical for trading terminal functionality

---

### 1.2 Configuration Management

**Current State:**
- `fqs/config/settings.py` has basic Settings class
- Uses python-dotenv for .env loading
- No validation of API credentials

**Improvements:**
1. **Add validation layer**
   ```python
   class Settings:
       def validate(self):
           # Check API key format (starts with specific prefix)
           # Validate CHAIN_ID (137 for Polygon mainnet)
           # Test API connectivity on startup
   ```

2. **Environment-specific configs**
   - `config/development.env` - testnet, verbose logging
   - `config/production.env` - mainnet, optimized settings
   - `config/staging.env` - hybrid testing environment

3. **Add runtime config updates**
   - Settings screen to modify DEFAULT_SIZE, MAX_POSITION
   - Save preferences to `~/.fqs/user_config.json`
   - Hot-reload settings without restart

**Impact:** Easier onboarding, safer credential management, flexible testing

---

### 1.3 Error Handling & Logging

**Current State:**
- Basic try-except blocks
- Logger configured but underutilized
- No structured error reporting

**Improvements:**
1. **Centralized error handler**
   ```python
   # fqs/utils/error_handler.py
   class ErrorHandler:
       @staticmethod
       def handle_api_error(e: Exception, context: str):
           # Log with full traceback
           # Show user-friendly message
           # Optionally retry with exponential backoff
   ```

2. **Structured logging**
   ```python
   # Use JSON logging for production
   logger.info("order_placed", extra={
       "market": market_slug,
       "side": "YES",
       "price": 0.55,
       "size": 10,
       "timestamp": datetime.utcnow().isoformat()
   })
   ```

3. **Error recovery strategies**
   - Network errors → auto-retry with backoff
   - API rate limits → queue requests
   - WebSocket disconnects → auto-reconnect
   - Invalid commands → show help with examples

**Impact:** Better debugging, improved user experience, production-ready reliability

---

## 2. Feature Enhancements

### 2.1 Advanced Football Analytics

**Goal:** Provide real-time football statistics to inform trading decisions

**Features:**
1. **Live match stats widget** (next to football_widget)
   - Possession %
   - Shots on target
   - Corners
   - Dangerous attacks
   - Yellow/red cards
   - xG (expected goals)

2. **Data sources:**
   - Primary: Scrape from live score APIs (free tier: API-Football, Football-Data.org)
   - Fallback: Manual input via commands (`stats possession 60`)
   - Cache: Store in `data/match_stats/<event_slug>.json`

3. **Integration with trading logic:**
   - High possession + low score → "Pressure building" indicator
   - Late game + close score → "High volatility" warning
   - Red card → "Market shift likely" alert

**Implementation:**
```python
# fqs/core/football_stats.py
class FootballStatsManager:
    def fetch_live_stats(self, match_id: str) -> Dict[str, Any]:
        # API call to Football-Data.org
        # Parse JSON response
        # Return structured stats
        
# fqs/ui/widgets/stats_widget.py
class StatsWidget(Static):
    def update_stats(self, stats: Dict):
        # Display possession bar
        # Show shot counter
        # Highlight key events
```

**Timeline:** 2-3 days development, 1 day testing

---

### 2.2 Order Management System

**Current State:**
- Basic buy/sell commands
- No order tracking
- No position management

**Enhancements:**
1. **Open orders tracking**
   ```
   Commands:
   - orders           → List all open orders
   - orders cancel <id>  → Cancel specific order
   - orders cancel all   → Cancel all orders
   ```

2. **Position summary**
   ```
   Positions:
   Market: Will Team X score next?
   YES: 100 shares @ avg 0.52 (current: 0.58, PnL: +6.00 USDC)
   NO:  50 shares @ avg 0.48 (current: 0.42, PnL: -3.00 USDC)
   Total PnL: +3.00 USDC
   ```

3. **Risk management**
   - Max position size per market (config setting)
   - Max total exposure across all markets
   - Alert when approaching limits
   - Auto-close positions at target profit/loss

**Implementation:**
```python
# fqs/managers/position_manager.py
class PositionManager:
    def __init__(self):
        self.positions = {}  # market_slug -> {YES: {...}, NO: {...}}
        
    def track_order(self, order: Dict):
        # Add to positions on fill
        
    def get_pnl(self, market_slug: str) -> float:
        # Calculate P&L from current prices
        
    def check_limits(self) -> bool:
        # Validate against MAX_POSITION
```

**Timeline:** 3-4 days development, 2 days testing

---

### 2.3 Multi-Market Dashboard

**Goal:** Trade multiple football markets simultaneously

**Features:**
1. **Market selector screen**
   - Show all active football markets
   - Filter by league, match time, liquidity
   - Quick subscribe to 3-5 markets

2. **Split-screen layout**
   ```
   ┌─────────────────────────────────────────┐
   │  Market 1: Team A vs B - YES: 0.55      │
   ├─────────────────────────────────────────┤
   │  Market 2: Team C vs D - NO: 0.42       │
   ├─────────────────────────────────────────┤
   │  Market 3: Team E vs F - YES: 0.68      │
   └─────────────────────────────────────────┘
   ```

3. **Hotkeys for switching**
   - `Ctrl+1-9` → Jump to market 1-9
   - `Ctrl+Tab` → Cycle through active markets
   - `Ctrl+W` → Close current market

**Implementation:**
```python
# fqs/ui/screens/multi_market_screen.py
class MultiMarketScreen(Screen):
    def __init__(self):
        self.markets = []  # List of MarketWidget
        
    def add_market(self, market_slug: str):
        widget = MarketWidget(market_slug)
        self.markets.append(widget)
```

**Timeline:** 4-5 days development, 2 days testing

---

### 2.4 Historical Data & Backtesting

**Goal:** Analyze past trades and test strategies

**Features:**
1. **Trade history export**
   - Save all trades to `data/trade_history.csv`
   - Columns: timestamp, market, side, price, size, pnl, strategy
   - Export to CSV for Excel analysis

2. **Strategy backtesting**
   - Define strategy rules (e.g., "Buy YES when possession > 60% and score tied")
   - Replay historical market data
   - Calculate hypothetical P&L

3. **Performance metrics**
   - Win rate
   - Average profit per trade
   - Max drawdown
   - Sharpe ratio

**Implementation:**
```python
# fqs/analysis/backtest.py
class Backtester:
    def __init__(self, strategy: Strategy, data: pd.DataFrame):
        self.strategy = strategy
        self.data = data
        
    def run(self) -> Dict[str, float]:
        # Simulate trades
        # Calculate metrics
        return {"win_rate": 0.65, "sharpe": 1.2, ...}
```

**Timeline:** 5-7 days development, 3 days testing

---

## 3. Code Quality Improvements

### 3.1 Type Hints & Documentation

**Current State:**
- Inconsistent type hints
- Missing docstrings in some modules
- No API documentation

**Improvements:**
1. **Add type hints to all functions**
   ```python
   from typing import Dict, List, Optional, Tuple
   
   async def fetch_orderbook(token_id: str) -> Dict[str, Any]:
       """
       Fetch orderbook from CLOB API.
       
       Args:
           token_id: Token ID to fetch orderbook for
           
       Returns:
           Dict containing bids, asks, and market info
           
       Raises:
           ValueError: If token_id is invalid
           NetworkError: If API request fails
       """
   ```

2. **Generate API docs with Sphinx**
   ```bash
   cd fqs/docs
   sphinx-quickstart
   sphinx-apidoc -o source/ ../
   make html
   ```

3. **Add inline documentation**
   - Explain complex algorithms (e.g., orderbook matching)
   - Document WebSocket message formats
   - Clarify trading logic flow

**Timeline:** 2-3 days

---

### 3.2 Testing Framework

**Current State:**
- No unit tests
- No integration tests
- Manual testing only

**Improvements:**
1. **Unit tests with pytest**
   ```python
   # tests/test_commands_manager.py
   def test_handle_buy_command():
       manager = CommandsManager(...)
       response = await manager._handle_buy("YES", "0.55", "10")
       assert response.success == True
       assert "order placed" in response.message.lower()
   ```

2. **Integration tests**
   ```python
   # tests/test_api_integration.py
   @pytest.mark.integration
   async def test_fetch_balance():
       client = PolymarketClobClient(...)
       balance = await client.get_balance()
       assert isinstance(balance, float)
       assert balance >= 0
   ```

3. **Mock external APIs**
   ```python
   from unittest.mock import Mock, patch
   
   @patch('fqs.client.clob_client.httpx.AsyncClient')
   async def test_buy_order(mock_client):
       mock_client.post.return_value.json.return_value = {"orderId": "123"}
       # Test order creation
   ```

4. **CI/CD pipeline**
   ```yaml
   # .github/workflows/test.yml
   name: Tests
   on: [push, pull_request]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v2
         - name: Install dependencies
           run: pip install -r requirements.txt -r requirements-dev.txt
         - name: Run tests
           run: pytest tests/ --cov=fqs --cov-report=html
   ```

**Timeline:** 5-7 days for comprehensive test coverage

---

### 3.3 Performance Optimization

**Current State:**
- Synchronous API calls in some places
- No caching layer
- Repeated data fetching

**Improvements:**
1. **Async everywhere**
   - Convert all API calls to async/await
   - Use `asyncio.gather()` for parallel requests
   - Non-blocking WebSocket handling

2. **Caching layer**
   ```python
   # fqs/utils/cache.py
   from functools import lru_cache
   import time
   
   class TTLCache:
       def __init__(self, ttl: int = 60):
           self.cache = {}
           self.ttl = ttl
           
       def get(self, key: str):
           if key in self.cache:
               value, timestamp = self.cache[key]
               if time.time() - timestamp < self.ttl:
                   return value
           return None
           
       def set(self, key: str, value):
           self.cache[key] = (value, time.time())
   
   # Usage
   market_cache = TTLCache(ttl=30)  # 30 second cache
   ```

3. **Database for historical data**
   - SQLite for local storage
   - Store: trade history, market data, orderbook snapshots
   - Query for analytics without API calls

**Timeline:** 3-4 days

---

## 4. User Experience Enhancements

### 4.1 Improved Terminal UI

**Current State:**
- Basic Textual layout
- Limited visual feedback
- No customization

**Improvements:**
1. **Theme system**
   - Dark mode (default)
   - Light mode
   - Custom color schemes (football team colors)
   - Save theme preference

2. **Visual indicators**
   - Price changes: ↑ green, ↓ red
   - Flash on trade execution
   - Progress bars for time remaining
   - Sparklines for price history

3. **Keyboard shortcuts help**
   - Press `?` to show help overlay
   - List all commands and bindings
   - Interactive tutorial mode

**Implementation:**
```python
# fqs/ui/themes.py
DARK_THEME = {
    "primary": "#00D4FF",
    "secondary": "#FF6B6B",
    "background": "#1E1E1E",
    "text": "#FFFFFF",
}

LIGHT_THEME = {
    "primary": "#0066CC",
    "secondary": "#CC0000",
    "background": "#FFFFFF",
    "text": "#000000",
}
```

**Timeline:** 2-3 days

---

### 4.2 Smart Command Autocomplete

**Current State:**
- Manual command typing
- No suggestions
- Easy to make typos

**Improvements:**
1. **Autocomplete in CommandInput**
   - Tab to complete command names
   - Show available options (e.g., `buy <TAB>` → YES, NO)
   - Fuzzy matching (e.g., `bal` → `balance`)

2. **Command history**
   - Up/Down arrows to navigate history
   - Store in `~/.fqs/command_history.txt`
   - Search history with `Ctrl+R`

3. **Contextual help**
   - Show command syntax while typing
   - Example: `buy ` → "Usage: buy <YES|NO> <price> <size>"

**Implementation:**
```python
# fqs/ui/widgets/command_input.py
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

completer = WordCompleter([
    'buy', 'sell', 'balance', 'see', 'score', 'time', 'ws', 'help'
])

session = PromptSession(completer=completer)
```

**Timeline:** 2-3 days

---

### 4.3 Mobile Companion App (Stretch Goal)

**Goal:** Monitor trades on mobile device

**Features:**
1. **Flask REST API** (already exists)
   - Expose endpoints: `/api/positions`, `/api/orders`, `/api/balance`
   - Add authentication (JWT tokens)
   - WebSocket endpoint for live updates

2. **React Native mobile app**
   - Login with API key
   - View positions & P&L
   - Receive push notifications on trade fills
   - Quick close positions

3. **Deployment:**
   - Deploy Flask API to cloud (Railway, Render, Fly.io)
   - App connects to public API
   - End-to-end encryption for sensitive data

**Timeline:** 2-3 weeks (outside core terminal development)

---

## 5. Deployment & Distribution

### 5.1 Packaging

**Current State:**
- Manual setup with virtualenv
- start.sh script for local use
- No installable package

**Improvements:**
1. **PyPI package**
   ```bash
   pip install fqs-terminal
   fqs --help
   fqs run
   ```

2. **Docker container**
   ```dockerfile
   FROM python:3.10-slim
   WORKDIR /app
   COPY . .
   RUN pip install -r requirements.txt
   CMD ["python", "-m", "fqs.app"]
   ```

3. **Standalone executable** (PyInstaller)
   ```bash
   pyinstaller --onefile fqs/app.py
   ./dist/fqs
   ```

**Timeline:** 2-3 days

---

### 5.2 Documentation

**Current State:**
- SETUP.md with basic instructions
- No user manual
- No troubleshooting guide

**Improvements:**
1. **User manual**
   - Getting started tutorial
   - Command reference
   - Trading strategies guide
   - FAQ

2. **Developer docs**
   - Architecture overview
   - API documentation
   - Contributing guidelines
   - Code style guide

3. **Video tutorials**
   - YouTube: "FQS Setup in 5 Minutes"
   - Demo: "Placing Your First Trade"
   - Advanced: "Multi-Market Trading Strategy"

**Timeline:** 3-4 days

---

## 6. Development Roadmap

### Phase 1: Core Stability (Week 1-2)
- ✅ Fix WebSocket integration
- ✅ Add comprehensive error handling
- ✅ Implement unit tests (>70% coverage)
- ✅ Optimize performance (async, caching)

### Phase 2: Essential Features (Week 3-4)
- ✅ Order management system
- ✅ Position tracking & P&L
- ✅ Live football stats widget
- ✅ Multi-market dashboard

### Phase 3: User Experience (Week 5-6)
- ✅ Theme system & visual polish
- ✅ Command autocomplete
- ✅ Improved keyboard shortcuts
- ✅ Help system & tutorial

### Phase 4: Advanced Analytics (Week 7-8)
- ✅ Historical data export
- ✅ Strategy backtesting
- ✅ Performance metrics
- ✅ Trade journal

### Phase 5: Deployment (Week 9-10)
- ✅ PyPI package
- ✅ Docker container
- ✅ Documentation site
- ✅ Public release

---

## 7. Metrics for Success

### Technical Metrics
- **Test Coverage:** >80%
- **Response Time:** <100ms for local commands, <500ms for API calls
- **Uptime:** >99% WebSocket connection stability
- **Error Rate:** <1% failed orders

### User Metrics
- **Time to First Trade:** <5 minutes from installation
- **Daily Active Users:** 50+ within first month
- **User Retention:** >70% week-over-week
- **Average P&L:** Positive for >60% of users

### Business Metrics
- **GitHub Stars:** 100+ within 3 months
- **Community:** Discord server with 200+ members
- **Contributors:** 5+ active contributors
- **Adoption:** Used in 10+ trading strategies

---

## 8. Risk Mitigation

### Technical Risks
1. **WebSocket instability**
   - Mitigation: Implement robust reconnection logic, fallback to polling
   
2. **API rate limits**
   - Mitigation: Implement request queuing, caching, backoff strategies
   
3. **Breaking changes in py-clob-client**
   - Mitigation: Pin specific versions, vendor critical code

### Business Risks
1. **Low user adoption**
   - Mitigation: Active marketing, partnerships with trading communities
   
2. **Competition from other terminals**
   - Mitigation: Focus on football-specific features, superior UX
   
3. **Regulatory concerns**
   - Mitigation: Clear disclaimer (not financial advice), no custody of funds

---

## 9. Conclusion

This improvement plan provides a comprehensive roadmap for transforming FQS from a basic trading terminal into a production-ready, feature-rich platform for football market trading on Polymarket. 

**Key Priorities:**
1. **Short-term (1-2 weeks):** Fix WebSocket, add error handling, implement tests
2. **Medium-term (1-2 months):** Build out order management, multi-market support, analytics
3. **Long-term (3-6 months):** Package for distribution, build community, iterate on feedback

**Next Steps:**
1. Review this plan with stakeholders
2. Prioritize features based on user feedback
3. Set up project board (GitHub Projects or Trello)
4. Begin Phase 1 implementation

---

**Last Updated:** January 2025
**Version:** 1.0
**Author:** FQS Development Team
