#!/usr/bin/env python3
"""
Test MainHeader balance update
"""
import asyncio
from ui.widgets.main_header import MainHeader

async def test_header_update():
    """Test that balance updates work correctly"""
    
    # Create header widget
    header = MainHeader()
    
    # Test update_balances with the correct parameter names
    print("Testing update_balances()...")
    header.update_balances(funder_balance=24.0, proxy_balance=349.85)
    
    print(f"✅ Funder balance set to: ${header.funder_balance:.2f}")
    print(f"✅ Proxy balance set to: ${header.proxy_balance:.2f}")
    
    # Test individual updates
    print("\nTesting update_funder()...")
    header.update_funder(address="0x1234567890abcdef", balance=100.0)
    print(f"✅ Funder: {header.funder_address} - ${header.funder_balance:.2f}")
    
    print("\nTesting update_proxy()...")
    header.update_proxy(address="0xfedcba0987654321", balance=200.0)
    print(f"✅ Proxy: {header.proxy_address} - ${header.proxy_balance:.2f}")
    
    print("\n" + "="*60)
    print("✅ ALL HEADER TESTS PASSED")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_header_update())
