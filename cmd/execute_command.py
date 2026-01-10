#!/usr/bin/env python3
"""
Command Executor CLI
Execute FQS commands from the terminal without launching the TUI

Usage:
    python execute_command.py "buy YES 0.65 100"
    python execute_command.py "orders list"
    python execute_command.py "positions show"
    python execute_command.py -h
"""
import sys
import argparse
import requests
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Default Flask server URL
DEFAULT_SERVER_URL = "http://localhost:5000"


class CommandExecutor:
    """Execute FQS commands via backend API"""
    
    def __init__(self, server_url: str = DEFAULT_SERVER_URL):
        self.server_url = server_url.rstrip('/')
        self.api_url = f"{self.server_url}/api/command"
    
    def execute(self, command: str, session: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a command via the API
        
        Args:
            command: Command string to execute
            session: Optional session context (e.g., token IDs)
        
        Returns:
            API response as dictionary
        """
        url = f"{self.api_url}/execute"
        
        payload = {
            "command": command,
            "origin": "cli"
        }
        
        if session:
            payload["session"] = session
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Connection failed",
                "message": f"Could not connect to server at {self.server_url}\n"
                          "Make sure the FQS backend is running:\n"
                          "  cd fqs && ./start_backend.sh"
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout",
                "message": "Command execution took too long (>30s)"
            }
        except requests.exceptions.HTTPError as e:
            try:
                error_data = e.response.json()
                return {
                    "success": False,
                    "error": f"HTTP {e.response.status_code}",
                    "message": error_data.get("message") or error_data.get("error", str(e))
                }
            except Exception:
                return {
                    "success": False,
                    "error": f"HTTP {e.response.status_code}",
                    "message": str(e)
                }
        except Exception as e:
            return {
                "success": False,
                "error": "Unexpected error",
                "message": str(e)
            }
    
    def get_help(self) -> Dict[str, Any]:
        """Get available commands and help text"""
        url = f"{self.api_url}/help"
        
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get command system status"""
        url = f"{self.api_url}/status"
        
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


def print_response(response: Dict[str, Any], verbose: bool = False):
    """Print command response in a formatted way"""
    if response.get("success"):
        print("✓ SUCCESS")
        print()
        print(response.get("message", "(no message)"))
        
        if verbose:
            print()
            print("─" * 60)
            print(f"Command: {response.get('command')}")
            print(f"Origin: {response.get('origin')}")
            print(f"Execution time: {response.get('execution_time_ms')} ms")
            if response.get("navigation"):
                print(f"Navigation: {response.get('navigation')}")
    else:
        print("✗ ERROR")
        print()
        error_msg = response.get("message") or response.get("error", "(unknown error)")
        print(error_msg)
        
        if verbose and "error" in response and response["error"] != response.get("message"):
            print()
            print(f"Error type: {response['error']}")


def main():
    parser = argparse.ArgumentParser(
        description="Execute FQS commands from the terminal",
        epilog="""
Examples:
  %(prog)s "buy YES 0.65 100"
  %(prog)s "orders list"
  %(prog)s "positions show"
  %(prog)s "balance"
  %(prog)s --help-commands
  %(prog)s --status
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        help="Command to execute (e.g., 'buy YES 0.65 100')"
    )
    
    parser.add_argument(
        "-s", "--server",
        default=DEFAULT_SERVER_URL,
        help=f"Server URL (default: {DEFAULT_SERVER_URL})"
    )
    
    parser.add_argument(
        "--session",
        type=json.loads,
        help="Session context as JSON (e.g., '{\"yes_token_id\": \"...\"}')"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output with execution details"
    )
    
    parser.add_argument(
        "--help-commands",
        action="store_true",
        help="Show available commands"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show command system status"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output response as JSON"
    )
    
    args = parser.parse_args()
    
    # Create executor
    executor = CommandExecutor(server_url=args.server)
    
    # Handle special flags
    if args.help_commands:
        response = executor.get_help()
        if args.json:
            print(json.dumps(response, indent=2))
        else:
            if response.get("success"):
                print("Available Commands:")
                print("=" * 60)
                for cmd in response.get("commands", []):
                    print(f"  {cmd}")
                print()
                print("For detailed help, run: help")
            else:
                print(f"Error: {response.get('error')}")
        return 0 if response.get("success") else 1
    
    if args.status:
        response = executor.get_status()
        if args.json:
            print(json.dumps(response, indent=2))
        else:
            if response.get("available"):
                print("Command System Status:")
                print("=" * 60)
                print(f"Available: ✓")
                print(f"Registered commands: {response.get('command_count', 0)}")
                print(f"Queue size: {response.get('queue_size', 0)}")
                print(f"Running: {response.get('running', False)}")
            else:
                print(f"Command system unavailable: {response.get('error')}")
        return 0 if response.get("available") else 1
    
    # Require command
    if not args.command:
        parser.print_help()
        print()
        print("Error: Command is required")
        print("Try: %(prog)s --help-commands" % {"prog": sys.argv[0]})
        return 1
    
    # Execute command
    response = executor.execute(args.command, session=args.session)
    
    if args.json:
        print(json.dumps(response, indent=2))
    else:
        print_response(response, verbose=args.verbose)
    
    return 0 if response.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
