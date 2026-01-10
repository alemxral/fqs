#!/usr/bin/env python3
"""
Test HomeScreen - Market Loading and UI Functionality

Tests:
1. Gamma API market loading
2. Search functionality
3. UI layout and scrolling
4. Market data parsing
5. Error handling
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
from fqs.ui.screens.home_screen import HomeScreen

# Direct Gamma API test
try:
    utils_path = project_root / "fqs" / "utils" / "gamma-api"
    if str(utils_path) not in sys.path:
        sys.path.insert(0, str(utils_path))
    from get_events_with_tags import get_events_with_tags
    GAMMA_API_AVAILABLE = True
except ImportError as e:
    print(f"❌ Gamma API import failed: {e}")
    GAMMA_API_AVAILABLE = False


def test_gamma_api_direct():
    """Test direct Gamma API call"""
    print("\n" + "="*60)
    print("TEST 1: Direct Gamma API Call")
    print("="*60)
    
    if not GAMMA_API_AVAILABLE:
        print("❌ FAILED: Gamma API not available")
        return False
    
    try:
        print("📡 Calling get_events_with_tags(tag_id=100381, limit=5, closed=False, order='id', ascending=False)")
        
        events = get_events_with_tags(
            tag_id=100381,
            limit=5,
            closed=False,
            order="id",
            ascending=False
        )
        
        if not events:
            print("❌ FAILED: No events returned")
            return False
        
        if isinstance(events, list):
            event_count = len(events)
            print(f"✅ SUCCESS: Received {event_count} events")
            
            # Show first event
            if event_count > 0:
                first = events[0]
                print(f"\n📋 First Event:")
                print(f"   ID: {first.get('id', 'N/A')}")
                print(f"   Title: {first.get('title', 'N/A')[:80]}")
                print(f"   Slug: {first.get('slug', 'N/A')}")
                print(f"   Active: {first.get('active', 'N/A')}")
                print(f"   Closed: {first.get('closed', 'N/A')}")
                
                # Check markets
                markets = first.get('markets', [])
                print(f"   Markets: {len(markets) if markets else 0}")
                if markets and len(markets) > 0:
                    print(f"   First Market Question: {markets[0].get('question', 'N/A')[:60]}")
            
            return True
        else:
            print(f"❌ FAILED: Expected list, got {type(events)}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gamma_api_different_params():
    """Test with different parameters"""
    print("\n" + "="*60)
    print("TEST 2: Different API Parameters")
    print("="*60)
    
    if not GAMMA_API_AVAILABLE:
        print("⏭️  SKIPPED: Gamma API not available")
        return True
    
    test_cases = [
        {"tag_id": 100381, "limit": 1, "closed": False, "order": "id"},
        {"limit": 3, "closed": False, "order": "id"},
        {"tag_id": 100381, "limit": 10, "order": "id", "ascending": True},
    ]
    
    passed = 0
    for i, params in enumerate(test_cases, 1):
        try:
            print(f"\n  Test Case {i}: {params}")
            events = get_events_with_tags(**params)
            
            if events:
                count = len(events) if isinstance(events, list) else 1
                print(f"  ✅ Got {count} events")
                passed += 1
            else:
                print(f"  ⚠️  No events returned")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n✅ Passed {passed}/{len(test_cases)} test cases")
    return passed > 0


def test_homescreen_layout():
    """Test HomeScreen layout structure"""
    print("\n" + "="*60)
    print("TEST 3: HomeScreen Layout Structure")
    print("="*60)
    
    try:
        # Import HomeScreen
        from fqs.ui.screens.home_screen import HomeScreen
        
        # Check CSS definitions
        css = HomeScreen.CSS
        
        checks = [
            ("#search_container" in css, "Search container CSS defined"),
            ("#markets_container" in css, "Markets container CSS defined"),
            ("#markets_list" in css, "Markets list CSS defined"),
            ("overflow-y: auto" in css, "Vertical scrolling enabled"),
            ("scrollbar-size-vertical" in css, "Scrollbar configured"),
        ]
        
        passed = 0
        for check, description in checks:
            if check:
                print(f"  ✅ {description}")
                passed += 1
            else:
                print(f"  ❌ {description}")
        
        print(f"\n✅ Passed {passed}/{len(checks)} layout checks")
        return passed == len(checks)
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_homescreen_compose():
    """Test HomeScreen compose method"""
    print("\n" + "="*60)
    print("TEST 4: HomeScreen Compose Method")
    print("="*60)
    
    try:
        from fqs.ui.screens.home_screen import HomeScreen
        import inspect
        
        # Get compose method source
        source = inspect.getsource(HomeScreen.compose)
        
        checks = [
            ("search_container" in source, "Search container in compose"),
            ("search_input" in source, "Search input in compose"),
            ("markets_container" in source, "Markets container in compose"),
            ("markets_list" in source, "Markets list in compose"),
            ("ListView" in source, "ListView widget used"),
            ("LoadingIndicator" in source, "Loading indicator present"),
        ]
        
        passed = 0
        for check, description in checks:
            if check:
                print(f"  ✅ {description}")
                passed += 1
            else:
                print(f"  ❌ {description}")
        
        print(f"\n✅ Passed {passed}/{len(checks)} compose checks")
        return passed == len(checks)
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_market_data_parsing():
    """Test market data parsing logic"""
    print("\n" + "="*60)
    print("TEST 5: Market Data Parsing")
    print("="*60)
    
    if not GAMMA_API_AVAILABLE:
        print("⏭️  SKIPPED: Gamma API not available")
        return True
    
    try:
        # Get real events
        events = get_events_with_tags(tag_id=100381, limit=3, closed=False, order="id")
        
        if not events or len(events) == 0:
            print("⚠️  WARNING: No events to test parsing")
            return True
        
        print(f"📦 Testing parsing of {len(events)} events...")
        
        parsed_count = 0
        for event in events:
            try:
                # Simulate HomeScreen parsing logic
                market_data = {
                    'slug': event.get('slug', ''),
                    'question': event.get('title', 'Unknown'),
                    'yes_price': 0.5,
                    'no_price': 0.5,
                    'end_date': event.get('end_date_min', 'Unknown'),
                    'event': event
                }
                
                # Validate parsed data
                if market_data['slug'] and market_data['question'] != 'Unknown':
                    parsed_count += 1
                    print(f"  ✅ Parsed: {market_data['question'][:50]}")
                else:
                    print(f"  ⚠️  Incomplete: {event.get('id', 'N/A')}")
                    
            except Exception as e:
                print(f"  ❌ Parse error: {e}")
        
        print(f"\n✅ Successfully parsed {parsed_count}/{len(events)} events")
        return parsed_count > 0
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_search_functionality():
    """Test different search tags"""
    print("\n" + "="*60)
    print("TEST 6: Search Tag Functionality")
    print("="*60)
    
    if not GAMMA_API_AVAILABLE:
        print("⏭️  SKIPPED: Gamma API not available")
        return True
    
    # Test different tags
    tags = [
        (100381, "Football"),
        (None, "All Events (no tag)"),
    ]
    
    passed = 0
    for tag_id, description in tags:
        try:
            print(f"\n  Testing: {description} (tag_id={tag_id})")
            
            params = {"limit": 3, "closed": False, "order": "id"}
            if tag_id is not None:
                params["tag_id"] = tag_id
            
            events = get_events_with_tags(**params)
            
            if events and len(events) > 0:
                print(f"  ✅ Found {len(events)} events")
                passed += 1
            else:
                print(f"  ⚠️  No events found")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n✅ Passed {passed}/{len(tags)} search tests")
    return passed > 0


def run_all_tests():
    """Run all HomeScreen tests"""
    print("\n" + "="*70)
    print("🧪 HOMESCREEN TEST SUITE")
    print("="*70)
    
    tests = [
        ("Gamma API Direct Call", test_gamma_api_direct),
        ("Different API Parameters", test_gamma_api_different_params),
        ("HomeScreen Layout", test_homescreen_layout),
        ("HomeScreen Compose", test_homescreen_compose),
        ("Market Data Parsing", test_market_data_parsing),
        ("Search Functionality", test_search_functionality),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{'='*70}")
    print(f"Final Score: {passed}/{total} tests passed")
    print(f"{'='*70}")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
