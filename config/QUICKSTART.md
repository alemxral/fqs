# FQS - Quick Start Guide

## 🚀 Launch

### Option 1: Automated Scripts (Recommended)

**Terminal 1 - Backend:**
```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
./start_backend.sh
```

**Terminal 2 - Frontend:**
```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
./start_frontend.sh
```

### Option 2: Manual Startup
**Terminal 1 - Backend:**
```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
python server/run_flask.py
```

**Terminal 2 - Frontend:**
```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
python app.py
```

---

## 📋 Workflow

### 1️⃣ Welcome Screen
- Press **Enter** to continue to market selection

### 2️⃣ Home Screen (Football Markets)
- Browse active football markets
- Use **↑/↓** arrow keys to navigate
- Press **Enter** to select a match for trading
- Press **Ctrl+R** to refresh market list
- Press **Esc** to go back

### 3️⃣ Trading Screen

#### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ ⚽ Match: Team A vs Team B | Score: 2-1 | Time: 67:30      │  ← Football Widget
├──────────────────────────┬──────────────────────┬──────────┤
│   YES Token Orderbook    │  NO Token Orderbook  │  Debug   │  ← Orderbooks + Log
│   📈 Bids    | Asks      │  📉 Bids   | Asks   │  Panel   │
│   0.64 x 100 | 0.66 x 50 │  0.34 x 80 | 0.36.. │          │
│   ...                    │  ...                 │  > buy..  │
├──────────────────────────┴──────────────────────┴──────────┤
│ > buy YES 0.65 100                                          │  ← Command Input
└─────────────────────────────────────────────────────────────┘
```

#### Quick Trading
- **Ctrl+Y** - Quick buy YES at best ask price
- **Ctrl+N** - Quick buy NO at best ask price
- **Ctrl+B** - Check wallet balance
- **Ctrl+R** - Refresh orderbooks

#### Manual Trading Commands
```bash
buy YES 0.65 100     # Buy 100 YES tokens at 0.65
buy NO 0.35 50       # Buy 50 NO tokens at 0.35
sell YES 0.70 100    # Sell 100 YES tokens at 0.70
sell NO 0.40 50      # Sell 50 NO tokens at 0.40
balance              # Check USDC balance
```

#### Match State Updates (Manual)
```bash
score 2-1            # Update score to 2-1
time 67:30           # Update time to 67:30
```

#### Navigation
- **Esc** - Return to home screen
- **Ctrl+Q** - Quit application

---

## 🎯 Trading Examples

### Example 1: Quick Buy YES
1. Navigate to trading screen for desired match
2. Check YES orderbook - best ask is **0.65**
3. Press **Ctrl+Y** to instantly buy at 0.65
4. Confirmation appears in debug panel

### Example 2: Custom Buy Order
1. Type in command input: `buy YES 0.64 200`
2. Press **Enter**
3. Order submitted for 200 shares at 0.64
4. Result shown in debug panel

### Example 3: Check Balance Before Trading
1. Press **Ctrl+B** to see balance
2. Debug panel shows: `Balance: $1,234.56 USDC`
3. Calculate position size
4. Execute trade

### Example 4: Update Match State
1. Match enters 67th minute
2. Type: `time 67:00`
3. Football widget updates to show 67:00
4. Type: `score 2-1` if goal scored
5. Widget reflects new score

---

## 🔍 Monitoring

### Debug Panel
The debug panel (right side) shows:
- ✓ Command execution results
- ✗ Error messages
- 📊 WebSocket connection status
- 🔄 Orderbook updates
- 📈 Trade executions

### Orderbook Display
- **Green** = Bids (buy orders)
- **Red** = Asks (sell orders)
- **Best Bid/Ask** = Top of each side
- Updates in real-time via WebSocket

---

## ⚙️ Configuration

### Environment Variables
Edit `config/.env`:
```env
CLOB_API_URL=https://clob.polymarket.com
CLOB_API_KEY=your_key
CLOB_SECRET=your_secret
CLOB_PASS_PHRASE=your_passphrase
CHAIN_ID=137
```

### Flask Server Port
Default: `http://127.0.0.1:5000`

To change:
```bash
export FLASK_PORT=5001
python server/run_flask.py
```

---

## 🐛 Troubleshooting

### Problem: "No markets found"
**Solution:** 
- Check Flask server is running
- Verify internet connection
- Refresh with **Ctrl+R**

### Problem: "WebSocket connection failed"
**Solution:**
- Check token IDs are valid
- Verify WebSocket URL in client config
- Try reconnecting with **Ctrl+R**

### Problem: "Order failed"
**Solution:**
- Check balance with **Ctrl+B**
- Verify price is within valid range (0.01-0.99)
- Ensure sufficient USDC balance

### Problem: Import errors
**Solution:**
```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
python -c "import fqs.core.core"
# If error, check sys.path
```

---

## 📊 Next Steps

1. **Test Basic Flow:**
   - Launch app → Select market → View orderbooks → Check balance

2. **Practice Commands:**
   - Try each command in the trading screen
   - Monitor debug panel for results

3. **Explore Features:**
   - Quick buy shortcuts (Ctrl+Y/N)
   - Manual score/time updates
   - WebSocket live updates

4. **Advanced Usage:**
   - Multiple market monitoring
   - Custom trading strategies
   - Probability calculations (coming soon)

---

## 📞 Support

Check the main README.md for:
- Full API documentation
- Architecture details
- Development roadmap
- Contributing guidelines

**Happy Trading! ⚽💰**
