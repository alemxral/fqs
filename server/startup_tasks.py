"""
Startup Tasks for Flask Backend
Executes background tasks during server initialization
"""
import sys
import logging
import threading
import time
from pathlib import Path
from typing import Callable, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class StartupTask:
    """Represents a single startup task"""
    
    def __init__(self, name: str, func: Callable, priority: int = 5, blocking: bool = False):
        """
        Initialize startup task
        
        Args:
            name: Task name for logging
            func: Callable to execute
            priority: Priority (1=highest, 10=lowest)
            blocking: If True, waits for task completion before continuing
        """
        self.name = name
        self.func = func
        self.priority = priority
        self.blocking = blocking
        self.status = 'pending'
        self.error = None
        self.start_time = None
        self.end_time = None
        self.result = None
    
    def execute(self) -> bool:
        """
        Execute the task
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.status = 'running'
            self.start_time = datetime.now()
            logger.info(f"📋 Starting task: {self.name}")
            
            self.result = self.func()
            
            self.status = 'completed'
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            logger.info(f"✓ Task completed: {self.name} ({duration:.2f}s)")
            return True
            
        except Exception as e:
            self.status = 'failed'
            self.error = str(e)
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0
            logger.error(f"✗ Task failed: {self.name} ({duration:.2f}s) - {e}")
            return False
    
    def get_duration(self) -> float:
        """Get task duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class StartupTaskRegistry:
    """Registry for managing startup tasks"""
    
    def __init__(self):
        self.tasks: List[StartupTask] = []
        self._executed = False
    
    def register(self, name: str, func: Callable, priority: int = 5, blocking: bool = False):
        """
        Register a startup task
        
        Args:
            name: Task name
            func: Function to execute
            priority: Execution priority (1=first, 10=last)
            blocking: Wait for completion before continuing
        """
        task = StartupTask(name, func, priority, blocking)
        self.tasks.append(task)
        logger.debug(f"Registered startup task: {name} (priority={priority}, blocking={blocking})")
    
    def execute_all(self, async_mode: bool = True) -> Dict[str, Any]:
        """
        Execute all registered tasks
        
        Args:
            async_mode: If True, runs non-blocking tasks in background thread
        
        Returns:
            Summary of task execution
        """
        if self._executed:
            logger.warning("Startup tasks already executed")
            return self.get_summary()
        
        self._executed = True
        
        # Sort by priority
        self.tasks.sort(key=lambda t: t.priority)
        
        logger.info(f"🚀 Executing {len(self.tasks)} startup tasks...")
        start_time = datetime.now()
        
        blocking_tasks = [t for t in self.tasks if t.blocking]
        async_tasks = [t for t in self.tasks if not t.blocking]
        
        # Execute blocking tasks first (synchronously)
        for task in blocking_tasks:
            task.execute()
        
        # Execute async tasks
        if async_tasks and async_mode:
            def run_async_tasks():
                for task in async_tasks:
                    task.execute()
            
            thread = threading.Thread(target=run_async_tasks, daemon=True)
            thread.start()
            logger.info(f"✓ {len(async_tasks)} async tasks started in background")
        else:
            # Run synchronously
            for task in async_tasks:
                task.execute()
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        summary = self.get_summary()
        logger.info(f"✓ Startup tasks completed in {total_duration:.2f}s")
        logger.info(f"  Completed: {summary['completed']}, Failed: {summary['failed']}, Pending: {summary['pending']}")
        
        return summary
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of task execution"""
        completed = len([t for t in self.tasks if t.status == 'completed'])
        failed = len([t for t in self.tasks if t.status == 'failed'])
        pending = len([t for t in self.tasks if t.status in ['pending', 'running']])
        
        return {
            'total': len(self.tasks),
            'completed': completed,
            'failed': failed,
            'pending': pending,
            'tasks': [
                {
                    'name': t.name,
                    'status': t.status,
                    'duration': t.get_duration(),
                    'error': t.error
                }
                for t in self.tasks
            ]
        }


# Global registry
_registry = StartupTaskRegistry()


def register_task(name: str, func: Callable, priority: int = 5, blocking: bool = False):
    """
    Register a startup task (convenience function)
    
    Args:
        name: Task name
        func: Function to execute
        priority: Priority (1=highest, 10=lowest)
        blocking: Wait for completion
    """
    _registry.register(name, func, priority, blocking)


def execute_startup_tasks(async_mode: bool = True) -> Dict[str, Any]:
    """
    Execute all registered startup tasks
    
    Args:
        async_mode: Run non-blocking tasks asynchronously
    
    Returns:
        Execution summary
    """
    return _registry.execute_all(async_mode)


def get_task_summary() -> Dict[str, Any]:
    """Get summary of task execution"""
    return _registry.get_summary()


# ============= PREDEFINED TASKS =============

def fetch_live_football_matches_task():
    """Fetch and cache live football matches"""
    try:
        # Import utility
        gamma_utils_path = PROJECT_ROOT / "fqs" / "utils" / "gamma-api"
        if str(gamma_utils_path) not in sys.path:
            sys.path.insert(0, str(gamma_utils_path))
        
        from get_live_football_matches import get_live_football_matches
        
        # Import cache manager
        cache_utils_path = PROJECT_ROOT / "fqs" / "utils" / "core"
        if str(cache_utils_path) not in sys.path:
            sys.path.insert(0, str(cache_utils_path))
        
        from cache_manager import write_cache
        
        # Fetch matches
        logger.info("Fetching live football matches...")
        matches = get_live_football_matches(fields=None)
        
        if not matches:
            logger.warning("No matches found")
            return {'success': False, 'count': 0}
        
        # Cache results
        metadata = {
            "total_matches": len(matches),
            "source": "Startup Task - Gamma API",
            "extraction_timestamp": datetime.now().isoformat()
        }
        
        cache_data = {
            "metadata": metadata,
            "matches": matches
        }
        
        write_cache('live_football_matches.json', cache_data, ttl_seconds=300)
        
        logger.info(f"✓ Cached {len(matches)} live football matches")
        return {'success': True, 'count': len(matches)}
        
    except Exception as e:
        logger.error(f"Failed to fetch live matches: {e}")
        return {'success': False, 'error': str(e)}


def warm_up_gamma_api_task():
    """Warm up Gamma API connection"""
    try:
        import requests
        response = requests.get('https://gamma-api.polymarket.com/events?limit=1', timeout=5)
        response.raise_for_status()
        logger.info("✓ Gamma API connection warmed up")
        return {'success': True}
    except Exception as e:
        logger.warning(f"Gamma API warm-up failed: {e}")
        return {'success': False, 'error': str(e)}


def validate_environment_task():
    """Validate environment configuration"""
    try:
        from dotenv import load_dotenv
        import os
        
        # Load .env file
        env_path = PROJECT_ROOT / "fqs" / "config" / ".env"
        load_dotenv(env_path)
        
        # Check required variables
        required = ['PK', 'POLYGON_RPC_URL']
        missing = [var for var in required if not os.getenv(var)]
        
        if missing:
            logger.warning(f"Missing environment variables: {missing}")
            return {'success': False, 'missing': missing}
        
        logger.info("✓ Environment validated")
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        return {'success': False, 'error': str(e)}


# ============= AUTO-REGISTER DEFAULT TASKS =============

def register_default_tasks():
    """Register default startup tasks"""
    # Priority 1: Critical tasks (blocking)
    register_task(
        name="Validate Environment",
        func=validate_environment_task,
        priority=1,
        blocking=True
    )
    
    # Priority 3: API warm-up (non-blocking)
    register_task(
        name="Warm Up Gamma API",
        func=warm_up_gamma_api_task,
        priority=3,
        blocking=False
    )
    
    # Priority 5: Data fetching (non-blocking)
    register_task(
        name="Fetch Live Football Matches",
        func=fetch_live_football_matches_task,
        priority=5,
        blocking=False
    )
