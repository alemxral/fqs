#!/usr/bin/env python3
"""
Simple test script to check balance fetch directly
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

print("="*80)
print("SIMPLE BALANCE FETCH TEST")
print("="*80)

# Test 1: Import ClobClientWrapper
print("\n[Test 1] Importing ClobClientWrapper...")
try:
    from client.ClobClientWrapper import get_authenticated_client
    print("✅ Import successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Create client
print("\n[Test 2] Creating authenticated client...")
try:
    client = get_authenticated_client()
    print(f"✅ Client created: {type(client)}")
except Exception as e:
    print(f"❌ Client creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Get balance
print("\n[Test 3] Fetching balance...")
try:
    from client.py_clob_client.clob_types import BalanceAllowanceParams, AssetType
    params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)  # USDC balance
    balance_data = client.get_balance_allowance(params)
    print(f"✅ Balance data: {balance_data}")
    
    if isinstance(balance_data, dict):
        balance = balance_data.get('balance', 0)
        allowance = balance_data.get('allowance', 0)
        print(f"\n💰 Balance: ${balance}")
        print(f"💳 Allowance: ${allowance}")
    else:
        print(f"⚠️  Unexpected data type: {type(balance_data)}")
        
except Exception as e:
    print(f"❌ Balance fetch failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("✅ ALL TESTS PASSED")
print("="*80)
