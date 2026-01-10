"""
README: Testing and Running FQS with New Widgets
================================================

This document explains how to test and see the new trading widgets.

## ✅ What's Been Added

1. **Four New Widgets** (all integrated into FootballTradeScreen):
   - PriceTickerWidget - Live token prices
   - OpenOrdersWidget - Active orders with cancel button
   - TradeHistoryWidget - Scrolling trade log
   - PositionSummaryWidget - Portfolio P&L

2. **Commands Extended**:
   - markets - Search/list markets
   - orders - View/cancel orders
   - positions - Show positions
   - trades - Trade history

3. **Backend Integration**:
   - OrdersCore uses utils/trading/* functions
   - WalletCore uses utils/account/* functions
   - All commands registered and working

## 🧪 Running Tests

### Backend Tests
```bash
cd /home/amoral-a/sgoinfre/polytrading/poly
python3 fqs/tests/test_backend.py
```

Expected: 43/44 tests pass
- Tests OrdersCore, WalletCore, CommandsManager
- Verifies all command handlers
- Checks utils integration

### Layout Inspection
```bash
python3 fqs/tests/inspect_layout.py
```

Expected: All ✅ checkmarks
- Confirms widgets are in FootballTradeScreen
- Shows compose() structure
- Verifies CSS and IDs

## 🚀 Seeing the UI Changes

### IMPORTANT: You MUST restart the FQS app to see changes!

1. **Use the restart script (recommended)**:
   ```bash
   cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
   ./restart.sh   # Kills all old processes
   ./start.sh     # Starts fresh with backend + frontend
   ```

2. **Or manually restart**:
   ```bash
   # Press Ctrl+Q in the FQS terminal
   # Or kill processes manually
   pkill -f "python.*fqs"
   pkill -f "python.*app.py"
   pkill -f "python.*run_flask.py"
   
   # Then start fresh
   cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
   ./start.sh
   ```

3. **Navigate to FootballTradeScreen**:
   - From WelcomeScreen → HomeScreen
   - Select a football market
   - This should open FootballTradeScreen

4. **What you should see**:
   ```
   ┌────────────────────────────────────────────────────┐
   │ ⚽ Football Trading Terminal   Balance: 1000.00    │
   ├──────────┬────────────────────┬────────────────────┤
   │ Events   │  Match Widget      │ Command Output     │
   │ List     │  +                 │ ┌──────────────┐  │
   │          │  Orderbooks        │ │Price Ticker  │  │
   │          │  (YES / NO)        │ ├──────────────┤  │
   │          │                    │ │Open Orders   │  │
   │          │                    │ ├──────────────┤  │
   │          │                    │ │Positions     │  │
   │          │                    │ ├──────────────┤  │
   │          │                    │ │Trade History │  │
   │          │                    │ └──────────────┘  │
   │          │                    │ Command Log...    │
   └──────────┴────────────────────┴────────────────────┘
   ```

## 📍 Widget Locations

The 4 new widgets are in the **right panel** (#output_panel):

- **Top 40%**: Trading widgets container (#trading_widgets)
  - PriceTickerWidget (#price_ticker)
  - OpenOrdersWidget (#open_orders)
  - PositionSummaryWidget (#position_summary)
  - TradeHistoryWidget (#trade_history)

- **Bottom 60%**: Command output log (#command_output)

## 🐛 Troubleshooting

### "I don't see the widgets!"

1. **Did you restart the app?**
   - Python caches imported modules
   - Changes won't appear until full restart

2. **Are you on FootballTradeScreen?**
   - Widgets only appear on this specific screen
   - Navigate: Welcome → Home → Select Football Market

3. **Check terminal size**:
   - Widgets might be too small to see
   - Resize terminal to at least 120x40

### "Widgets show but are empty!"

This is normal if:
- No market is selected (no token_id set)
- No active orders exist
- WebSocket not connected yet
- Still initializing (wait 2-3 seconds)

### "Commands don't work!"

1. **Check backend is running**:
   ```bash
   curl http://localhost:5000/health
   ```

2. **Test commands in terminal**:
   ```bash
   cd /home/amoral-a/sgoinfre/polytrading/poly
   ./fqs/cmd/execute_command.py orders
   ```

## 🔧 Manual Verification

If you still don't see changes, manually verify:

```bash
# 1. Check file was updated
grep -n "PriceTickerWidget" /home/amoral-a/sgoinfre/polytrading/poly/fqs/ui/screens/football_trade_screen.py

# 2. Check imports work
cd /home/amoral-a/sgoinfre/polytrading/poly
python3 -c "from fqs.ui.widgets import PriceTickerWidget, OpenOrdersWidget; print('✅ Widgets import successfully')"

# 3. Check screen imports
python3 -c "from fqs.ui.screens.football_trade_screen import FootballTradeScreen; print('✅ Screen imports successfully')"
```

## 📊 Testing Individual Widgets

To test widgets in isolation:

```python
from textual.app import App
from fqs.ui.widgets.price_ticker import PriceTickerWidget

class TestApp(App):
    def compose(self):
        yield PriceTickerWidget()

if __name__ == "__main__":
    TestApp().run()
```

## 🎯 Next Steps

After verifying the UI:

1. **Connect WebSocket** - Select a market to get live updates
2. **Test Commands** - Try: `markets`, `orders`, `positions`, `trades`
3. **Place Orders** - Use `buy` / `sell` commands
4. **Watch Widgets Update** - Should refresh automatically

## 📝 File Changes Summary

Modified files:
- `fqs/core/orders.py` - Refactored to use utils
- `fqs/ui/screens/football_trade_screen.py` - Added 4 widgets
- `fqs/managers/commands_manager.py` - Added new handlers
- `fqs/server/command_routes.py` - NEW command API
- `fqs/cmd/execute_command.py` - NEW CLI wrapper

New widget files:
- `fqs/ui/widgets/open_orders.py`
- `fqs/ui/widgets/price_ticker.py`
- `fqs/ui/widgets/trade_history.py`
- `fqs/ui/widgets/position_summary.py`

Test files:
- `fqs/tests/test_backend.py` - Backend tests
- `fqs/tests/test_ui.py` - UI tests
- `fqs/tests/inspect_layout.py` - Layout inspector
