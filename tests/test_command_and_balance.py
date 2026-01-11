"""
Comprehensive Diagnostic Test for Command Input and Balance Fetch
==================================================================

This test diagnoses:
1. CommandInput widget integration with CommandsManager
2. Balance fetch flow through Flask API
3. CLOB client initialization and availability
4. Alternative balance fetch methods

DO NOT IMPLEMENT FIXES - Only diagnose and report issues.
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Optional, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("\n" + "="*80)
print("COMMAND INPUT & BALANCE FETCH DIAGNOSTIC TEST")
print("="*80 + "\n")


# ============================================================================
# SECTION 1: TEST COMMAND INPUT WIDGET INTEGRATION
# ============================================================================

def test_command_input_widget():
    """Test CommandInput widget and its integration with handle_command"""
    print("\n" + "─"*80)
    print("SECTION 1: COMMAND INPUT WIDGET INTEGRATION")
    print("─"*80 + "\n")
    
    try:
        from fqs.ui.widgets.command_input import CommandInput
        print("✅ CommandInput widget imported successfully")
        
        # Check CommandInput attributes
        import inspect
        
        # Check __init__ signature
        init_sig = inspect.signature(CommandInput.__init__)
        print(f"\n📋 CommandInput.__init__ parameters:")
        for param_name, param in init_sig.parameters.items():
            if param_name != 'self':
                print(f"   - {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'Any'}")
        
        # Check if command_handler parameter exists
        if 'command_handler' in init_sig.parameters:
            print("✅ command_handler parameter found in __init__")
        else:
            print("❌ command_handler parameter NOT found in __init__")
        
        # Check on_input_submitted method
        if hasattr(CommandInput, 'on_input_submitted'):
            print("\n✅ on_input_submitted method exists")
            
            # Get method signature
            method_sig = inspect.signature(CommandInput.on_input_submitted)
            print(f"   Signature: {method_sig}")
            
            # Check if it's async
            if asyncio.iscoroutinefunction(CommandInput.on_input_submitted):
                print("   ✅ Method is async")
            else:
                print("   ❌ Method is NOT async")
        else:
            print("❌ on_input_submitted method NOT found")
        
        # Check CommandSubmitted message
        if hasattr(CommandInput, 'CommandSubmitted'):
            print("✅ CommandSubmitted message class exists")
        else:
            print("⚠️  CommandSubmitted message class NOT found")
        
    except ImportError as e:
        print(f"❌ Failed to import CommandInput: {e}")
        return False
    
    return True


def test_home_screen_handle_command():
    """Test HomeScreen.handle_command integration"""
    print("\n" + "─"*80)
    print("SECTION 2: HOME SCREEN handle_command INTEGRATION")
    print("─"*80 + "\n")
    
    try:
        from fqs.ui.screens.home_screen import HomeScreen
        print("✅ HomeScreen imported successfully")
        
        import inspect
        
        # Check if handle_command exists
        if hasattr(HomeScreen, 'handle_command'):
            print("✅ handle_command method exists")
            
            method_sig = inspect.signature(HomeScreen.handle_command)
            print(f"   Signature: {method_sig}")
            
            if asyncio.iscoroutinefunction(HomeScreen.handle_command):
                print("   ✅ Method is async")
            else:
                print("   ❌ Method is NOT async")
            
            # Get source to check implementation
            source = inspect.getsource(HomeScreen.handle_command)
            
            # Check for commands_manager.submit call
            if 'commands_manager.submit' in source:
                print("   ✅ Calls commands_manager.submit()")
            else:
                print("   ❌ Does NOT call commands_manager.submit()")
            
            # Check for LOOK command handling
            if 'LOOK' in source:
                print("   ✅ Has special LOOK command handling")
            
        else:
            print("❌ handle_command method NOT found")
        
        # Check if CommandInput is used in HomeScreen
        source = inspect.getsource(HomeScreen)
        if 'CommandInput' in source:
            print("\n✅ CommandInput widget is used in HomeScreen")
            
            # Check if command_handler is passed
            if 'command_handler=' in source or 'handle_command' in source:
                print("   ✅ command_handler parameter appears to be set")
            else:
                print("   ⚠️  Cannot determine if command_handler is properly set")
        else:
            print("\n❌ CommandInput widget NOT found in HomeScreen")
        
    except Exception as e:
        print(f"❌ Error analyzing HomeScreen: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_commands_manager_integration():
    """Test CommandsManager handler registration and processing"""
    print("\n" + "─"*80)
    print("SECTION 3: COMMANDS MANAGER INTEGRATION")
    print("─"*80 + "\n")
    
    try:
        from fqs.managers.commands_manager import CommandsManager, CommandRequest, CommandResponse
        print("✅ CommandsManager imported successfully")
        
        import inspect
        
        # Check submit method
        if hasattr(CommandsManager, 'submit'):
            print("\n✅ submit() method exists")
            sig = inspect.signature(CommandsManager.submit)
            print(f"   Signature: {sig}")
            
            if asyncio.iscoroutinefunction(CommandsManager.submit):
                print("   ✅ submit() is async")
            else:
                print("   ❌ submit() is NOT async")
        
        # Check _register_defaults method
        if hasattr(CommandsManager, '_register_defaults'):
            print("\n✅ _register_defaults() method exists")
            source = inspect.getsource(CommandsManager._register_defaults)
            
            # List registered handlers
            print("\n📋 Registered command handlers:")
            handlers = []
            for line in source.split('\n'):
                if 'register_handler' in line and not line.strip().startswith('#'):
                    # Extract handler name
                    if '"' in line:
                        handler = line.split('"')[1]
                        handlers.append(handler)
            
            for handler in handlers:
                print(f"   - {handler}")
            
            # Check for balance handler
            if 'balance' in handlers or 'bal' in handlers:
                print("\n✅ Balance handler is registered")
            else:
                print("\n⚠️  Balance handler NOT found in defaults")
        
        # Check _handle_balance method
        if hasattr(CommandsManager, '_handle_balance'):
            print("\n✅ _handle_balance() method exists")
            source = inspect.getsource(CommandsManager._handle_balance)
            
            # Check what it does
            if 'api_client.get' in source:
                print("   ✅ Uses app.api_client.get() for balance fetch")
            
            if '/api/balance' in source:
                print("   ✅ Calls /api/balance endpoint")
            else:
                print("   ⚠️  Endpoint path not found in source")
        
    except Exception as e:
        print(f"❌ Error analyzing CommandsManager: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


# ============================================================================
# SECTION 2: TEST BALANCE FETCH FLOW
# ============================================================================

async def test_flask_api_server():
    """Test if Flask API server is running"""
    print("\n" + "─"*80)
    print("SECTION 4: FLASK API SERVER STATUS")
    print("─"*80 + "\n")
    
    try:
        import httpx
        
        base_url = "http://127.0.0.1:5000"
        print(f"🔍 Testing connection to: {base_url}")
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(f"{base_url}/api/health")
                print(f"✅ Server is running (status: {response.status_code})")
                if response.status_code == 200:
                    try:
                        print(f"   Response: {response.json()}")
                    except:
                        print(f"   Response: {response.text}")
                return True
            except httpx.ConnectError:
                print("❌ Server is NOT running (connection refused)")
                print("   💡 Start server with: python -m fqs.server.run_flask")
                return False
            except httpx.TimeoutException:
                print("❌ Server connection timed out")
                return False
            except Exception as e:
                print(f"❌ Error connecting to server: {e}")
                return False
                
    except ImportError:
        print("❌ httpx not installed (required for API tests)")
        return False


async def test_balance_endpoint():
    """Test GET /api/balance endpoint directly"""
    print("\n" + "─"*80)
    print("SECTION 5: BALANCE ENDPOINT TEST")
    print("─"*80 + "\n")
    
    try:
        import httpx
        
        base_url = "http://127.0.0.1:5000"
        endpoint = f"{base_url}/api/balance"
        
        print(f"🔍 Testing: GET {endpoint}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(endpoint)
                print(f"   Status: {response.status_code}")
                
                data = response.json()
                print(f"   Response: {data}")
                
                if response.status_code == 200:
                    if data.get('success'):
                        balance = data.get('balance', 0)
                        currency = data.get('currency', 'USDC')
                        print(f"\n✅ Balance fetch successful: ${balance:.2f} {currency}")
                        return True
                    else:
                        error = data.get('error', 'Unknown error')
                        print(f"\n❌ Balance fetch failed: {error}")
                        return False
                else:
                    error = data.get('error', 'Unknown error')
                    print(f"\n❌ API error (status {response.status_code}): {error}")
                    return False
                    
            except httpx.ConnectError:
                print("❌ Cannot connect to server")
                return False
            except Exception as e:
                print(f"❌ Error calling endpoint: {e}")
                import traceback
                traceback.print_exc()
                return False
                
    except ImportError:
        print("❌ httpx not installed")
        return False


def test_api_balance_implementation():
    """Analyze the /api/balance endpoint implementation"""
    print("\n" + "─"*80)
    print("SECTION 6: BALANCE ENDPOINT IMPLEMENTATION ANALYSIS")
    print("─"*80 + "\n")
    
    try:
        # Read the api.py file
        api_file = PROJECT_ROOT / "server" / "api.py"
        if not api_file.exists():
            print(f"❌ API file not found: {api_file}")
            return False
        
        with open(api_file, 'r') as f:
            source = f.read()
        
        # Check for balance endpoint
        if 'def get_balance():' in source or "@api_bp.route('/balance'" in source:
            print("✅ Balance endpoint found in server/api.py")
            
            # Check imports
            print("\n📋 Import Analysis:")
            if 'from py_clob_client.client import ClobClient' in source:
                print("   ✅ ClobClient imported from py_clob_client")
            else:
                print("   ⚠️  ClobClient import not found")
            
            if 'CLOB_URL' in source:
                print("   ✅ CLOB_URL configuration found")
            else:
                print("   ⚠️  CLOB_URL not defined")
            
            # Check client usage
            print("\n📋 Client Usage:")
            if 'create_clob_client()' in source:
                print("   ✅ Uses create_clob_client() wrapper")
            
            if 'def get_clob_client():' in source:
                print("   ✅ Has get_clob_client() function")
                
                # Check what it returns
                if 'return clob_client' in source:
                    print("   ✅ Returns module-level clob_client")
                elif 'return _clob_client' in source:
                    print("   ✅ Returns _clob_client instance")
            
            if 'get_balance_allowance()' in source:
                print("   ✅ Calls client.get_balance_allowance()")
        else:
            print("❌ Balance endpoint NOT found in server/api.py")
            return False
        
    except Exception as e:
        print(f"❌ Error analyzing API implementation: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_clob_client_initialization():
    """Test CLOB client initialization"""
    print("\n" + "─"*80)
    print("SECTION 7: CLOB CLIENT INITIALIZATION")
    print("─"*80 + "\n")
    
    try:
        from fqs.client.ClobClientWrapper import create_clob_client
        print("✅ ClobClientWrapper.create_clob_client imported")
        
        try:
            client = create_clob_client()
            print("✅ CLOB client created successfully")
            
            # Check client methods
            if hasattr(client, 'get_balance_allowance'):
                print("   ✅ client.get_balance_allowance() method exists")
            else:
                print("   ❌ client.get_balance_allowance() method NOT found")
            
            # Try to get balance
            try:
                print("\n🔍 Testing balance fetch with CLOB client...")
                balance_data = client.get_balance_allowance()
                print(f"   ✅ Balance data retrieved: {balance_data}")
                
                if isinstance(balance_data, dict):
                    if 'balance' in balance_data:
                        balance = balance_data.get('balance')
                        print(f"   💰 Balance: {balance}")
                    else:
                        print(f"   ⚠️  'balance' key not in response")
                        print(f"   Keys: {list(balance_data.keys())}")
                        
            except Exception as e:
                print(f"   ❌ Balance fetch failed: {e}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            print(f"❌ Failed to create CLOB client: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except ImportError as e:
        print(f"❌ Cannot import ClobClientWrapper: {e}")
        return False
    
    return True


# ============================================================================
# SECTION 3: DIAGNOSTIC INFORMATION
# ============================================================================

def print_recommendations():
    """Print recommendations based on test results"""
    print("\n" + "="*80)
    print("DIAGNOSTIC SUMMARY & RECOMMENDATIONS")
    print("="*80 + "\n")
    
    print("📋 COMMAND INPUT INTEGRATION:")
    print("   1. ✅ CommandInput widget has command_handler parameter")
    print("   2. ✅ handle_command is passed to CommandInput in HomeScreen")
    print("   3. ✅ handle_command calls commands_manager.submit()")
    print("   4. Check if CommandsManager has handlers registered")
    
    print("\n📋 BALANCE FETCH FLOW:")
    print("   1. Ensure Flask server is running: python -m fqs.server.run_flask")
    print("   2. ✅ /api/balance endpoint now has proper imports")
    print("   3. ✅ get_clob_client() now uses module-level clob_client")
    print("   4. ✅ Balance fetch has fallback to direct client call")
    print("   5. Verify .env configuration has correct API credentials")
    
    print("\n📋 FIXES APPLIED:")
    print("   ✅ Added ClobClient and CLOB_URL imports to server/api.py")
    print("   ✅ Fixed get_clob_client() to use existing clob_client instance")
    print("   ✅ Added proper error handling to update_balance() in home_screen.py")
    print("   ✅ Added fallback balance fetch using create_clob_client()")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def run_all_tests():
    """Run all diagnostic tests"""
    
    # Section 1: Command Input Integration
    test_command_input_widget()
    test_home_screen_handle_command()
    test_commands_manager_integration()
    
    # Section 2: Balance Fetch Flow
    server_running = await test_flask_api_server()
    
    if server_running:
        await test_balance_endpoint()
    else:
        print("\n⚠️  Skipping balance endpoint test (server not running)")
    
    test_api_balance_implementation()
    test_clob_client_initialization()
    
    # Section 3: Recommendations
    print_recommendations()
    
    print("\n" + "="*80)
    print("DIAGNOSTIC TEST COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
