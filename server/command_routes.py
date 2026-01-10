"""
Command Execution Routes
Provides HTTP API endpoints for executing commands outside the TUI
"""
import sys
from pathlib import Path
from flask import Blueprint, jsonify, request
from datetime import datetime
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Create Blueprint
command_bp = Blueprint('command', __name__, url_prefix='/api/command')

# Global reference to the app's command manager (will be set by server)
_command_manager = None
_manager_loop = None
_executor = ThreadPoolExecutor(max_workers=4)


def set_command_manager(manager, loop=None):
    """Set the command manager instance from the main app"""
    global _command_manager, _manager_loop
    _command_manager = manager
    _manager_loop = loop


@command_bp.route('/execute', methods=['POST'])
def execute_command():
    """
    Execute a command via HTTP API
    
    Request body:
        {
            "command": "buy YES 0.65 100",
            "session": {
                "yes_token_id": "...",
                "no_token_id": "...",
                ...
            },
            "origin": "cli"  # optional, defaults to "api"
        }
    
    Response:
        {
            "success": true/false,
            "message": "Command result message",
            "navigation": null or "screen_name",
            "command": "original command",
            "timestamp": "ISO timestamp",
            "execution_time_ms": 123
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body required'
            }), 400
        
        command = data.get('command')
        if not command:
            return jsonify({
                'success': False,
                'error': 'Missing required field: command'
            }), 400
        
        session = data.get('session', {})
        origin = data.get('origin', 'api')
        
        # Check if command manager is available
        if not _command_manager:
            return jsonify({
                'success': False,
                'error': 'Command manager not initialized',
                'message': 'The server is not running with a command manager context'
            }), 503
        
        # Execute command using the command manager
        start_time = datetime.utcnow()
        
        try:
            # Check if we have the manager's event loop
            if not _manager_loop:
                return jsonify({
                    'success': False,
                    'error': 'Event loop not available',
                    'message': 'Command manager event loop was not initialized properly'
                }), 503
            
            # Execute command in the manager's event loop thread-safely
            async def _execute():
                """Run command in the manager's event loop"""
                # Submit command and get future
                response_future = await _command_manager.submit(
                    command=command,
                    origin=origin,
                    session=session
                )
                # Await the future to get CommandResponse
                return await asyncio.wait_for(response_future, timeout=25.0)
            
            # Schedule in the manager's loop and wait for result
            future = asyncio.run_coroutine_threadsafe(_execute(), _manager_loop)
            response = future.result(timeout=28.0)
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000  # milliseconds
            
            return jsonify({
                'success': response.success,
                'message': response.message,
                'navigation': response.navigation,
                'command': command,
                'origin': origin,
                'timestamp': end_time.isoformat(),
                'execution_time_ms': round(execution_time, 2),
                'meta': response.meta if hasattr(response, 'meta') else {}
            })
            
        except asyncio.TimeoutError:
            return jsonify({
                'success': False,
                'error': 'Command execution timeout',
                'message': 'Command took longer than 30 seconds to execute',
                'command': command
            }), 504
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Command execution error: {type(e).__name__}',
                'message': str(e),
                'command': command
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@command_bp.route('/help', methods=['GET'])
def get_help():
    """
    Get available commands help text
    
    Response:
        {
            "commands": ["list", "of", "commands"],
            "help_text": "Full help text"
        }
    """
    try:
        if not _command_manager:
            return jsonify({
                'success': False,
                'error': 'Command manager not initialized'
            }), 503
        
        # Execute the help command
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        future = _command_manager.submit(
            command="help",
            origin="api"
        )
        
        response = loop.run_until_complete(
            asyncio.wait_for(future, timeout=5.0)
        )
        
        # Extract available commands from handlers
        handlers = _command_manager.handlers if hasattr(_command_manager, 'handlers') else {}
        command_list = sorted(list(handlers.keys()))
        
        return jsonify({
            'success': True,
            'commands': command_list,
            'help_text': response.message if response.success else "Help not available",
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@command_bp.route('/status', methods=['GET'])
def get_status():
    """
    Get command system status
    
    Response:
        {
            "available": true/false,
            "registered_commands": ["list", "of", "commands"],
            "queue_size": 0,
            "timestamp": "ISO timestamp"
        }
    """
    try:
        if not _command_manager:
            return jsonify({
                'available': False,
                'error': 'Command manager not initialized',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Get diagnostic info
        handlers = _command_manager.handlers if hasattr(_command_manager, 'handlers') else {}
        command_list = sorted(list(handlers.keys()))
        
        # Try to get queue size and other diagnostics
        diagnostics = {}
        if hasattr(_command_manager, 'active_handlers_info'):
            try:
                diagnostics = _command_manager.active_handlers_info()
            except Exception:
                pass
        
        return jsonify({
            'available': True,
            'registered_commands': command_list,
            'command_count': len(command_list),
            'queue_size': diagnostics.get('queue_size', 0),
            'running': getattr(_command_manager, '_running', False),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'available': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


# Export the blueprint
__all__ = ['command_bp', 'set_command_manager']
