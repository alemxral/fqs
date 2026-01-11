"""
Test CommandInput Widget and CommandsManager Integration
Verify that commands are properly flowing through the system
"""
import asyncio
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from managers.commands_manager import CommandsManager


async def test_commands_manager():
    """Test that CommandsManager properly handles commands"""
    print("=" * 60)
    print("Testing CommandsManager Integration")
    print("=" * 60)
    
    # Create a commands manager
    manager = CommandsManager()
    
    # Start the manager
    await manager.start()
    print("✓ CommandsManager started")
    
    # Test 1: Submit a help command
    print("\n[Test 1] Submitting 'help' command...")
    future = await manager.submit(origin="Test", command="help")
    response = await future
    print(f"  Response: {response.message}")
    print(f"  Success: {response.success}")
    assert response.success, "Help command should succeed"
    print("✓ Help command works")
    
    # Test 2: Submit a hello command
    print("\n[Test 2] Submitting 'hello' command...")
    future = await manager.submit(origin="Test", command="hello")
    response = await future
    print(f"  Response: {response.message}")
    print(f"  Success: {response.success}")
    assert response.success, "Hello command should succeed"
    print("✓ Hello command works")
    
    # Test 3: Submit an unknown command
    print("\n[Test 3] Submitting 'unknowncommand' command...")
    future = await manager.submit(origin="Test", command="unknowncommand")
    response = await future
    print(f"  Response: {response.message}")
    print(f"  Success: {response.success}")
    assert not response.success, "Unknown command should fail"
    print("✓ Unknown command properly rejected")
    
    # Test 4: Test with subscriber
    print("\n[Test 4] Testing subscriber callback...")
    received_responses = []
    
    def subscriber_callback(resp):
        received_responses.append(resp)
        print(f"  Subscriber received: {resp.raw} -> {resp.message}")
    
    manager.subscribe(subscriber_callback)
    
    future = await manager.submit(origin="Test", command="status")
    response = await future
    
    # Wait a bit for subscriber
    await asyncio.sleep(0.1)
    
    assert len(received_responses) > 0, "Subscriber should receive responses"
    print(f"✓ Subscriber received {len(received_responses)} response(s)")
    
    # Test 5: List all registered handlers
    print("\n[Test 5] Listing all registered handlers...")
    handlers = list(manager._handlers.keys())
    print(f"  Registered commands: {', '.join(sorted(handlers))}")
    print(f"✓ Found {len(handlers)} registered handlers")
    
    # Stop the manager
    await manager.stop()
    print("\n✓ CommandsManager stopped")
    
    print("\n" + "=" * 60)
    print("All Tests Passed!")
    print("=" * 60)
    
    # Print available commands summary
    print("\n📖 Available Commands:")
    print("-" * 60)
    for cmd in sorted(handlers):
        print(f"  • {cmd}")
    print("-" * 60)


async def test_command_flow():
    """Test the full flow: CommandInput -> handle_command -> CommandsManager"""
    print("\n" + "=" * 60)
    print("Testing Command Flow")
    print("=" * 60)
    
    manager = CommandsManager()
    await manager.start()
    
    # Simulate what happens in screens
    async def mock_handle_command(command: str):
        """Simulates the handle_command method in screens"""
        print(f"\n[handle_command] Received: {command}")
        
        # This is what the screen does
        future = await manager.submit(origin="MockScreen", command=command)
        response = await future
        
        print(f"[handle_command] Response: {response.message}")
        print(f"[handle_command] Success: {response.success}")
        
        return response
    
    # Test commands
    test_commands = [
        "help",
        "balance",
        "markets",
        "buy YES 0.65 10",
        "invalid_command",
    ]
    
    for cmd in test_commands:
        print(f"\n→ Testing command: '{cmd}'")
        response = await mock_handle_command(cmd)
        status = "✓" if response.success else "✗"
        print(f"{status} Result: {response.message[:80]}")
    
    await manager.stop()
    print("\n" + "=" * 60)
    print("Command Flow Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    print("\n🔧 Command System Integration Test\n")
    
    # Run tests
    asyncio.run(test_commands_manager())
    asyncio.run(test_command_flow())
    
    print("\n✅ All integration tests passed!")
    print("\n💡 Command Input Widget should work correctly with these commands")
    print("   The widget calls handle_command() which submits to CommandsManager")
