"""
Test Backend Logs Viewer Screen
Quick validation of the logs viewer functionality
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from textual.app import App
from ui.screens.backend_logs_screen import BackendLogsScreen


class TestLogsApp(App):
    """Simple test app for the backend logs screen"""
    
    def on_mount(self) -> None:
        """Show logs screen on mount"""
        self.push_screen(BackendLogsScreen())


if __name__ == "__main__":
    print("=" * 80)
    print("🧪 Testing Backend Logs Viewer")
    print("=" * 80)
    print()
    print("Instructions:")
    print("1. The logs viewer should load and display available logs")
    print("2. Press Ctrl+R to refresh logs")
    print("3. Press Ctrl+P to pause/resume auto-refresh")
    print("4. Press Ctrl+C to clear logs")
    print("5. Press ESC to exit")
    print()
    print("Starting test app...")
    print("=" * 80)
    print()
    
    app = TestLogsApp()
    app.run()
