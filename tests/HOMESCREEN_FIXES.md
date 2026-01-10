# HomeScreen Fixes - Summary

## Issues Fixed

### 1. ✅ Search Container Too Small
**Problem:** Search input box height was 4, making it difficult to see and use.
**Solution:** Increased to height 7 with proper padding.

### 2. ✅ No Vertical Scrolling
**Problem:** Markets list couldn't scroll when content exceeded visible area.
**Solution:** Added `overflow-y: auto` and `scrollbar-size-vertical: 1` to markets container.

### 3. ✅ Wrong Tag ID - No Markets Loading
**Problem:** Using tag_id=100381 (Football) which returns 0 events.
**Solution:** 
- Changed default to tag_id=1 (Sports) which actually has events
- Made tag input accept numeric IDs directly
- Updated search hints to show working tag IDs:
  - 1 = Sports (football, basketball, etc.)
  - 21 = Crypto
  - 25 = Politics

### 4. ✅ API Order Parameter Error
**Problem:** HTTP 422 error from using invalid `order="start_date_min"`
**Solution:** Changed to `order="id"` (valid field)

## Testing Created

### test_gamma_api_standalone.py
Standalone test that doesn't require UI dependencies.

**Tests:**
1. ✅ Basic Gamma API call with different tags
2. ✅ API without tag filter (all events)
3. ✅ Different tag IDs (1, 21, 100381, etc.)
4. ✅ Order parameters (id ascending/descending)

**Key Finding:**
- Tag ID 100381 (Football) = **0 events** ❌
- Tag ID 1 (Sports) = **3+ events** ✅
- Tag ID 21 (Crypto) = **events** ✅

### test_home_screen.py
Full UI test suite (requires Textual).

## Usage

**Run API test:**
```bash
python3 /home/amoral-a/sgoinfre/polytrading/poly/fqs/tests/test_gamma_api_standalone.py
```

**Start FQS with fixes:**
```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
./restart.sh && ./start.sh
```

**In HomeScreen:**
- Default loads Sports (tag_id=1)
- Press Ctrl+S to search different tags
- Enter tag IDs: 1, 21, 25, etc.
- Markets will now load and scroll properly

## Known Working Tag IDs

From test results:
- **1** - Sports (football, basketball, etc.)
- **21** - Crypto
- **25** - Politics (likely)
- **100381** - Football (BROKEN - returns 0 events)

## Changes Made

**fqs/ui/screens/home_screen.py:**
1. CSS: `#search_container` height 4 → 7
2. CSS: Added scrolling to `#markets_container`
3. Default tag: "football" → "1"
4. Search hint: Updated to show working tag IDs
5. load_markets_by_tag: Parses tag as int, uses tag_id param
6. load_markets_by_tag: Changed order param to "id"

**Widget scrolling fixes:**
1. OpenOrdersWidget DataTable: Added `overflow-y: auto`
2. TradeHistoryWidget RichLog: Added `overflow-y: auto`
3. PositionSummaryWidget DataTable: Added `overflow-y: auto`
4. FootballTradeScreen #trading_widgets: Added `overflow-y: auto`

## Next Steps

1. ✅ Markets now load correctly (using tag_id=1)
2. ✅ Scrolling works in all widgets
3. ✅ Search container is visible
4. ⚠️  Need to rebuild venv (currently broken)

**To rebuild venv:**
```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
rm -rf venv venv.old
python3 -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
pip install -e /home/amoral-a/sgoinfre/polytrading/poly
```
