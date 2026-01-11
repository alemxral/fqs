#!/usr/bin/env python3
"""
Quick Verification Script
Tests that the balance system is working correctly
"""

import requests
import json
import sys
from pathlib import Path

def main():
    print("\n" + "="*60)
    print("BALANCE SYSTEM VERIFICATION")
    print("="*60 + "\n")
    
    # 1. Check server is running
    print("1. Testing Flask server...")
    try:
        r = requests.get("http://127.0.0.1:5000/api/health", timeout=3)
        if r.status_code == 200:
            print("   ✅ Server is running")
        else:
            print(f"   ❌ Server returned {r.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot connect to server: {e}")
        print("   💡 Start server with: python -m server.run_flask")
        return False
    
    # 2. Check balance endpoint
    print("\n2. Testing balance endpoint...")
    try:
        r = requests.get("http://127.0.0.1:5000/api/balance", timeout=5)
        data = r.json()
        
        print(f"   ✅ Balance endpoint responded")
        print(f"   📊 Total Balance: ${data.get('balance', 0):.2f} USDC")
        print(f"   💰 Derived Wallet: ${data.get('derived_balance', 0):.2f}")
        print(f"   💰 Proxy Wallet: ${data.get('proxy_balance', 0):.2f}")
        print(f"   💾 Cached: {data.get('cached', False)}")
        print(f"   🔄 Updating: {data.get('updating', False)}")
        print(f"   📅 Timestamp: {data.get('timestamp', 'N/A')}")
        
    except Exception as e:
        print(f"   ❌ Balance endpoint failed: {e}")
        return False
    
    # 3. Check JSON file exists
    print("\n3. Checking balance.json cache file...")
    balance_file = Path("data/balance.json")
    if balance_file.exists():
        print(f"   ✅ Cache file exists: {balance_file}")
        with open(balance_file) as f:
            cached = json.load(f)
            print(f"   📄 Cached balance: ${cached.get('balance', 0):.2f} USDC")
    else:
        print(f"   ❌ Cache file not found: {balance_file}")
        return False
    
    # 4. Verify data consistency
    print("\n4. Verifying data consistency...")
    api_balance = data.get('balance', 0)
    cached_balance = cached.get('balance', 0)
    
    if abs(api_balance - cached_balance) < 0.01:
        print(f"   ✅ API and cache match: ${api_balance:.2f}")
    else:
        print(f"   ⚠️  API ({api_balance}) != Cache ({cached_balance})")
    
    # 5. Check derived + proxy = total
    derived = data.get('derived_balance', 0)
    proxy = data.get('proxy_balance', 0)
    total = data.get('balance', 0)
    calculated_total = derived + proxy
    
    if abs(total - calculated_total) < 0.01:
        print(f"   ✅ Balance breakdown correct: {derived} + {proxy} = {total}")
    else:
        print(f"   ❌ Balance mismatch: {derived} + {proxy} ≠ {total}")
        return False
    
    print("\n" + "="*60)
    print("✅ ALL CHECKS PASSED - BALANCE SYSTEM WORKING")
    print("="*60 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Verification interrupted")
        sys.exit(1)
