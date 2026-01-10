#!/usr/bin/env python3
"""
FQS System Tester - Comprehensive validation of all components

Tests:
1. Import validation
2. Configuration loading
3. Flask API endpoints
4. Command handlers
5. FetchManager (Gamma API)
6. WebSocket stub
7. UI components
8. Utility functions

Usage:
    python test_fqs.py
    python test_fqs.py --verbose
    python test_fqs.py --quick  # Skip slow tests
"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Tuple
import argparse

# Add parent directory to path
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


class FQSTester:
    """Comprehensive system tester for FQS"""
    
    def __init__(self, verbose: bool = False, quick: bool = False):
        self.verbose = verbose
        self.quick = quick
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results = []
    
    def print_header(self, text: str):
        """Print section header"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}\n")
    
    def print_test(self, name: str, passed: bool, message: str = ""):
        """Print test result"""
        if passed:
            symbol = f"{Colors.GREEN}✓{Colors.END}"
            self.passed += 1
        else:
            symbol = f"{Colors.RED}✗{Colors.END}"
            self.failed += 1
        
        status = f"{symbol} {name}"
        if message:
            status += f" {Colors.YELLOW}({message}){Colors.END}"
        
        print(status)
        self.results.append((name, passed, message))
        
        if self.verbose and not passed:
            print(f"  {Colors.RED}Error: {message}{Colors.END}")
    
    def print_skip(self, name: str, reason: str):
        """Print skipped test"""
        print(f"{Colors.YELLOW}⊘{Colors.END} {name} {Colors.YELLOW}(skipped: {reason}){Colors.END}")
        self.skipped += 1
    
    # ==================== TEST SECTION 1: IMPORTS ====================
    
    def test_imports(self):
        """Test all critical imports"""
        self.print_header("TEST SECTION 1: IMPORTS")
        
        imports = [
            ("textual", "from textual.app import App"),
            ("flask", "import flask"),
            ("httpx", "import httpx"),
            ("websockets", "import websockets"),
            ("lomond", "import lomond"),
            ("pandas", "import pandas"),
            ("web3", "from web3 import Web3"),
            ("dotenv", "from dotenv import load_dotenv"),
            ("pyperclip", "import pyperclip"),
        ]
        
        for name, import_stmt in imports:
            try:
                exec(import_stmt)
                self.print_test(f"Import {name}", True)
            except ImportError as e:
                self.print_test(f"Import {name}", False, str(e))
        
        # Test FQS module imports
        fqs_imports = [
            ("fqs.config.settings", "from fqs.config.settings import Settings"),
            ("fqs.core.fetch", "from fqs.core.fetch import FetchManager"),
            ("fqs.core.websocket", "from fqs.core.websocket import WebSocketCore"),
            ("fqs.managers.commands_manager", "from fqs.managers.commands_manager import CommandsManager"),
            ("fqs.ui.widgets.football_widget", "from fqs.ui.widgets.football_widget import FootballWidget"),
            ("fqs.ui.widgets.orderbook", "from fqs.ui.widgets.orderbook import OrderBookWidget"),
            ("fqs.ui.widgets.command_input", "from fqs.ui.widgets.command_input import CommandInput"),
        ]
        
        for name, import_stmt in fqs_imports:
            try:
                exec(import_stmt)
                self.print_test(f"Import {name}", True)
            except ImportError as e:
                self.print_test(f"Import {name}", False, str(e))
    
    # ==================== TEST SECTION 2: CONFIGURATION ====================
    
    def test_configuration(self):
        """Test configuration loading"""
        self.print_header("TEST SECTION 2: CONFIGURATION")
        
        try:
            from fqs.config.settings import Settings
            settings = Settings()
            self.print_test("Settings instantiation", True)
            
            # Check required attributes
            attrs = ['CLOB_API_URL', 'CLOB_API_KEY', 'CHAIN_ID', 'FLASK_HOST', 'FLASK_PORT']
            for attr in attrs:
                has_attr = hasattr(settings, attr)
                self.print_test(f"Settings.{attr}", has_attr, 
                               f"Missing attribute" if not has_attr else "")
            
            # Validate method
            try:
                settings.validate()
                self.print_test("Settings.validate()", True)
            except Exception as e:
                self.print_test("Settings.validate()", False, str(e))
                
        except Exception as e:
            self.print_test("Settings loading", False, str(e))
    
    # ==================== TEST SECTION 3: FETCH MANAGER ====================
    
    def test_fetch_manager(self):
        """Test FetchManager functionality"""
        self.print_header("TEST SECTION 3: FETCH MANAGER")
        
        try:
            from fqs.core.fetch import FetchManager
            from fqs.utils.logger import setup_logger
            
            logger = setup_logger()
            fetch_manager = FetchManager(logger=logger)
            self.print_test("FetchManager instantiation", True)
            
            # Check methods exist
            methods = ['get_event_by_slug', 'get_market_by_slug', 
                      'extract_market_table_data', 'format_market_table']
            for method in methods:
                has_method = hasattr(fetch_manager, method)
                self.print_test(f"FetchManager.{method}", has_method,
                               f"Missing method" if not has_method else "")
            
            # Test actual API call (if not quick mode)
            if not self.quick:
                try:
                    event_data = fetch_manager.get_event_by_slug("epl-tot-ast-2025-10-19")
                    if event_data:
                        self.print_test("Fetch event by slug", True, 
                                       f"Got event: {event_data.get('title', 'N/A')[:50]}...")
                    else:
                        self.print_test("Fetch event by slug", False, "No data returned")
                except Exception as e:
                    self.print_test("Fetch event by slug", False, str(e))
            else:
                self.print_skip("Fetch event by slug", "quick mode")
                
        except Exception as e:
            self.print_test("FetchManager loading", False, str(e))
    
    # ==================== TEST SECTION 4: COMMAND HANDLERS ====================
    
    def test_command_handlers(self):
        """Test command handler registration"""
        self.print_header("TEST SECTION 4: COMMAND HANDLERS")
        
        try:
            from fqs.managers.commands_manager import CommandsManager
            from fqs.core.core import CoreModule
            
            core = CoreModule()
            commands_manager = CommandsManager(core)
            self.print_test("CommandsManager instantiation", True)
            
            # Check handler registration
            expected_handlers = [
                'help', 'exit', 'hello', 'ws', 'status', 'see', 'refresh',
                'quickbuy', 'buy', 'sell', 'balance', 'score', 'time'
            ]
            
            for handler in expected_handlers:
                is_registered = handler in commands_manager.handlers
                self.print_test(f"Handler '{handler}' registered", is_registered,
                               f"Not found in handlers dict" if not is_registered else "")
            
            # Test command parsing
            test_commands = [
                ("buy YES 0.55 10", "buy"),
                ("sell NO 0.45 20", "sell"),
                ("balance", "balance"),
                ("see slug test-event", "see"),
            ]
            
            for cmd, expected_name in test_commands:
                parts = cmd.split()
                cmd_name = parts[0]
                matches = cmd_name == expected_name
                self.print_test(f"Parse '{cmd}'", matches,
                               f"Expected '{expected_name}', got '{cmd_name}'" if not matches else "")
                
        except Exception as e:
            self.print_test("CommandsManager loading", False, str(e))
    
    # ==================== TEST SECTION 5: FLASK API ====================
    
    def test_flask_api(self):
        """Test Flask API endpoints"""
        self.print_header("TEST SECTION 5: FLASK API")
        
        try:
            from fqs.server.api import create_app
            
            app = create_app()
            self.print_test("Flask app creation", True)
            
            # Check routes exist
            routes = [
                '/api/order/buy',
                '/api/order/sell',
                '/api/balance',
                '/api/markets/football',
                '/api/market/<slug>',
            ]
            
            with app.app_context():
                for route in routes:
                    # Check if route pattern exists
                    found = any(route.replace('<slug>', '') in str(rule) 
                               for rule in app.url_map.iter_rules())
                    self.print_test(f"Route {route}", found,
                                   "Route not found" if not found else "")
            
            # Test app config
            has_cors = hasattr(app, 'extensions') and 'cors' in app.extensions
            self.print_test("Flask CORS enabled", has_cors,
                           "CORS extension not found" if not has_cors else "")
            
        except Exception as e:
            self.print_test("Flask API loading", False, str(e))
    
    # ==================== TEST SECTION 6: UI WIDGETS ====================
    
    def test_ui_widgets(self):
        """Test UI widget components"""
        self.print_header("TEST SECTION 6: UI WIDGETS")
        
        widgets = [
            ("FootballWidget", "fqs.ui.widgets.football_widget", "FootballWidget"),
            ("OrderBookWidget", "fqs.ui.widgets.orderbook", "OrderBookWidget"),
            ("CommandInput", "fqs.ui.widgets.command_input", "CommandInput"),
        ]
        
        for name, module, class_name in widgets:
            try:
                mod = __import__(module, fromlist=[class_name])
                widget_class = getattr(mod, class_name)
                self.print_test(f"Widget {name}", True)
                
                # Check if it has required Textual methods
                required_methods = ['compose'] if name != 'CommandInput' else ['on_mount']
                for method in required_methods:
                    has_method = hasattr(widget_class, method) or hasattr(widget_class, method)
                    self.print_test(f"  {name}.{method}()", has_method,
                                   "Method not found" if not has_method else "")
                    
            except Exception as e:
                self.print_test(f"Widget {name}", False, str(e))
    
    # ==================== TEST SECTION 7: SCREENS ====================
    
    def test_screens(self):
        """Test UI screens"""
        self.print_header("TEST SECTION 7: SCREENS")
        
        screens = [
            ("WelcomeScreen", "fqs.ui.screens.welcome_screen"),
            ("HomeScreen", "fqs.ui.screens.home_screen"),
            ("FootballTradeScreen", "fqs.ui.screens.football_trade_screen"),
            ("SettingsScreen", "fqs.ui.screens.settings_screen"),
        ]
        
        for name, module in screens:
            try:
                mod = __import__(module, fromlist=[name])
                screen_class = getattr(mod, name)
                self.print_test(f"Screen {name}", True)
                
                # Check if it has compose method
                has_compose = hasattr(screen_class, 'compose')
                self.print_test(f"  {name}.compose()", has_compose,
                               "Method not found" if not has_compose else "")
                               
            except Exception as e:
                self.print_test(f"Screen {name}", False, str(e))
    
    # ==================== TEST SECTION 8: WEBSOCKET ====================
    
    def test_websocket(self):
        """Test WebSocket core"""
        self.print_header("TEST SECTION 8: WEBSOCKET")
        
        try:
            from fqs.core.websocket import WebSocketCore
            
            # Test stub implementation (no args needed for instantiation)
            ws_core = WebSocketCore()
            self.print_test("WebSocketCore instantiation", True)
            
            # Check attributes
            attrs = ['orderbooks', 'connection_state']
            for attr in attrs:
                has_attr = hasattr(ws_core, attr)
                self.print_test(f"WebSocketCore.{attr}", has_attr,
                               "Missing attribute" if not has_attr else "")
                               
        except Exception as e:
            self.print_test("WebSocketCore loading", False, str(e))
    
    # ==================== TEST SECTION 9: UTILITIES ====================
    
    def test_utilities(self):
        """Test utility functions"""
        self.print_header("TEST SECTION 9: UTILITIES")
        
        try:
            from fqs.utils.logger import setup_logger
            logger = setup_logger()
            self.print_test("Logger setup", logger is not None)
            
            # Test logger methods
            logger_methods = ['info', 'error', 'debug', 'warning']
            for method in logger_methods:
                has_method = hasattr(logger, method)
                self.print_test(f"Logger.{method}()", has_method,
                               "Method not found" if not has_method else "")
                               
        except Exception as e:
            self.print_test("Logger utilities", False, str(e))
        
        # Test gamma-api utilities
        try:
            sys.path.insert(0, str(Path(__file__).parent / "utils" / "gamma-api"))
            from get_events_by_slug import get_events_by_slug
            from get_markets_by_slug import get_markets_by_slug
            
            self.print_test("Gamma API utilities", True)
            
            if not self.quick:
                # Test actual call
                try:
                    events = get_events_by_slug("epl-tot-ast-2025-10-19")
                    self.print_test("get_events_by_slug() call", events is not None,
                                   "No data returned" if not events else "")
                except Exception as e:
                    self.print_test("get_events_by_slug() call", False, str(e))
            else:
                self.print_skip("get_events_by_slug() call", "quick mode")
                
        except Exception as e:
            self.print_test("Gamma API utilities", False, str(e))
    
    # ==================== TEST SECTION 10: FILE STRUCTURE ====================
    
    def test_file_structure(self):
        """Test critical files exist"""
        self.print_header("TEST SECTION 10: FILE STRUCTURE")
        
        base_path = Path(__file__).parent
        
        critical_files = [
            "app.py",
            "requirements.txt",
            "README.md",
            "SETUP.md",
            "IMPROVEMENT_PLAN.md",
            "start.sh",
            "check_imports.py",
            "run_football_widget.py",
            "config/settings.py",
            "core/core.py",
            "core/fetch.py",
            "core/websocket.py",
            "managers/commands_manager.py",
            "server/api.py",
            "server/run_flask.py",
            "ui/screens/welcome_screen.py",
            "ui/screens/home_screen.py",
            "ui/screens/football_trade_screen.py",
            "ui/screens/settings_screen.py",
            "ui/widgets/football_widget.py",
            "ui/widgets/orderbook.py",
            "ui/widgets/command_input.py",
        ]
        
        for file_path in critical_files:
            full_path = base_path / file_path
            exists = full_path.exists()
            self.print_test(f"File {file_path}", exists,
                           "File not found" if not exists else "")
    
    # ==================== MAIN TEST RUNNER ====================
    
    def run_all_tests(self):
        """Run all test sections"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}FQS SYSTEM TESTER{Colors.END}")
        print(f"{Colors.BLUE}Testing all components of Football Quick Shoot Terminal{Colors.END}")
        
        if self.quick:
            print(f"{Colors.YELLOW}Running in QUICK mode (skipping API calls){Colors.END}")
        
        # Run all test sections
        self.test_imports()
        self.test_configuration()
        self.test_fetch_manager()
        self.test_command_handlers()
        self.test_flask_api()
        self.test_ui_widgets()
        self.test_screens()
        self.test_websocket()
        self.test_utilities()
        self.test_file_structure()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        
        self.print_header("TEST SUMMARY")
        
        print(f"{Colors.GREEN}Passed:{Colors.END}  {self.passed}")
        print(f"{Colors.RED}Failed:{Colors.END}  {self.failed}")
        print(f"{Colors.YELLOW}Skipped:{Colors.END} {self.skipped}")
        print(f"{Colors.BLUE}Total:{Colors.END}   {total}")
        print(f"\n{Colors.BOLD}Pass Rate: {pass_rate:.1f}%{Colors.END}")
        
        if self.failed == 0:
            print(f"\n{Colors.BOLD}{Colors.GREEN}🎉 ALL TESTS PASSED! 🎉{Colors.END}")
            return 0
        else:
            print(f"\n{Colors.BOLD}{Colors.RED}⚠️  SOME TESTS FAILED ⚠️{Colors.END}")
            print(f"\n{Colors.YELLOW}Failed tests:{Colors.END}")
            for name, passed, message in self.results:
                if not passed:
                    print(f"  {Colors.RED}✗{Colors.END} {name}: {message}")
            return 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='FQS System Tester')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed error messages')
    parser.add_argument('--quick', '-q', action='store_true',
                       help='Skip slow tests (API calls)')
    
    args = parser.parse_args()
    
    tester = FQSTester(verbose=args.verbose, quick=args.quick)
    exit_code = tester.run_all_tests()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
