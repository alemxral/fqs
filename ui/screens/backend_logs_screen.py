"""
Backend Logs Viewer Screen
Real-time display of Flask backend logs and debugging messages
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Header, Footer, Static, RichLog, Button
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from rich.text import Text
import asyncio
import httpx
from datetime import datetime
from pathlib import Path


class BackendLogsScreen(Screen):
    """
    Screen to view Flask backend logs in real-time
    """
    
    BINDINGS = [
        Binding("escape", "go_back", "Back", priority=True),
        Binding("ctrl+c", "clear_logs", "Clear", priority=True),
        Binding("ctrl+r", "refresh_logs", "Refresh", priority=True),
        Binding("ctrl+p", "pause_auto_refresh", "Pause/Resume", priority=True),
    ]
    
    # Reactive state
    auto_refresh_enabled = reactive(True)
    log_count = reactive(0)
    
    CSS = """
    BackendLogsScreen {
        background: $surface;
    }
    
    #header_bar {
        height: 5;
        width: 100%;
        background: $boost;
        border: tall $primary;
        padding: 1 2;
    }
    
    #status_bar {
        height: 3;
        width: 100%;
        background: $panel;
        border: solid $accent;
        padding: 0 2;
    }
    
    .status-indicator {
        color: $success;
        text-style: bold;
    }
    
    .status-indicator.paused {
        color: $warning;
    }
    
    .status-indicator.error {
        color: $error;
    }
    
    #controls_bar {
        height: 5;
        width: 100%;
        background: $surface;
        border: solid $accent;
        padding: 1;
    }
    
    .control-btn {
        margin: 0 1;
        min-width: 12;
        height: 2;
    }
    
    #logs_container {
        height: 1fr;
        border: thick $primary;
        background: $panel;
        padding: 0;
    }
    
    #backend_logs {
        width: 100%;
        height: 100%;
        background: $panel;
        border: none;
    }
    
    #footer_info {
        dock: bottom;
        height: 3;
        background: $boost;
        color: $text;
        text-align: center;
        padding: 1;
    }
    
    RichLog {
        scrollbar-size-vertical: 2;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_lines = []
        self.max_log_lines = 500  # Keep last 500 lines
        self.auto_refresh_task = None
        self.last_fetch_time = None
        self.backend_url = "http://127.0.0.1:5000"
        
    def compose(self) -> ComposeResult:
        """Create screen layout"""
        yield Header(show_clock=True)
        
        # Header with title and status
        with Vertical(id="header_bar"):
            yield Static("🖥️  Backend Logs Viewer", id="title_label")
            yield Static("● Live", id="status_indicator", classes="status-indicator")
        
        # Status bar with metrics
        with Horizontal(id="status_bar"):
            yield Static("Logs: 0", id="log_count_label")
            yield Static("Auto-refresh: ON", id="auto_refresh_label")
            yield Static("Last update: Never", id="last_update_label")
        
        # Control buttons
        with Horizontal(id="controls_bar"):
            yield Button("🔄 Refresh", id="btn_refresh", classes="control-btn")
            yield Button("⏸️  Pause", id="btn_pause", classes="control-btn")
            yield Button("🗑️  Clear", id="btn_clear", classes="control-btn")
            yield Button("📥 Export", id="btn_export", classes="control-btn")
        
        # Logs display
        with Container(id="logs_container"):
            yield RichLog(
                id="backend_logs",
                highlight=True,
                markup=True,
                wrap=True,
                auto_scroll=True
            )
        
        yield Static(
            "Ctrl+R: Refresh | Ctrl+C: Clear | Ctrl+P: Pause/Resume | ESC: Back",
            id="footer_info"
        )
        yield Footer()
    
    async def on_mount(self) -> None:
        """Initialize when screen is mounted"""
        # Start auto-refresh
        await self.start_auto_refresh()
        
        # Initial log fetch
        await self.fetch_logs()
    
    async def start_auto_refresh(self) -> None:
        """Start auto-refresh task"""
        if self.auto_refresh_task is None:
            self.auto_refresh_task = asyncio.create_task(self._auto_refresh_loop())
            self.app.logger.info("Backend logs auto-refresh started")
    
    async def stop_auto_refresh(self) -> None:
        """Stop auto-refresh task"""
        if self.auto_refresh_task:
            self.auto_refresh_task.cancel()
            try:
                await self.auto_refresh_task
            except asyncio.CancelledError:
                pass
            self.auto_refresh_task = None
            self.app.logger.info("Backend logs auto-refresh stopped")
    
    async def _auto_refresh_loop(self) -> None:
        """Auto-refresh loop"""
        while True:
            try:
                if self.auto_refresh_enabled:
                    await self.fetch_logs()
                await asyncio.sleep(2.0)  # Refresh every 2 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.app.logger.error(f"Auto-refresh error: {e}")
                await asyncio.sleep(5.0)  # Wait longer on error
    
    async def fetch_logs(self) -> None:
        """Fetch logs from Flask backend or log file"""
        try:
            # Try to read from Flask logs file
            log_file = Path(__file__).parent.parent.parent / "logs" / "flask.log"
            
            if log_file.exists():
                await self._read_log_file(log_file)
            else:
                # Try to fetch from health endpoint as fallback
                await self._fetch_from_api()
                
        except Exception as e:
            self.app.logger.error(f"Failed to fetch logs: {e}")
            await self._add_log_line(f"[red]Error fetching logs: {e}[/red]")
    
    async def _read_log_file(self, log_file: Path) -> None:
        """Read logs from file"""
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                # Read last N lines efficiently
                lines = f.readlines()
                recent_lines = lines[-self.max_log_lines:]
                
                # Clear and add new lines if this is initial load
                if not self.log_lines:
                    for line in recent_lines:
                        await self._add_log_line(line.rstrip(), skip_duplicate_check=True)
                else:
                    # Only add new lines
                    existing_count = len(self.log_lines)
                    for line in recent_lines[existing_count:]:
                        await self._add_log_line(line.rstrip())
            
            self.last_fetch_time = datetime.now()
            await self._update_status_labels()
            
        except Exception as e:
            self.app.logger.error(f"Error reading log file: {e}")
    
    async def _fetch_from_api(self) -> None:
        """Fetch status from API (fallback)"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.backend_url}/api/health")
                
                if response.status_code == 200:
                    data = response.json()
                    timestamp = data.get('timestamp', 'Unknown')
                    status = data.get('status', 'unknown')
                    
                    await self._add_log_line(
                        f"[green]{timestamp}[/green] - Backend status: [bold]{status}[/bold]"
                    )
                else:
                    await self._add_log_line(
                        f"[yellow]Backend returned status {response.status_code}[/yellow]"
                    )
            
            self.last_fetch_time = datetime.now()
            await self._update_status_labels()
            
        except httpx.ConnectError:
            await self._add_log_line(
                "[red]⚠ Cannot connect to Flask backend at {self.backend_url}[/red]"
            )
            status_indicator = self.query_one("#status_indicator", Static)
            status_indicator.update("● Offline")
            status_indicator.remove_class("status-indicator")
            status_indicator.add_class("status-indicator", "error")
            
        except Exception as e:
            await self._add_log_line(f"[red]API fetch error: {e}[/red]")
    
    async def _add_log_line(self, line: str, skip_duplicate_check: bool = False) -> None:
        """Add a log line to the display"""
        if not line.strip():
            return
        
        # Avoid duplicates unless explicitly skipped
        if not skip_duplicate_check and self.log_lines and self.log_lines[-1] == line:
            return
        
        self.log_lines.append(line)
        
        # Trim old lines
        if len(self.log_lines) > self.max_log_lines:
            self.log_lines = self.log_lines[-self.max_log_lines:]
        
        # Add to RichLog widget
        logs_widget = self.query_one("#backend_logs", RichLog)
        
        # Colorize log levels
        formatted_line = self._format_log_line(line)
        logs_widget.write(formatted_line)
        
        # Update count
        self.log_count = len(self.log_lines)
    
    def _format_log_line(self, line: str) -> str:
        """Format log line with colors based on content"""
        line_lower = line.lower()
        
        # Already has markup
        if '[' in line and ']' in line and any(c in line for c in ['red', 'green', 'yellow', 'blue', 'cyan']):
            return line
        
        # Add color based on log level
        if 'error' in line_lower or 'exception' in line_lower or 'failed' in line_lower:
            return f"[red]{line}[/red]"
        elif 'warning' in line_lower or 'warn' in line_lower:
            return f"[yellow]{line}[/yellow]"
        elif 'info' in line_lower or '✓' in line or 'success' in line_lower:
            return f"[green]{line}[/green]"
        elif 'debug' in line_lower:
            return f"[dim]{line}[/dim]"
        elif 'starting' in line_lower or 'initialized' in line_lower:
            return f"[cyan]{line}[/cyan]"
        else:
            return line
    
    async def _update_status_labels(self) -> None:
        """Update status bar labels"""
        # Update log count
        count_label = self.query_one("#log_count_label", Static)
        count_label.update(f"Logs: {self.log_count}")
        
        # Update auto-refresh status
        refresh_label = self.query_one("#auto_refresh_label", Static)
        refresh_label.update(f"Auto-refresh: {'ON' if self.auto_refresh_enabled else 'OFF'}")
        
        # Update last update time
        if self.last_fetch_time:
            time_str = self.last_fetch_time.strftime("%H:%M:%S")
            update_label = self.query_one("#last_update_label", Static)
            update_label.update(f"Last update: {time_str}")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id
        
        if button_id == "btn_refresh":
            await self.action_refresh_logs()
        elif button_id == "btn_pause":
            await self.action_pause_auto_refresh()
        elif button_id == "btn_clear":
            await self.action_clear_logs()
        elif button_id == "btn_export":
            await self.export_logs()
    
    async def action_refresh_logs(self) -> None:
        """Manually refresh logs"""
        self.notify("Refreshing logs...", severity="information")
        await self.fetch_logs()
        self.notify("Logs refreshed", severity="information")
    
    async def action_pause_auto_refresh(self) -> None:
        """Toggle auto-refresh"""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        
        # Update button text
        pause_btn = self.query_one("#btn_pause", Button)
        if self.auto_refresh_enabled:
            pause_btn.label = "⏸️  Pause"
            status_indicator = self.query_one("#status_indicator", Static)
            status_indicator.update("● Live")
            status_indicator.remove_class("paused")
            self.notify("Auto-refresh enabled", severity="information")
        else:
            pause_btn.label = "▶️  Resume"
            status_indicator = self.query_one("#status_indicator", Static)
            status_indicator.update("⏸ Paused")
            status_indicator.add_class("paused")
            self.notify("Auto-refresh paused", severity="warning")
        
        await self._update_status_labels()
    
    async def action_clear_logs(self) -> None:
        """Clear all logs"""
        self.log_lines.clear()
        self.log_count = 0
        
        logs_widget = self.query_one("#backend_logs", RichLog)
        logs_widget.clear()
        
        await self._update_status_labels()
        self.notify("Logs cleared", severity="information")
    
    async def export_logs(self) -> None:
        """Export logs to file"""
        try:
            export_file = Path.cwd() / f"backend_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(export_file, 'w', encoding='utf-8') as f:
                f.write(f"Backend Logs Export - {datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n\n")
                for line in self.log_lines:
                    # Strip markup for plain text export
                    clean_line = line
                    for tag in ['red', 'green', 'yellow', 'blue', 'cyan', 'bold', 'dim']:
                        clean_line = clean_line.replace(f'[{tag}]', '').replace(f'[/{tag}]', '')
                    f.write(clean_line + "\n")
            
            self.notify(f"Logs exported to {export_file.name}", severity="information")
            
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error")
    
    def action_go_back(self) -> None:
        """Go back to previous screen"""
        self.app.pop_screen()
    
    async def on_unmount(self) -> None:
        """Cleanup when screen is unmounted"""
        await self.stop_auto_refresh()
