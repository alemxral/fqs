#!/usr/bin/env python3
"""
Standalone test for Gamma API and market loading
Does not require Textual or UI imports
"""
import sys
from pathlib import Path

# Add utils path
project_root = Path(__file__).parent.parent.parent
utils_path = project_root / "fqs" / "utils" / "gamma-api"
if str(utils_path) not in sys.path:
    sys.path.insert(0, str(utils_path))

try:
    from get_events_with_tags import get_events_with_tags
    GAMMA_AVAILABLE = True
except ImportError as e:
    print(f"❌ Cannot import Gamma API: {e}")
    GAMMA_AVAILABLE = False
    sys.exit(1)


def test_basic_call():
    """Test basic Gamma API call"""
    print("\n" + "="*70)
    print("TEST 1: Basic Gamma API Call (Football Tag)")
    print("="*70)
    
    try:
        print("📡 Calling: get_events_with_tags(tag_id=100381, limit=5, closed=False, order='id', ascending=False)")
        
        events = get_events_with_tags(
            tag_id=100381,
            limit=5,
            closed=False,
            order="id",
            ascending=False
        )
        
        print(f"\n📦 Response type: {type(events)}")
        
        if isinstance(events, list):
            print(f"✅ Got list with {len(events)} events")
            
            if len(events) == 0:
                print("⚠️  WARNING: Empty list returned!")
                print("   This means:")
                print("   - API call succeeded")
                print("   - But no football events match the criteria")
                print("   - Check if tag_id=100381 is correct")
                return False
            
            # Show details of first event
            for i, event in enumerate(events[:3], 1):
                print(f"\n📋 Event {i}:")
                print(f"   ID: {event.get('id', 'N/A')}")
                print(f"   Title: {event.get('title', 'N/A')[:70]}")
                print(f"   Slug: {event.get('slug', 'N/A')}")
                print(f"   Active: {event.get('active', 'N/A')}")
                print(f"   Closed: {event.get('closed', 'N/A')}")
                
                markets = event.get('markets', [])
                print(f"   Markets: {len(markets) if markets else 0}")
                
                if markets and len(markets) > 0:
                    print(f"   First Market: {markets[0].get('question', 'N/A')[:50]}")
            
            return True
            
        elif isinstance(events, dict):
            print(f"⚠️  Got dict instead of list:")
            print(f"   Keys: {list(events.keys())[:10]}")
            return False
            
        else:
            print(f"❌ Unexpected type: {type(events)}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_without_tag():
    """Test API call without tag filter"""
    print("\n" + "="*70)
    print("TEST 2: API Call Without Tag Filter (All Events)")
    print("="*70)
    
    try:
        print("📡 Calling: get_events_with_tags(limit=5, closed=False, order='id')")
        
        events = get_events_with_tags(
            limit=5,
            closed=False,
            order="id"
        )
        
        if isinstance(events, list) and len(events) > 0:
            print(f"✅ Got {len(events)} events (no tag filter)")
            
            for i, event in enumerate(events[:2], 1):
                print(f"\n   Event {i}: {event.get('title', 'N/A')[:60]}")
                print(f"   Tags: {event.get('tags', [])}")
            
            return True
        else:
            print(f"⚠️  Got {len(events) if isinstance(events, list) else 0} events")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_different_tags():
    """Test with different tag IDs"""
    print("\n" + "="*70)
    print("TEST 3: Testing Different Tag IDs")
    print("="*70)
    
    # Common Polymarket tags
    tags_to_test = [
        (100381, "Football"),
        (100000, "Sports (generic)"),
        (1, "Tag ID 1"),
    ]
    
    results = {}
    
    for tag_id, name in tags_to_test:
        try:
            print(f"\n🔍 Testing tag_id={tag_id} ({name})...")
            
            events = get_events_with_tags(
                tag_id=tag_id,
                limit=3,
                closed=False,
                order="id"
            )
            
            if isinstance(events, list):
                count = len(events)
                results[tag_id] = count
                print(f"   ✅ Found {count} events")
                
                if count > 0:
                    print(f"   First: {events[0].get('title', 'N/A')[:50]}")
            else:
                results[tag_id] = 0
                print(f"   ❌ Got {type(events)} instead of list")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[tag_id] = -1
    
    print(f"\n📊 Summary:")
    for tag_id, name in tags_to_test:
        count = results.get(tag_id, -1)
        if count > 0:
            print(f"   ✅ tag_id={tag_id} ({name}): {count} events")
        elif count == 0:
            print(f"   ⚠️  tag_id={tag_id} ({name}): No events found")
        else:
            print(f"   ❌ tag_id={tag_id} ({name}): Error")
    
    return any(c > 0 for c in results.values())


def test_order_params():
    """Test different order parameters"""
    print("\n" + "="*70)
    print("TEST 4: Testing Order Parameters")
    print("="*70)
    
    order_tests = [
        {"order": "id", "ascending": False, "desc": "Newest IDs first"},
        {"order": "id", "ascending": True, "desc": "Oldest IDs first"},
    ]
    
    passed = 0
    for test_params in order_tests:
        try:
            desc = test_params.pop("desc")
            print(f"\n🔍 Testing: {desc}")
            print(f"   Params: {test_params}")
            
            events = get_events_with_tags(
                limit=3,
                closed=False,
                **test_params
            )
            
            if isinstance(events, list) and len(events) > 0:
                print(f"   ✅ Got {len(events)} events")
                ids = [e.get('id', 'N/A') for e in events]
                print(f"   Event IDs: {ids}")
                passed += 1
            else:
                print(f"   ⚠️  Got {len(events) if isinstance(events, list) else 0} events")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return passed > 0


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 GAMMA API STANDALONE TEST SUITE")
    print("="*70)
    
    if not GAMMA_AVAILABLE:
        print("❌ Gamma API not available - cannot run tests")
        return False
    
    tests = [
        ("Basic Call (Football)", test_basic_call),
        ("No Tag Filter", test_without_tag),
        ("Different Tags", test_different_tags),
        ("Order Parameters", test_order_params),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("📊 FINAL RESULTS")
    print("="*70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{'='*70}")
    print(f"Score: {passed}/{total} tests passed")
    print(f"{'='*70}")
    
    if passed < total:
        print("\n💡 DIAGNOSIS:")
        if not any(r for _, r in results):
            print("   - No tests passed")
            print("   - This suggests API might be down or tag_id is wrong")
            print("   - Try checking Polymarket API status")
        else:
            print("   - Some tests passed, some failed")
            print("   - Check specific failures above for details")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
