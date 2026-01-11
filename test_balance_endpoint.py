#!/usr/bin/env python3
"""
Test the /api/balance endpoint to ensure:
1. Server responds immediately with cached data
2. JSON file is served correctly
3. Background thread updates the file
"""

import sys
import time
import json
import requests
from pathlib import Path

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def test_balance_endpoint():
    print(f"\n{BLUE}{'='*60}")
    print("BALANCE ENDPOINT TEST")
    print(f"{'='*60}{RESET}\n")
    
    base_url = "http://127.0.0.1:5000"
    balance_file = Path(__file__).parent / "data" / "balance.json"
    
    # 1. Check if cache file exists
    print(f"{YELLOW}1. Checking balance.json cache file...{RESET}")
    if balance_file.exists():
        print(f"{GREEN}✅ Cache file exists: {balance_file}{RESET}")
        with open(balance_file, 'r') as f:
            cached_data = json.load(f)
            print(f"   Balance: ${cached_data.get('balance', 0):.2f} USDC")
            print(f"   Derived: ${cached_data.get('derived_balance', 0):.2f}")
            print(f"   Proxy:   ${cached_data.get('proxy_balance', 0):.2f}")
    else:
        print(f"{RED}❌ No cache file found{RESET}")
    
    # 2. Test health endpoint
    print(f"\n{YELLOW}2. Testing /api/health endpoint...{RESET}")
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            print(f"{GREEN}✅ Server is healthy: {response.json()}{RESET}")
        else:
            print(f"{RED}❌ Health check failed: {response.status_code}{RESET}")
            return False
    except Exception as e:
        print(f"{RED}❌ Cannot connect to server: {e}{RESET}")
        print(f"{YELLOW}   Make sure Flask server is running on port 5000{RESET}")
        return False
    
    # 3. Test balance endpoint - measure response time
    print(f"\n{YELLOW}3. Testing /api/balance endpoint...{RESET}")
    start_time = time.time()
    try:
        response = requests.get(f"{base_url}/api/balance", timeout=10)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"{GREEN}✅ Balance endpoint responded in {elapsed:.2f}s{RESET}")
            print(f"   Success: {data.get('success')}")
            print(f"   Balance: ${data.get('balance', 0):.2f} USDC")
            print(f"   Derived: ${data.get('derived_balance', 0):.2f}")
            print(f"   Proxy:   ${data.get('proxy_balance', 0):.2f}")
            print(f"   Cached:  {data.get('cached', False)}")
            print(f"   Updating: {data.get('updating', False)}")
            
            # Verify it's fast (should be < 1s if serving from cache)
            if elapsed < 1.0:
                print(f"{GREEN}✅ Response was INSTANT (cached data){RESET}")
            elif elapsed < 5.0:
                print(f"{YELLOW}⚠️  Response was somewhat slow ({elapsed:.2f}s){RESET}")
            else:
                print(f"{RED}❌ Response was VERY SLOW ({elapsed:.2f}s) - not serving from cache!{RESET}")
            
            return True
        else:
            print(f"{RED}❌ Balance endpoint error: {response.status_code}{RESET}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.Timeout:
        elapsed = time.time() - start_time
        print(f"{RED}❌ Balance endpoint TIMED OUT after {elapsed:.2f}s{RESET}")
        print(f"{YELLOW}   This means the server is blocking on blockchain calls{RESET}")
        return False
    except Exception as e:
        print(f"{RED}❌ Balance endpoint failed: {e}{RESET}")
        return False
    
    # 4. Wait and check if JSON file was updated
    print(f"\n{YELLOW}4. Waiting 10s for background update...{RESET}")
    time.sleep(10)
    
    if balance_file.exists():
        with open(balance_file, 'r') as f:
            updated_data = json.load(f)
            timestamp = updated_data.get('timestamp', 'unknown')
            print(f"{GREEN}✅ Balance file still exists{RESET}")
            print(f"   Timestamp: {timestamp}")
            print(f"   Balance: ${updated_data.get('balance', 0):.2f} USDC")
    else:
        print(f"{RED}❌ Balance file disappeared!{RESET}")

if __name__ == "__main__":
    try:
        success = test_balance_endpoint()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted{RESET}")
        sys.exit(1)
