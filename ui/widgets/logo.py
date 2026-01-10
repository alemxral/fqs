"""
Logo Widget - Reusable ASCII logo
Can be used in any screen (welcome, help, about, etc.)
"""
from textual.widgets import Static
from textual.app import RenderResult


class PMTerminalLogo(Static):
    """
    ASCII art logo widget
    
    Features:
    - Responsive (adapts to terminal width)
    - Reusable across screens
    - Configurable size (full/compact)
    """
    

    
    def __init__(
        self,
        size: str = "full",  # "full" or "compact"
        show_subtitle: bool = True,
        **kwargs
    ):
        """
        Initialize logo widget
        
        Args:
            size: "full" or "compact" logo
            show_subtitle: Show subtitle line below logo
        """
        super().__init__(**kwargs)
        self.logo_size = size
        self.show_subtitle = show_subtitle
    
    def render(self) -> RenderResult:
        """Render the logo"""
        # Get logo based on size
        if self.logo_size == "compact":
            logo = self._get_compact_logo()
        else:
            logo = self._get_full_logo()
        
        # Add subtitle if requested
        if self.show_subtitle:
            logo += "\n[cyan]Polymarket Trading Terminal[/cyan]"
        
        return logo
    
    def _get_full_logo(self) -> str:
        """Full size logo (for wide terminals)"""
        return """[white]
 ██████╗ ███████╗████████╗███████╗██████╗ ███╗   ███╗██╗███╗   ██╗ █████╗ ██╗     
██╔═══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██║████╗  ██║██╔══██╗██║     
██║   ██║███████╗   ██║   █████╗  ██████╔╝██╔████╔██║██║██╔██╗ ██║███████║██║     
██║▄▄ ██║╚════██║   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██║██║╚██╗██║██╔══██║██║     
╚██████╔╝███████║   ██║   ███████╗██║  ██║██║ ╚═╝ ██║██║██║ ╚████║██║  ██║███████╗
 ╚══▀▀═╝ ╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝
"""
    
    def _get_compact_logo(self) -> str:
        """Compact logo (for small terminals)"""
        return """[white]
 ██████╗ ███████╗████████╗███████╗██████╗ ███╗   ███╗██╗███╗   ██╗ █████╗ ██╗     
██╔═══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██║████╗  ██║██╔══██╗██║     
██║   ██║███████╗   ██║   █████╗  ██████╔╝██╔████╔██║██║██╔██╗ ██║███████║██║     
██║▄▄ ██║╚════██║   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██║██║╚██╗██║██╔══██║██║     
╚██████╔╝███████║   ██║   ███████╗██║  ██║██║ ╚═╝ ██║██║██║ ╚████║██║  ██║███████╗
 ╚══▀▀═╝ ╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝
"""
    
    def set_size(self, size: str) -> None:
        """Change logo size dynamically"""
        self.logo_size = size
        self.refresh()
    
    def toggle_subtitle(self) -> None:
        """Toggle subtitle visibility"""
        self.show_subtitle = not self.show_subtitle
        self.refresh()


class LogoAnimated(PMTerminalLogo):
    """
    Animated logo with color cycling
    Optional: Use for splash screens
    """
    
    def on_mount(self) -> None:
        """Start animation timer"""
        self.colors = ["cyan", "magenta", "yellow", "green"]
        self.color_index = 0
        self.set_interval(0.5, self._cycle_color)
    
    def _cycle_color(self) -> None:
        """Cycle through colors"""
        self.color_index = (self.color_index + 1) % len(self.colors)
        color = self.colors[self.color_index]
        self.styles.color = color