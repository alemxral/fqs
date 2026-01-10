"""
Test Backend Commands and Functions
Tests all command handlers and utils integrations
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fqs.managers.commands_manager import CommandsManager, CommandRequest
from fqs.core.orders import OrdersCore
from fqs.core.wallet import WalletCore


class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def pass_test(self, name):
        self.passed += 1
        print(f"✅ {name}")
    
    def fail_test(self, name, error):
        self.failed += 1
        self.errors.append((name, error))
        print(f"❌ {name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print("\n" + "="*60)
        print(f"Test Results: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailed Tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        print("="*60)


async def test_orders_core():
    """Test OrdersCore initialization and methods"""
    results = TestResults()
    
    print("\n🧪 Testing OrdersCore...")
    print("-" * 60)
    
    try:
        orders = OrdersCore()
        results.pass_test("OrdersCore instantiation")
    except Exception as e:
        results.fail_test("OrdersCore instantiation", str(e))
        return results
    
    # Test initialize
    try:
        await orders.initialize()
        results.pass_test("OrdersCore.initialize()")
    except Exception as e:
        results.fail_test("OrdersCore.initialize()", str(e))
    
    # Test get_active_orders
    try:
        result = await orders.get_active_orders()
        if isinstance(result, dict) and "success" in result:
            results.pass_test("OrdersCore.get_active_orders()")
        else:
            results.fail_test("OrdersCore.get_active_orders()", "Invalid return format")
    except Exception as e:
        results.fail_test("OrdersCore.get_active_orders()", str(e))
    
    # Test get_orders_summary
    try:
        result = await orders.get_orders_summary()
        if isinstance(result, dict):
            results.pass_test("OrdersCore.get_orders_summary()")
        else:
            results.fail_test("OrdersCore.get_orders_summary()", "Invalid return format")
    except Exception as e:
        results.fail_test("OrdersCore.get_orders_summary()", str(e))
    
    return results


async def test_wallet_core():
    """Test WalletCore"""
    results = TestResults()
    
    print("\n🧪 Testing WalletCore...")
    print("-" * 60)
    
    try:
        wallet = WalletCore()
        results.pass_test("WalletCore instantiation")
    except Exception as e:
        results.fail_test("WalletCore instantiation", str(e))
        return results
    
    # Test initialize
    try:
        await wallet.initialize()
        results.pass_test("WalletCore.initialize()")
    except Exception as e:
        results.fail_test("WalletCore.initialize()", str(e))
    
    return results


async def test_commands_manager():
    """Test CommandsManager and command handlers"""
    results = TestResults()
    
    print("\n🧪 Testing CommandsManager...")
    print("-" * 60)
    
    try:
        manager = CommandsManager()
        results.pass_test("CommandsManager instantiation")
    except Exception as e:
        results.fail_test("CommandsManager instantiation", str(e))
        return results
    
    # Start the manager
    try:
        await manager.start()
        results.pass_test("CommandsManager.start()")
    except Exception as e:
        results.fail_test("CommandsManager.start()", str(e))
    
    # Test registered handlers
    handlers = manager.handlers
    expected_handlers = [
        "help", "exit", "hello", "ws", "status", "see", "refresh",
        "quickbuy", "buy", "sell", "balance", "score", "time",
        "markets", "orders", "positions", "trades"
    ]
    
    for handler_name in expected_handlers:
        if handler_name in handlers:
            results.pass_test(f"Handler registered: {handler_name}")
        else:
            results.fail_test(f"Handler registered: {handler_name}", "Not found")
    
    # Test help command
    try:
        req = CommandRequest(origin="test", command="help")
        future = await manager.submit("test", "help")
        response = await asyncio.wait_for(future, timeout=5.0)
        if response.success:
            results.pass_test("Command: help")
        else:
            results.fail_test("Command: help", "Command failed")
    except Exception as e:
        results.fail_test("Command: help", str(e))
    
    # Test markets command
    try:
        future = await manager.submit("test", "markets")
        response = await asyncio.wait_for(future, timeout=10.0)
        results.pass_test("Command: markets")
    except Exception as e:
        results.fail_test("Command: markets", str(e))
    
    # Test orders command
    try:
        future = await manager.submit("test", "orders")
        response = await asyncio.wait_for(future, timeout=10.0)
        results.pass_test("Command: orders")
    except Exception as e:
        results.fail_test("Command: orders", str(e))
    
    # Test positions command
    try:
        future = await manager.submit("test", "positions")
        response = await asyncio.wait_for(future, timeout=10.0)
        results.pass_test("Command: positions")
    except Exception as e:
        results.fail_test("Command: positions", str(e))
    
    # Test trades command
    try:
        future = await manager.submit("test", "trades")
        response = await asyncio.wait_for(future, timeout=10.0)
        results.pass_test("Command: trades")
    except Exception as e:
        results.fail_test("Command: trades", str(e))
    
    # Stop the manager
    try:
        await manager.stop()
        results.pass_test("CommandsManager.stop()")
    except Exception as e:
        results.fail_test("CommandsManager.stop()", str(e))
    
    return results


async def test_widgets():
    """Test widget imports"""
    results = TestResults()
    
    print("\n🧪 Testing Widget Imports...")
    print("-" * 60)
    
    widgets = [
        ("OpenOrdersWidget", "fqs.ui.widgets.open_orders"),
        ("PriceTickerWidget", "fqs.ui.widgets.price_ticker"),
        ("TradeHistoryWidget", "fqs.ui.widgets.trade_history"),
        ("PositionSummaryWidget", "fqs.ui.widgets.position_summary"),
    ]
    
    for widget_name, module_path in widgets:
        try:
            module = __import__(module_path, fromlist=[widget_name])
            widget_class = getattr(module, widget_name)
            results.pass_test(f"Import: {widget_name}")
        except Exception as e:
            results.fail_test(f"Import: {widget_name}", str(e))
    
    return results


async def test_utils_integration():
    """Test that utils functions are accessible"""
    results = TestResults()
    
    print("\n🧪 Testing Utils Integration...")
    print("-" * 60)
    
    # Test trading utils
    trading_utils = [
        "fqs.utils.trading.create_order",
        "fqs.utils.trading.buy",
        "fqs.utils.trading.sell",
        "fqs.utils.trading.cancel_order",
        "fqs.utils.trading.get_orders",
        "fqs.utils.trading.create_limit_order",
    ]
    
    for util_path in trading_utils:
        try:
            __import__(util_path)
            results.pass_test(f"Import: {util_path}")
        except Exception as e:
            results.fail_test(f"Import: {util_path}", str(e))
    
    # Test market utils
    market_utils = [
        "fqs.utils.market.get_orderbook",
        "fqs.utils.market.get_spreads",
        "fqs.utils.market.market_search",
    ]
    
    for util_path in market_utils:
        try:
            __import__(util_path)
            results.pass_test(f"Import: {util_path}")
        except Exception as e:
            results.fail_test(f"Import: {util_path}", str(e))
    
    return results


async def main():
    """Run all tests"""
    print("="*60)
    print("🚀 FQS Backend Test Suite")
    print("="*60)
    
    all_results = TestResults()
    
    # Run all test suites
    test_suites = [
        test_widgets(),
        test_utils_integration(),
        test_orders_core(),
        test_wallet_core(),
        test_commands_manager(),
    ]
    
    for test_coro in test_suites:
        try:
            results = await test_coro
            all_results.passed += results.passed
            all_results.failed += results.failed
            all_results.errors.extend(results.errors)
        except Exception as e:
            print(f"\n❌ Test suite failed: {e}")
            all_results.failed += 1
            all_results.errors.append(("Test suite", str(e)))
    
    # Print final summary
    all_results.summary()
    
    return all_results.failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
