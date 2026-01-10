"""
Test UI Components and Layout
Verifies that widgets are properly composed in the screen
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from textual.app import App
from fqs.ui.screens.football_trade_screen import FootballTradeScreen
from fqs.ui.widgets.open_orders import OpenOrdersWidget
from fqs.ui.widgets.price_ticker import PriceTickerWidget
from fqs.ui.widgets.trade_history import TradeHistoryWidget
from fqs.ui.widgets.position_summary import PositionSummaryWidget


def test_screen_composition():
    """Test that FootballTradeScreen composes all widgets"""
    print("🧪 Testing FootballTradeScreen Composition...")
    print("-" * 60)
    
    # Create a minimal app to mount the screen
    class TestApp(App):
        def __init__(self):
            super().__init__()
            self.session = {
                'yes_token': 'test_yes_token',
                'no_token': 'test_no_token',
                'market_slug': 'test-market',
                'market_question': 'Test Market Question'
            }
    
    try:
        app = TestApp()
        screen = FootballTradeScreen()
        
        # Get composed widgets
        widgets = list(screen.compose())
        
        print(f"✅ Screen composes {len(widgets)} top-level widgets")
        
        # Check for specific widget types
        widget_types = [type(w).__name__ for w in widgets]
        print(f"📋 Composed widgets: {', '.join(widget_types)}")
        
        # Check CSS
        if screen.CSS:
            print(f"✅ Screen has CSS defined ({len(screen.CSS)} chars)")
        else:
            print(f"❌ Screen has no CSS")
        
        # Check bindings
        if screen.BINDINGS:
            print(f"✅ Screen has {len(screen.BINDINGS)} bindings")
        else:
            print(f"⚠️  Screen has no bindings")
        
        return True
        
    except Exception as e:
        print(f"❌ Screen composition failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_widget_ids():
    """Test that widgets have correct IDs"""
    print("\n🧪 Testing Widget IDs in Screen...")
    print("-" * 60)
    
    from textual.app import App
    
    class TestApp(App):
        def __init__(self):
            super().__init__()
            self.session = {
                'yes_token': 'test_yes_token',
                'no_token': 'test_no_token',
                'market_slug': 'test-market',
                'market_question': 'Test Market Question'
            }
    
    try:
        app = TestApp()
        screen = FootballTradeScreen()
        
        # Expected widget IDs
        expected_ids = [
            "price_ticker",
            "open_orders",
            "position_summary",
            "trade_history",
            "command_output",
            "command_input",
        ]
        
        # Compose and check
        composed = list(screen.compose())
        
        # Since widgets are nested in containers, we need to walk the tree
        def get_all_ids(widgets, depth=0):
            """Recursively get all widget IDs"""
            ids = []
            for widget in widgets:
                if hasattr(widget, 'id') and widget.id:
                    ids.append(widget.id)
                # Check children
                if hasattr(widget, '_nodes'):
                    ids.extend(get_all_ids(widget._nodes, depth+1))
                elif hasattr(widget, 'compose'):
                    try:
                        children = list(widget.compose())
                        ids.extend(get_all_ids(children, depth+1))
                    except:
                        pass
            return ids
        
        all_ids = get_all_ids(composed)
        print(f"📋 Found widget IDs: {', '.join(all_ids)}")
        
        found_count = 0
        for expected_id in expected_ids:
            if expected_id in all_ids:
                print(f"✅ Widget ID found: {expected_id}")
                found_count += 1
            else:
                print(f"❌ Widget ID missing: {expected_id}")
        
        print(f"\n✅ Found {found_count}/{len(expected_ids)} expected widget IDs")
        return found_count == len(expected_ids)
        
    except Exception as e:
        print(f"❌ Widget ID test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all UI tests"""
    print("="*60)
    print("🎨 FQS UI Test Suite")
    print("="*60 + "\n")
    
    results = []
    
    # Test screen composition
    results.append(test_screen_composition())
    
    # Test widget IDs
    results.append(test_widget_ids())
    
    # Summary
    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)
    print(f"UI Tests: {passed}/{total} passed")
    print("="*60)
    
    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
