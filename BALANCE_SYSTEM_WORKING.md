# ✅ Balance System - Working Implementation

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BALANCE DATA FLOW                         │
└─────────────────────────────────────────────────────────────┘

1. CLIENT REQUEST
   ↓
   UI (HomeScreen) → HTTP GET http://127.0.0.1:5000/api/balance
   
2. SERVER RESPONSE (IMMEDIATE - <1s)
   ↓
   Flask /api/balance endpoint:
   ├─ Read cached data/balance.json
   ├─ Return cached data immediately
   └─ Start background thread (daemon)
   
3. BACKGROUND UPDATE (async, non-blocking)
   ↓
   Background Thread:
   ├─ Call get_balance_derived_address("USDC") → Derived wallet balance
   ├─ Call check_blockchain_balance(verbose=False) → Proxy wallet balance  
   ├─ Total = derived + proxy
   └─ Save to data/balance.json
```

## Files Modified

### 1. server/api.py (Balance Endpoint)
**Location**: `/api/balance`
**Method**: GET

**Implementation**:
```python
def get_balance():
    # Immediately serve cached data
    if balance_file.exists():
        return jsonify({cached: true, updating: true, ...})
    
    # Background thread updates blockchain data
    threading.Thread(target=update_balance_background, daemon=True).start()
```

**Response Format**:
```json
{
  "success": true,
  "balance": 373.852118,
  "derived_balance": 24.0,
  "proxy_balance": 349.852118,
  "proxy_allowance": 1.15e+71,
  "currency": "USDC",
  "timestamp": "2026-01-11T17:07:56.851736",
  "source": "blockchain",
  "cached": true,
  "updating": true
}
```

### 2. data/balance.json (Cache File)
**Purpose**: Persistent cache for balance data
**Location**: `data/balance.json`
**Updated by**: Background thread in Flask server
**Read by**: Flask /api/balance endpoint
**Frequency**: Updates on each /api/balance request (async)

### 3. ui/screens/home_screen.py (UI Client)
**Method**: `update_balance()`
**Trigger**: On app startup, manual refresh
**Implementation**:
```python
async def update_balance(self):
    response = await self.app.api_client.get("/api/balance")
    data = response.json()
    
    # Extract balances
    derived_balance = data.get("derived_balance", 0)
    proxy_balance = data.get("proxy_balance", 0)
    total_balance = data.get("balance", 0)
    
    # Update header display
    header.update_balance(
        f"${total_balance:.2f} USDC "
        f"(D: ${derived_balance:.2f} | P: ${proxy_balance:.2f})"
    )
```

## Blockchain Utilities Used

### 1. Derived Wallet Balance
**Function**: `get_balance_derived_address(token_type)`
**Location**: `utils/account/derived-wallet/get_balance_derived_address_blockchain.py`
**Purpose**: Get USDC balance for derived wallet (from PRIVATE_KEY)
**Usage**: 
```python
derived_balance = get_balance_derived_address("USDC")
```

### 2. Proxy Wallet Balance
**Function**: `check_blockchain_balance(address, rpc_url, verbose)`
**Location**: `utils/account/proxy-wallet/get_balance_proxy_address_blockchain.py`
**Purpose**: Get USDC balance and allowance for proxy wallet (FUNDER/PROXY_ADDRESS)
**Usage**:
```python
proxy_balance, proxy_allowance = check_blockchain_balance(verbose=False)
```

## Performance Characteristics

### ✅ FAST - Cached Response
- **Endpoint response time**: < 1 second
- **Data source**: JSON file cache
- **User experience**: Instant balance display
- **Freshness**: Last blockchain update timestamp included

### 🔄 ACCURATE - Background Update
- **Blockchain RPC calls**: 30-60 seconds (asynchronous)
- **Update frequency**: On each /api/balance request
- **Non-blocking**: Server responds immediately while updating
- **Cache invalidation**: Automatic on successful update

## Testing

### 1. Test Balance Endpoint
```bash
curl -s http://127.0.0.1:5000/api/balance | python -m json.tool
```

**Expected Output**:
```json
{
    "balance": 373.85,
    "cached": true,
    "updating": true,
    "derived_balance": 24.0,
    "proxy_balance": 349.85
}
```

### 2. Verify JSON Cache
```bash
cat data/balance.json | python -m json.tool
```

### 3. Monitor Background Updates
```bash
tail -f logs/flask.log | grep -E "balance|blockchain|Background"
```

### 4. Run Automated Test
```bash
python test_balance_endpoint.py
```

## Current Balance Breakdown

**Last Update**: 2026-01-11 17:07:56 UTC

| Wallet Type | Balance (USDC) | Source |
|-------------|----------------|--------|
| Derived     | $24.00         | Blockchain (Web3) |
| Proxy       | $349.85        | Blockchain (Web3) |
| **TOTAL**   | **$373.85**    | Sum |

**Proxy Allowance**: 1.15e+71 USDC (effectively unlimited)

## Key Features

### ✅ Implemented
- [x] Instant cached response (< 1s)
- [x] Background blockchain updates (non-blocking)
- [x] JSON file persistence
- [x] HTTP-only UI architecture (no direct file reading)
- [x] Derived + Proxy wallet breakdown
- [x] Automatic cache refresh on request
- [x] Thread-safe background updates
- [x] Proper error handling and logging

### 🔧 Architecture Decisions
- **No direct file access from UI** - All data flows through HTTP API
- **Background threading** - Avoids blocking on slow RPC calls
- **Daemon threads** - Prevents hanging on Flask shutdown
- **Immediate cache response** - Better UX, shows stale data with `cached: true`
- **Automatic updates** - Each request triggers background refresh

## Troubleshooting

### Issue: Balance endpoint times out
**Solution**: Check if blockchain RPC is accessible
```bash
python -m utils.account.proxy-wallet.get_balance_proxy_address_blockchain
```

### Issue: Cached data is stale
**Solution**: Background thread may be slow, check logs
```bash
tail -f logs/flask.log
```

### Issue: JSON file not updating
**Solution**: Check background thread errors
```bash
grep "Background balance update failed" logs/flask.log
```

### Issue: Server import errors
**Solution**: Make sure all imports are non-relative (no `from fqs.` or `from ..`)
```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
python -c "from server import create_app; print('OK')"
```

## Server Management

### Start Server
```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
python -m server.run_flask
```

### Stop Server
```bash
pkill -9 -f "run_flask"
```

### Check Server Status
```bash
curl -s http://127.0.0.1:5000/api/health
```

### View Server Logs
```bash
tail -f logs/flask.log
```

## Success Criteria ✅

All requirements met:

1. ✅ **JSON file saved**: `data/balance.json` exists and updates
2. ✅ **Backend retrieves blockchain data**: Uses `get_balance_derived_address()` and `check_blockchain_balance()`
3. ✅ **Frontend fetches via HTTP**: UI calls `/api/balance` endpoint
4. ✅ **Fast response**: Cached data served instantly (< 1s)
5. ✅ **Accurate data**: Background updates from blockchain
6. ✅ **Derived + Proxy breakdown**: Both wallet balances shown separately

## Next Steps

### Optional Enhancements
- [ ] Add polling interval (e.g., auto-refresh every 30s)
- [ ] Cache expiration (e.g., force blockchain update if >5 min old)
- [ ] WebSocket for real-time balance updates
- [ ] Historical balance tracking
- [ ] Balance change notifications

---

**Status**: ✅ **FULLY FUNCTIONAL**  
**Date**: 2026-01-11  
**Version**: 1.0
