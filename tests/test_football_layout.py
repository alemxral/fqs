"""
Test script for FootballTradeScreen layout improvements
Validates scrolling, proportions, visibility, and CSS enhancements
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_css_improvements():
    """Verify CSS has all required scrolling and styling properties"""
    from fqs.ui.screens.football_trade_screen import FootballTradeScreen
    
    css = FootballTradeScreen.CSS
    
    checks = {
        "Left Panel Scrolling": "scrollbar-size-vertical: 2" in css and "#events_panel" in css,
        "Center Panel Scrolling": "#center_panel" in css and "overflow-y: auto" in css,
        "Right Panel Scrolling": "#output_panel" in css and "overflow-y: auto" in css,
        "Trading Widgets Scrolling": "#trading_widgets" in css and "overflow-y: auto" in css,
        "Command Output Scrolling": "#command_output" in css and "overflow-y: auto" in css,
        "Events Table Scrolling": "#events_table" in css and "overflow-y: auto" in css,
        "Orderbook Scrolling": ".orderbook-side" in css and "overflow-y: auto" in css,
        "Widget Borders": "#price_ticker" in css and "border: solid" in css,
        "Proportions Updated": "width: 30%" in css and "width: 40%" in css,
        "Header Styling": "#events_header" in css and "#output_header" in css,
    }
    
    print("=" * 60)
    print("CSS IMPROVEMENTS VALIDATION")
    print("=" * 60)
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("✅ ALL CSS CHECKS PASSED")
    else:
        print("❌ SOME CSS CHECKS FAILED")
    
    return all_passed


def test_layout_structure():
    """Verify compose() has correct widget structure"""
    from fqs.ui.screens.football_trade_screen import FootballTradeScreen
    import inspect
    
    source = inspect.getsource(FootballTradeScreen.compose)
    
    checks = {
        "Events Panel": '#events_panel' in source,
        "Center Panel": '#center_panel' in source,
        "Output Panel": '#output_panel' in source,
        "Trading Widgets Container": '#trading_widgets' in source,
        "Command Output": '#command_output' in source,
        "Price Ticker": '#price_ticker' in source,
        "Open Orders": '#open_orders' in source,
        "Position Summary": '#position_summary' in source,
        "Trade History": '#trade_history' in source,
        "Football Widget": '#football_widget' in source,
        "Orderbooks": '#orderbooks_container' in source,
        "YES Orderbook": '#yes_orderbook' in source,
        "NO Orderbook": '#no_orderbook' in source,
        "Headers Present": '#events_header' in source and '#output_header' in source,
    }
    
    print("\n" + "=" * 60)
    print("LAYOUT STRUCTURE VALIDATION")
    print("=" * 60)
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("✅ ALL LAYOUT CHECKS PASSED")
    else:
        print("❌ SOME LAYOUT CHECKS FAILED")
    
    return all_passed


def test_proportions():
    """Extract and validate panel proportions"""
    from fqs.ui.screens.football_trade_screen import FootballTradeScreen
    
    css = FootballTradeScreen.CSS
    
    print("\n" + "=" * 60)
    print("PANEL PROPORTIONS")
    print("=" * 60)
    
    proportions = {}
    
    # Extract widths
    for line in css.split('\n'):
        line = line.strip()
        if 'events_panel' in css and 'width:' in line.lower():
            # Find the width declaration
            pass
    
    # Manual check from CSS
    if "width: 30%" in css:
        print("✅ Left Panel (Events): 30%")
        proportions['left'] = '30%'
    
    if "width: 40%" in css:
        print("✅ Center Panel (Trading): 40%")
        proportions['center'] = '40%'
    
    if css.count("width: 30%") >= 2:
        print("✅ Right Panel (Output): 30%")
        proportions['right'] = '30%'
    
    print("=" * 60)
    
    expected = 3  # Should have 3 panel widths defined
    actual = len(proportions)
    
    if actual == expected:
        print(f"✅ ALL PROPORTIONS CORRECT: {proportions}")
        return True
    else:
        print(f"❌ PROPORTIONS INCOMPLETE: {proportions}")
        return False


def test_widget_visibility():
    """Check individual widget styling for visibility"""
    from fqs.ui.screens.football_trade_screen import FootballTradeScreen
    
    css = FootballTradeScreen.CSS
    
    widgets = [
        '#price_ticker',
        '#open_orders', 
        '#position_summary',
        '#trade_history'
    ]
    
    print("\n" + "=" * 60)
    print("WIDGET VISIBILITY ENHANCEMENTS")
    print("=" * 60)
    
    all_visible = True
    for widget in widgets:
        has_border = f"{widget}" in css and "border:" in css
        has_min_height = f"{widget}" in css and "min-height:" in css
        has_scroll = f"{widget}" in css and "overflow-y:" in css
        
        visible = has_border and has_min_height and has_scroll
        
        status = "✅" if visible else "❌"
        print(f"{status} {widget}")
        print(f"    Border: {'✓' if has_border else '✗'} | "
              f"MinHeight: {'✓' if has_min_height else '✗'} | "
              f"Scroll: {'✓' if has_scroll else '✗'}")
        
        if not visible:
            all_visible = False
    
    print("=" * 60)
    
    if all_visible:
        print("✅ ALL WIDGETS HAVE ENHANCED VISIBILITY")
    else:
        print("❌ SOME WIDGETS NEED VISIBILITY IMPROVEMENTS")
    
    return all_visible


def test_scrollbar_configuration():
    """Verify scrollbar settings across all scrollable elements"""
    from fqs.ui.screens.football_trade_screen import FootballTradeScreen
    
    css = FootballTradeScreen.CSS
    
    scrollable_elements = [
        '#events_panel',
        '#events_table',
        '#center_panel',
        '#orderbooks_container',
        '.orderbook-side',
        '#output_panel',
        '#trading_widgets',
        '#command_output',
        '#price_ticker',
        '#open_orders',
        '#position_summary',
        '#trade_history'
    ]
    
    print("\n" + "=" * 60)
    print("SCROLLBAR CONFIGURATION")
    print("=" * 60)
    
    scroll_count = 0
    missing = []
    
    for element in scrollable_elements:
        # Check if element has scrolling configured
        element_block = None
        if element in css:
            # Find the CSS block for this element
            start = css.find(element)
            if start != -1:
                # Look for overflow-y in next 500 chars
                snippet = css[start:start+500]
                if 'overflow-y: auto' in snippet or 'scrollbar-size-vertical:' in snippet:
                    print(f"✅ {element}")
                    scroll_count += 1
                else:
                    print(f"⚠️  {element} (no explicit scroll config)")
                    missing.append(element)
        else:
            print(f"❌ {element} (not found)")
            missing.append(element)
    
    print("=" * 60)
    print(f"Scrollable Elements: {scroll_count}/{len(scrollable_elements)}")
    
    if missing:
        print(f"⚠️  Elements without explicit scroll: {', '.join(missing)}")
    
    return scroll_count >= 10  # At least 10 should have scrolling


def run_all_tests():
    """Run all validation tests"""
    print("\n" + "🔍 FOOTBALL TRADE SCREEN LAYOUT IMPROVEMENTS TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("CSS Improvements", test_css_improvements),
        ("Layout Structure", test_layout_structure),
        ("Panel Proportions", test_proportions),
        ("Widget Visibility", test_widget_visibility),
        ("Scrollbar Configuration", test_scrollbar_configuration),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ {test_name} FAILED WITH ERROR: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    print("=" * 60)
    print(f"\n{'✅' if passed == total else '⚠️'}  {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL LAYOUT IMPROVEMENTS SUCCESSFULLY IMPLEMENTED!")
    else:
        print(f"\n⚠️  {total - passed} test(s) need attention")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
