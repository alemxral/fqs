"""
FootballWidget - Display football match state and strategy information.

Shows:
- Current match score
- Match time (with dynamic timer)
- Match phase
- Time remaining
- Calculated max probability for next buy
"""
from __future__ import annotations

from typing import Optional, Dict, Any
from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Container
from rich.text import Text


class FootballWidget(Static):
    """Widget to display football match state and trading strategy info."""

    DEFAULT_CSS = """

    FootballWidget.hidden {
        display: none;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._widget_data: Optional[Dict[str, Any]] = None

    def on_mount(self) -> None:
        """Force widget styling when mounted - ensures full width."""
        # Force full width and styling via Python (overrides CSS issues)
        self.styles.width = "100%"
        self.styles.height = 3
        self.styles.background = "$boost"
        self.styles.color = "$text"
        self.styles.border = ("tall", "$accent")  # Top and bottom borders only
        self.styles.padding = (0, 2)
        self.styles.margin = 0
        self.styles.overflow_y = "hidden"
        self.styles.min_width = "100%"
        self.styles.max_width = "100%"
        # Initial display
        self.refresh_display()

    def update_data(self, widget_data: Optional[Dict[str, Any]]) -> None:
        """Update the widget with new football data."""
        print(f"[WIDGET] update_data() called with: {widget_data}")
        self._widget_data = widget_data
        self.refresh_display()
        print(f"[WIDGET] refresh_display() completed")

    def refresh_display(self) -> None:
        """Refresh the widget display with current data - HORIZONTAL LAYOUT."""
        print(f"[WIDGET] refresh_display() called, _widget_data={self._widget_data is not None}")
        
        # Default data if none provided
        if not self._widget_data:
            self._widget_data = {
                "score": "0-0",
                "time": "0:00",
                "minute": 0,
                "seconds": 0,
                "phase": "Waiting",
                "time_remaining": 90,
                "is_timer_running": False,
                "match_side": None,
                "goal_difference": 0
            }

        # Extract data
        score = self._widget_data.get("score", "0-0")
        time_display = self._widget_data.get("time", "0")
        minute = self._widget_data.get("minute", 0)
        seconds = self._widget_data.get("seconds", None)
        phase = self._widget_data.get("phase", "Unknown")
        time_remaining = self._widget_data.get("time_remaining", 90)
        is_running = self._widget_data.get("is_timer_running", False)
        match_side = self._widget_data.get("match_side", None)
        goal_diff = self._widget_data.get("goal_difference", 0)
        
        # If seconds is not provided, parse from time_display
        if seconds is None:
            try:
                if '+' in time_display:
                    base_time, injury_part = time_display.split('+')
                    _, sec_str = injury_part.split(':')
                    seconds = int(sec_str)
                elif ':' in time_display:
                    _, sec_str = time_display.split(':')
                    seconds = int(sec_str)
                else:
                    seconds = 0
            except:
                seconds = 0

        # Calculate remaining time
        try:
            # time_display format: "MM:SS" or "MM+I:SS"
            if '+' in time_display:
                base_time, injury_part = time_display.split('+')
                current_minute = int(base_time)
                injury_min, current_sec = injury_part.split(':')
                current_minute += int(injury_min)
                current_sec = int(current_sec)
            elif ':' in time_display:
                min_str, sec_str = time_display.split(':')
                current_minute = int(min_str)
                current_sec = int(sec_str)
            else:
                current_minute = int(time_display)
                current_sec = 0
            current_total_sec = (current_minute * 60) + current_sec
            total_match_sec = 90 * 60  # 5400 seconds
            remaining_total_sec = max(0, total_match_sec - current_total_sec)
            remaining_min = remaining_total_sec // 60
            remaining_sec = remaining_total_sec % 60
        except:
            remaining_min = time_remaining
            remaining_sec = 0

        # Build compact horizontal display text
        text = Text()
        
        # Line 1: Match info
        text.append("⚽ ", style="bold yellow")
        text.append(f"{score}", style="bold white")
        text.append(" │ ", style="dim")
        # Show timer as MM:SS or MM+I:SS
        text.append(f"{time_display}", style="bold cyan")
        text.append(f" [{seconds:02d}s]", style="bold magenta")
        text.append(" ", style="dim")
        
        # Timer status indicator
        if is_running:
            text.append("●", style="bold green")  # Live indicator
        else:
            text.append("○", style="dim yellow")  # Paused indicator
        
        text.append(" │ ", style="dim")
        text.append(f"{phase}", style="cyan")
        text.append(" │ ", style="dim")
        text.append(f"Rem: {remaining_min:02d}:{remaining_sec:02d}", style="bold white")
        
        # Line 2: Team tracking and strategy hints
        text.append("\n")
        if match_side:
            text.append(f"Track: {match_side.upper()}", style="magenta")
            text.append(" │ ", style="dim")
            
            # Goal difference with color
            if goal_diff > 0:
                text.append(f"+{goal_diff}", style="bold green")
            elif goal_diff < 0:
                text.append(f"{goal_diff}", style="bold red")
            else:
                text.append("0", style="yellow")
            text.append(" │ ", style="dim")
        
        # Strategy hints (compact)
        hints = []
        if time_remaining < 10:
            hints.append(("⚠Final", "bold red"))
        elif time_remaining < 20:
            hints.append(("⚠Late", "yellow"))
        
        if abs(goal_diff) >= 2:
            hints.append(("LowVol", "cyan"))
        
        if phase.startswith("Late"):
            hints.append(("Mult✓", "green"))
        
        if hints:
            for i, (hint_text, hint_style) in enumerate(hints):
                if i > 0:
                    text.append(" • ", style="dim")
                text.append(hint_text, style=hint_style)
        else:
            text.append("Standard parameters", style="dim")
        
        self.update(text)

    def on_mount(self) -> None:
        """Initialize widget when mounted."""
        self.refresh_display()
        
        # Set up periodic refresh if timer is running
        self.set_interval(1.0, self._periodic_refresh)

    def _periodic_refresh(self) -> None:
        """Periodically refresh display (for live timer updates)."""
        if self._widget_data and self._widget_data.get("is_timer_running"):
            # Request parent to update widget data
            # This will trigger through the screen's update cycle
            self.refresh_display()
