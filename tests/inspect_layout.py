"""
Quick Visual Check - Shows what's in FootballTradeScreen
Run this to see the actual screen structure
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def inspect_screen_layout():
    """Inspect the FootballTradeScreen layout"""
    print("="*70)
    print("📐 FootballTradeScreen Layout Inspector")
    print("="*70 + "\n")
    
    # Read the screen file
    screen_file = PROJECT_ROOT / "fqs" / "ui" / "screens" / "football_trade_screen.py"
    
    with open(screen_file, 'r') as f:
        content = f.read()
    
    # Check for widgets
    widgets_to_find = [
        ("OpenOrdersWidget", "open_orders"),
        ("PriceTickerWidget", "price_ticker"),
        ("TradeHistoryWidget", "trade_history"),
        ("PositionSummaryWidget", "position_summary"),
    ]
    
    print("🔍 Checking for Widget Imports...")
    print("-" * 70)
    for widget_class, widget_id in widgets_to_find:
        if f"from fqs.ui.widgets" in content and widget_class in content:
            print(f"✅ {widget_class} imported")
        else:
            print(f"❌ {widget_class} NOT imported")
    
    print("\n🔍 Checking for Widget Usage in compose()...")
    print("-" * 70)
    for widget_class, widget_id in widgets_to_find:
        if f"yield {widget_class}" in content or f"{widget_class}(" in content:
            print(f"✅ {widget_class} yielded in compose()")
        else:
            print(f"❌ {widget_class} NOT yielded in compose()")
    
    print("\n🔍 Checking for Widget IDs...")
    print("-" * 70)
    for widget_class, widget_id in widgets_to_find:
        if f'id="{widget_id}"' in content or f"id='{widget_id}'" in content:
            print(f"✅ Widget ID '{widget_id}' found")
        else:
            print(f"❌ Widget ID '{widget_id}' NOT found")
    
    # Check CSS
    print("\n🎨 Checking CSS...")
    print("-" * 70)
    if "#trading_widgets" in content:
        print("✅ #trading_widgets CSS selector found")
    else:
        print("❌ #trading_widgets CSS selector NOT found")
    
    # Extract compose method
    print("\n📝 compose() Method Preview...")
    print("-" * 70)
    
    import re
    compose_match = re.search(r'def compose\(self\)[^:]*:(.+?)(?=\n    def |\n    async def |\Z)', content, re.DOTALL)
    
    if compose_match:
        compose_body = compose_match.group(1)
        
        # Find widget yields
        widget_yields = re.findall(r'yield\s+(\w+)\(.*?\)', compose_body)
        print(f"Found {len(widget_yields)} yield statements:")
        for widget in widget_yields:
            print(f"  - yield {widget}(...)")
        
        # Check for our widgets specifically
        print("\n🎯 New Trading Widgets in compose():")
        if "PriceTickerWidget" in compose_body:
            print("  ✅ PriceTickerWidget")
        else:
            print("  ❌ PriceTickerWidget (MISSING)")
        
        if "OpenOrdersWidget" in compose_body:
            print("  ✅ OpenOrdersWidget")
        else:
            print("  ❌ OpenOrdersWidget (MISSING)")
            
        if "TradeHistoryWidget" in compose_body:
            print("  ✅ TradeHistoryWidget")
        else:
            print("  ❌ TradeHistoryWidget (MISSING)")
            
        if "PositionSummaryWidget" in compose_body:
            print("  ✅ PositionSummaryWidget")
        else:
            print("  ❌ PositionSummaryWidget (MISSING)")
    
    print("\n" + "="*70)
    print("✨ Layout inspection complete!")
    print("="*70)


if __name__ == "__main__":
    inspect_screen_layout()
