#!/usr/bin/env python3
"""
Test blockchain balance fetching
"""
import sys
from pathlib import Path

# Add utils paths
utils_derived_path = Path(__file__).parent / "utils" / "account" / "derived-wallet"
utils_proxy_path = Path(__file__).parent / "utils" / "account" / "proxy-wallet"

sys.path.insert(0, str(utils_derived_path))
sys.path.insert(0, str(utils_proxy_path))

print("="*80)
print("BLOCKCHAIN BALANCE TEST")
print("="*80)

# Test 1: Derived wallet
print("\n[Test 1] Fetching derived wallet balance...")
try:
    from get_balance_derived_address_blockchain import get_balance_derived_address
    derived_balance = get_balance_derived_address("USDC")
    print(f"✅ Derived Balance: ${derived_balance:.2f} USDC")
except Exception as e:
    print(f"❌ Error: {e}")
    derived_balance = 0.0

# Test 2: Proxy wallet  
print("\n[Test 2] Fetching proxy wallet balance...")
try:
    from get_balance_proxy_address_blockchain import check_blockchain_balance
    proxy_balance, proxy_allowance = check_blockchain_balance(verbose=True)
    print(f"✅ Proxy Balance: ${proxy_balance:.2f} USDC")
    print(f"✅ Proxy Allowance: ${proxy_allowance:.2f} USDC")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    proxy_balance = 0.0
    proxy_allowance = 0.0

# Test 3: Total
print("\n[Test 3] Calculating total...")
total_balance = derived_balance + proxy_balance
print(f"💰 Total Balance: ${total_balance:.2f} USDC")

# Test 4: Save to JSON
print("\n[Test 4] Saving to JSON...")
try:
    import json
    from datetime import datetime
    
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    balance_file = data_dir / "balance.json"
    
    balance_data = {
        'success': True,
        'balance': total_balance,
        'derived_balance': derived_balance,
        'proxy_balance': proxy_balance,
        'proxy_allowance': proxy_allowance,
        'currency': 'USDC',
        'timestamp': datetime.utcnow().isoformat(),
        'source': 'blockchain_test'
    }
    
    with open(balance_file, 'w') as f:
        json.dump(balance_data, f, indent=2)
    
    print(f"✅ Saved to: {balance_file}")
except Exception as e:
    print(f"❌ Save error: {e}")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
