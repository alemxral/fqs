#!/usr/bin/env python
"""
FQS Import Check Script
Tests all imports to ensure no ModuleNotFoundError
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("=" * 60)
print("FQS IMPORT VALIDATION CHECK")
print("=" * 60)
print()

errors = []
warnings = []

def test_import(module_name, description):
    """Test a single import"""
    try:
        __import__(module_name)
        print(f"✓ {description:40} OK")
        return True
    except ModuleNotFoundError as e:
        print(f"✗ {description:40} FAILED: {e}")
        errors.append((module_name, str(e)))
        return False
    except Exception as e:
        print(f"⚠ {description:40} WARNING: {e}")
        warnings.append((module_name, str(e)))
        return False

print("1. Core Modules")
print("-" * 60)
test_import("fqs", "FQS root package")
test_import("fqs.config.settings", "Settings configuration")
test_import("fqs.utils.logger", "Logger utilities")
test_import("fqs.core.core", "Core module")
test_import("fqs.core.websocket", "WebSocket core")
test_import("fqs.core.wallet", "Wallet core")
test_import("fqs.core.orders", "Orders core")
test_import("fqs.core.fetch", "Fetch manager")
print()

print("2. Managers")
print("-" * 60)
test_import("fqs.managers.commands_manager", "Commands manager")
test_import("fqs.managers.requests_manager", "Requests manager")
test_import("fqs.managers.navigation_manager", "Navigation manager")
test_import("fqs.managers.quickbuy_manager", "Quick buy manager")
print()

print("3. UI Components")
print("-" * 60)
test_import("fqs.ui.screens", "Screens package")
test_import("fqs.ui.screens.welcome_screen", "Welcome screen")
test_import("fqs.ui.screens.home_screen", "Home screen")
test_import("fqs.ui.screens.football_trade_screen", "Football trade screen")
test_import("fqs.ui.screens.settings_screen", "Settings screen")
test_import("fqs.ui.widgets.football_widget", "Football widget")
test_import("fqs.ui.widgets.orderbook", "Orderbook widget")
test_import("fqs.ui.widgets.command_input", "Command input widget")
print()

print("4. Server Components")
print("-" * 60)
test_import("fqs.server", "Server package")
test_import("fqs.server.api", "API blueprint")
print()

print("5. Client Libraries")
print("-" * 60)
test_import("fqs.client.clob_client", "CLOB client")
test_import("fqs.client.gamma_client", "Gamma client")
test_import("fqs.client.webscoket_client", "WebSocket client")
print()

print("6. External Dependencies")
print("-" * 60)
test_import("textual", "Textual framework")
test_import("flask", "Flask framework")
test_import("httpx", "HTTPX client")
test_import("websockets", "WebSockets library")
test_import("pandas", "Pandas library")
test_import("web3", "Web3 library")
print()

print("=" * 60)
print("SUMMARY")
print("=" * 60)
if not errors and not warnings:
    print("✓ All imports successful!")
    sys.exit(0)
else:
    if errors:
        print(f"✗ {len(errors)} critical errors:")
        for module, error in errors:
            print(f"  - {module}: {error}")
    if warnings:
        print(f"⚠ {len(warnings)} warnings:")
        for module, warning in warnings:
            print(f"  - {module}: {warning}")
    print()
    print("Fix these issues before running the application.")
    sys.exit(1)
