"""
Visual Test - DataTable Column Improvements
Quick check to verify the new column structure and formatting
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ui.screens.home_screen import HomeScreen
import inspect


def test_improvements():
    """Check all improvements are in place"""
    print("=" * 70)
    print("HOME SCREEN DATATABLE IMPROVEMENTS - VALIDATION")
    print("=" * 70)
    
    # Test 1: Column Headers
    print("\n1️⃣  COLUMN HEADERS CHECK")
    print("-" * 70)
    on_mount_source = inspect.getsource(HomeScreen.on_mount)
    
    expected_columns = [
        ("🔴", "Status indicator"),
        ("🏆 Match", "Match name column"),
        ("📅 Date/Time", "DateTime column"),
        ("✅ YES", "YES price column"),
        ("❌ NO", "NO price column"),
        ("📊 Volume", "Volume column"),
        ("🔗 Slug", "Slug column"),
    ]
    
    for col_name, description in expected_columns:
        if col_name in on_mount_source:
            print(f"   ✅ {description:25s} - '{col_name}'")
        else:
            print(f"   ❌ {description:25s} - MISSING")
    
    # Test 2: Horizontal Scrolling
    print("\n2️⃣  HORIZONTAL SCROLLING CHECK")
    print("-" * 70)
    css = HomeScreen.CSS
    
    scroll_checks = [
        ("overflow-x: auto", "Horizontal overflow"),
        ("scrollbar-size-horizontal", "Horizontal scrollbar size"),
        ("width: 100%", "Full width table"),
        ("min-width: 100%", "Minimum width constraint"),
    ]
    
    for check_str, description in scroll_checks:
        if check_str in css:
            print(f"   ✅ {description:30s} - Found")
        else:
            print(f"   ❌ {description:30s} - MISSING")
    
    # Test 3: Data Formatting
    print("\n3️⃣  DATA FORMATTING CHECK")
    print("-" * 70)
    populate_source = inspect.getsource(HomeScreen._populate_markets_table)
    
    format_checks = [
        ("is_live", "Live status detection"),
        ("🔴", "Live indicator emoji"),
        ("⏰", "Upcoming indicator emoji"),
        ("[:52]", "Match name truncation"),
        ("[green]", "YES price color (green)"),
        ("[red]", "NO price color (red)"),
        ("1000000", "Million volume threshold"),
        ("/1000", "Thousand volume division"),
        ("$volume/1000000", "Million formatting"),
        ("event.get('volume'", "Volume from event data"),
    ]
    
    for check_str, description in format_checks:
        if check_str in populate_source:
            print(f"   ✅ {description:30s} - Implemented")
        else:
            print(f"   ❌ {description:30s} - MISSING")
    
    # Test 4: CSS Enhancements
    print("\n4️⃣  CSS ENHANCEMENTS CHECK")
    print("-" * 70)
    
    css_checks = [
        ("datatable--header", "Header styling"),
        ("height: 3", "Row height"),
        ("datatable--fixed", "Fixed header style"),
        ("datatable--hover", "Hover effect"),
        ("datatable--cursor", "Cursor styling"),
        ("min-height: 3", "Minimum row height"),
    ]
    
    for check_str, description in css_checks:
        if check_str in css:
            print(f"   ✅ {description:30s} - Defined")
        else:
            print(f"   ❌ {description:30s} - MISSING")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\n✨ DataTable Improvements:")
    print("   • 7 new column headers with icons")
    print("   • Horizontal + vertical scrolling support")
    print("   • Live status indicators (🔴/⏰)")
    print("   • Color-coded YES/NO prices (green/red)")
    print("   • Smart volume formatting ($XXK/$XXM)")
    print("   • Intelligent text truncation")
    print("   • Enhanced row styling and hover effects")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_improvements()
